from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class SectionSpan:
    name: str
    start: int
    end: int
    heading: str
    level: int


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _heading_similarity(a: str, b: str) -> float:
    a_f = _fold(a)
    b_f = _fold(b)
    if not a_f or not b_f:
        return 0.0
    if a_f == b_f:
        return 1.0
    if a_f in b_f or b_f in a_f:
        return 0.95
    return SequenceMatcher(None, a_f, b_f).ratio()


class VietnameseClinicalSectionParser:
    """Parse Vietnamese clinical note section headings with original offsets."""

    # (canonical_name, level, aliases)
    # level 1 = major numbered history blocks; level 2 = subsections
    HEADING_SPECS: list[tuple[str, int, tuple[str, ...]]] = [
        # Major history
        ("Tiền sử bệnh", 1, ("tiền sử bệnh", "tiền sử")),
        (
            "Tiền sử bệnh nội khoa",
            2,
            ("tiền sử bệnh nội khoa", "tiền sử nội khoa"),
        ),
        (
            "Bệnh lý mãn tính",
            2,
            (
                "bệnh lý mãn tính",
                "các bệnh lý mãn tính",
                "các bệnh mãn tính",
                "các bệnh đã điều trị trước đây",
            ),
        ),
        (
            "Tiền sử phẫu thuật / thủ thuật",
            2,
            (
                "tiền sử phẫu thuật / thủ thuật",
                "tiền sử phẫu thuật",
                "lịch sử phẫu thuật / thủ thuật",
                "lịch sử phẫu thuật",
            ),
        ),
        (
            "Thuốc trước khi nhập viện",
            2,
            (
                "thuốc trước khi nhập viện",
                "thuốc đang dùng trước khi nhập viện",
                "thuốc đã dùng trước đây",
                "thuốc đang điều trị theo đơn",
                "thuốc đang dùng",
            ),
        ),
        # Current illness
        ("Bệnh sử", 1, ("bệnh sử", "bệnh sử hiện tại", "tiền sử bệnh hiện tại")),
        (
            "Lý do nhập viện",
            2,
            ("lý do nhập viện", "lý do vào viện", "lý do khám bệnh"),
        ),
        (
            "Triệu chứng hiện tại",
            2,
            (
                "triệu chứng hiện tại",
                "các triệu chứng hiện tại",
                "triệu chứng khi nhập viện",
            ),
        ),
        (
            "Tình trạng lúc vào viện",
            2,
            (
                "tình trạng lúc vào viện",
                "tình trạng khi đến khoa cấp cứu",
                "khám hiện tại",
            ),
        ),
        # Hospital assessment
        (
            "Đánh giá tại bệnh viện",
            1,
            ("đánh giá tại bệnh viện", "khám tại bệnh viện"),
        ),
        (
            "Kết quả xét nghiệm",
            2,
            ("kết quả xét nghiệm", "cận lâm sàng"),
        ),
        (
            "Kết quả chẩn đoán hình ảnh",
            2,
            ("kết quả chẩn đoán hình ảnh", "chẩn đoán hình ảnh"),
        ),
        ("Chẩn đoán", 2, ("chẩn đoán",)),
        (
            "Điều trị",
            2,
            ("điều trị", "điều trị tại bệnh viện", "xử trí thuốc"),
        ),
        (
            "Thủ thuật",
            2,
            ("thủ thuật", "các thủ thuật đã thực hiện"),
        ),
    ]

    LINE_HEADING_PATTERN = re.compile(
        r"^(?P<indent>\s*)(?:(?P<num>\d+)\s*[\.\)\-:]\s*)?(?P<body>.+?)\s*:?\s*$",
        flags=re.MULTILINE,
    )

    def __init__(self, similarity_threshold: float = 0.82):
        self.similarity_threshold = similarity_threshold
        self._sections: list[SectionSpan] = []

    def parse(self, text: str) -> list[SectionSpan]:
        matches: list[tuple[int, int, str, int, str]] = []
        # (heading_start, content_start, canonical, level, heading_text)

        for match in self.LINE_HEADING_PATTERN.finditer(text):
            body = match.group("body").strip().rstrip(":").strip()
            if not body or len(body) > 90:
                continue
            # Skip pure bullet content lines
            if body.startswith("-"):
                continue

            best_name = None
            best_level = None
            best_score = 0.0
            for canonical, level, aliases in self.HEADING_SPECS:
                for alias in aliases:
                    score = _heading_similarity(body, alias)
                    # Prefer more specific (longer) aliases on ties
                    if score > best_score or (
                        abs(score - best_score) < 1e-9
                        and best_name is not None
                        and len(alias) > len(best_name)
                    ):
                        # Avoid matching very short generic "chẩn đoán" inside long prose
                        if score >= self.similarity_threshold:
                            best_score = score
                            best_name = canonical
                            best_level = level

            if best_name is None or best_level is None:
                continue

            heading_start = match.start()
            # Content begins after the heading line
            content_start = match.end()
            if content_start < len(text) and text[content_start] == "\n":
                content_start += 1
            # If heading had inline content after colon on same line, keep it
            # e.g. "Lý do nhập viện: buồn nôn, ..."
            raw_line = match.group(0)
            if ":" in raw_line:
                colon_in_match = raw_line.find(":")
                after = raw_line[colon_in_match + 1 :].strip()
                if after and not re.fullmatch(r"\d+\s*[\.\)]?", after):
                    content_start = match.start() + colon_in_match + 1
                    while content_start < match.end() and text[content_start] in " \t":
                        content_start += 1

            matches.append(
                (
                    heading_start,
                    content_start,
                    best_name,
                    best_level,
                    body,
                )
            )

        # Deduplicate overlapping heading detections: keep highest score/specificity
        # by sorting and dropping near-duplicate starts
        matches.sort(key=lambda m: (m[0], -m[3], -len(m[4])))
        filtered: list[tuple[int, int, str, int, str]] = []
        used_starts: set[int] = set()
        for item in matches:
            hs = item[0]
            if any(abs(hs - u) <= 1 for u in used_starts):
                continue
            used_starts.add(hs)
            filtered.append(item)
        filtered.sort(key=lambda m: m[0])

        sections: list[SectionSpan] = []
        for i, (_hs, content_start, name, level, heading) in enumerate(filtered):
            end = len(text)
            for j in range(i + 1, len(filtered)):
                next_hs, _ncs, _nn, next_level, _nh = filtered[j]
                if next_level <= level:
                    end = next_hs
                    break
            if content_start > end:
                end = content_start
            sections.append(
                SectionSpan(
                    name=name,
                    start=content_start,
                    end=end,
                    heading=heading,
                    level=level,
                )
            )

        self._sections = sections
        return list(sections)

    def get_section_at(self, position: int) -> SectionSpan | None:
        # Innermost (highest level / latest start) containing section
        best: SectionSpan | None = None
        for section in self._sections:
            if section.start <= position < section.end:
                if best is None or section.level > best.level or (
                    section.level == best.level and section.start >= best.start
                ):
                    best = section
        return best

    def get_section_name_at(self, position: int) -> str | None:
        section = self.get_section_at(position)
        return section.name if section else None

    @property
    def sections(self) -> list[SectionSpan]:
        return list(self._sections)

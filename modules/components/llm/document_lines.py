from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentLine:
    line_id: str
    start: int
    end: int
    text: str


@dataclass
class LineIndexedDocument:
    """Exact line mapping over the unmodified original document."""

    original_text: str
    lines: list[DocumentLine]

    def get(self, line_id: str) -> DocumentLine | None:
        for line in self.lines:
            if line.line_id == line_id:
                return line
        return None

    def as_prompt_block(self) -> str:
        parts: list[str] = []
        for line in self.lines:
            parts.append(f"[{line.line_id}] {line.text}")
        return "\n".join(parts)

    def to_dicts(self) -> list[dict]:
        return [
            {
                "line_id": line.line_id,
                "start": line.start,
                "end": line.end,
                "text": line.text,
            }
            for line in self.lines
        ]


def build_line_index(text: str) -> LineIndexedDocument:
    """Split on '\\n' while preserving exact original offsets.

    Line IDs are prompt metadata only (L001, L002, ...). They must never appear
    in final competition JSON. The original document is not modified.
    """
    lines: list[DocumentLine] = []
    if text == "":
        return LineIndexedDocument(original_text=text, lines=lines)

    offset = 0
    # splitlines(keepends=False) drops the newline; recompute offsets carefully.
    parts = text.split("\n")
    for idx, part in enumerate(parts):
        # For all but the last segment produced by split("\n"), a newline existed.
        start = offset
        end = start + len(part)
        line_id = f"L{idx + 1:03d}"
        lines.append(DocumentLine(line_id=line_id, start=start, end=end, text=part))
        offset = end
        if idx < len(parts) - 1:
            offset += 1  # account for the '\n' separator
    return LineIndexedDocument(original_text=text, lines=lines)

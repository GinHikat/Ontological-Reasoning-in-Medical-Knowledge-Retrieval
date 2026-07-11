# v9 mid-run LLM cache audit

Snapshot while full cache gen still running (`46` cache JSON files on disk; tqdm may show a lower % because early docs were skipped).

Baseline for overlap: `output/v7_structured/same_env/submission` (field `position`).

## Headline (most important)

- Cache-accepted after align+verify: **604**
- Already exact span in v7: **435** (72.0%)
- Overlap v7 (non-exact): **150** (24.8%)
- Truly non-overlapping vs v7 (would be additive): **19** (3.1%)

Phase B drops overlaps, so **expected additive yield from these docs is ~19 mentions**, not hundreds.

## Status / funnel

- status counts: `{'ok': 44, 'completed_with_parse_issues': 1, 'proposer_failed': 1}`
- types accepted: `{'TRIỆU_CHỨNG': 330, 'CHẨN_ĐOÁN': 190, 'THUỐC': 84}`
- alignment rejects: `{'multiple_match': 16, 'zero_match': 29}`

### Problem docs

- **16** — `proposer_failed` (truncated JSON). Offline salvage recovers **48** proposals / **47** aligned; verifier not run yet (do not steal llama.cpp from live gen).
  - Artifact: `analysis/v9_doc16_salvage_record.json`
  - After cache finishes: `python modules/evaluation/salvage_v9_failed_cache.py --doc-id 16 --write-cache`
- **41** — `completed_with_parse_issues` but still **38** accepted (usable).
- **31** — `ok` with **0** proposals (4-line OB triage note; likely true empty).

## All non-overlapping candidates (manual review)

- doc 1 [1689:1706] CHẨN_ĐOÁN: `ngoại tâm thu nhĩ`
- doc 3 [4290:4320] CHẨN_ĐOÁN: `thay đổi sóng t không đặc hiệu`
- doc 5 [1083:1097] CHẨN_ĐOÁN: `giãn đường mật`
- doc 5 [1105:1124] CHẨN_ĐOÁN: `tắc nghẽn đường mật`
- doc 6 [357:365] TRIỆU_CHỨNG: `hẹp nặng`
- doc 12 [321:323] TRIỆU_CHỨNG: `ho`
- doc 13 [124:162] CHẨN_ĐOÁN: `Hội chứng kháng enzym tổng hợp protein`
- doc 13 [953:963] THUỐC: `doxycyclin`
- doc 13 [976:990] CHẨN_ĐOÁN: `viêm mô tế bào`
- doc 32 [1711:1713] TRIỆU_CHỨNG: `Ho`
- doc 35 [661:668] TRIỆU_CHỨNG: `ảo giác`
- doc 35 [1693:1696] CHẨN_ĐOÁN: `cml`
- doc 37 [943:951] THUỐC: `glargine`
- doc 48 [827:871] TRIỆU_CHỨNG: `khó khăn khi ước lượng vị trí ngồi xuống ghế`
- doc 70 [310:323] THUỐC: `thuốc an thần`
- doc 70 [1253:1266] THUỐC: `thuốc an thần`
- doc 70 [1516:1519] THUỐC: `nac`
- doc 96 [45:65] CHẨN_ĐOÁN: `bàng quang thần kinh`
- doc 100 [1441:1451] THUỐC: `Laxis 20mg`

## Quality flags among accepted (not only novel)

- long phrases (>50 chars): 12
  - doc 32 CHẨN_ĐOÁN: `nhiễm khuẩn huyết do tụ cầu vàng nhạy cảm methicillin`
  - doc 32 CHẨN_ĐOÁN: `Nhiễm khuẩn huyết do tụ cầu vàng nhạy cảm methicillin`
  - doc 15 CHẨN_ĐOÁN: `xuất huyết nội sọ không do chấn thương, không đặc hiệu`
  - doc 15 CHẨN_ĐOÁN: `xuất huyết nội sọ không do chấn thương, không đặc hiệu`
  - doc 17 CHẨN_ĐOÁN: `bệnh trào ngược dạ dày- thực quản không có viêm thực quản`
  - doc 7 TRIỆU_CHỨNG: `rối loạn thị giác, nhìn thấy con cái mình ở góc mắt`
  - doc 20 CHẨN_ĐOÁN: `bệnh tim mạch do xơ vữa động mạch với Nhồi máu cơ tim gần đây`
  - doc 20 CHẨN_ĐOÁN: `tim to, tràn dịch màng tim, tràn dịch màng phổi hai bên, thoát vị hoành nhỏ, thay đổi khí phế thủng, và xẹp phổi hai đáy`
  - doc 20 CHẨN_ĐOÁN: `tim to, tràn dịch màng tim, tràn dịch màng phổi hai bên, thoát vị hoành nhỏ, thay đổi khí phế thủng, xẹp phổi hai đáy`
  - doc 20 CHẨN_ĐOÁN: `EF30, mất vận động vùng đỉnh, hở van ba lá vừa-nặng (mod-severe TR) và hở van hai lá/van động mạch chủ nhẹ (mild ARMR)`
  - doc 20 CHẨN_ĐOÁN: `Gãy xương hông phải: gãy cổ xương đùi phải, lún đầu dưới`
  - doc 20 CHẨN_ĐOÁN: `Nhồi máu cơ tim vùng vách liên thất, mạn tính và đỉnh`
- English non-drug tokens: 11
  - doc 89 CHẨN_ĐOÁN: `Clostridioides difficile`
  - doc 17 TRIỆU_CHỨNG: `ho khan`
  - doc 41 TRIỆU_CHỨNG: `nausea`
  - doc 41 TRIỆU_CHỨNG: `diarrhea`
  - doc 41 TRIỆU_CHỨNG: `abdominal pain`
  - doc 21 CHẨN_ĐOÁN: `suy tim`
  - doc 37 CHẨN_ĐOÁN: `Suy tim`
  - doc 35 CHẨN_ĐOÁN: `cml`
  - doc 3 CHẨN_ĐOÁN: `Tim to`
  - doc 12 TRIỆU_CHỨNG: `fever`
  - doc 33 CHẨN_ĐOÁN: `suy tim`
- leading negation: 1
  - doc 10 TRIỆU_CHỨNG: `không tăng cân nhiều`

## Code changes made while waiting

1. `modules/components/llm/response_parser.py` — truncated-`entities` JSON salvage (would have recovered doc 16 without LLM repair).
2. `modules/evaluation/salvage_v9_failed_cache.py` — re-parse raw proposer + optional verifier; `--write-cache` quarantines stub first.

## Implications for Phase B

- Do **not** expect a large score jump from raw accepted counts; most LLM hits duplicate v7 spans.
- Focus review on the non-overlap list above (weak items: bare `Ho`/`ho`, `cml`, generic `thuốc an thần`, `nac`).
- Imaging dump phrases (e.g. doc 20 long CXR strings) are mostly overlapping/exact and will be dropped, but they waste verifier budget.

## Next after full 100 cache

1. Quarantine/regenerate any remaining `proposer_failed` / empty-raw stubs; run salvage for doc 16.
2. Stop Qwen server; Phase B `run_pipeline.py --pipeline v9_llm_recall`.
3. Re-run this overlap audit on full 100; decide READY / NOT READY.

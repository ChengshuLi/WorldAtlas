# Portugal–Spain six-centre authority assessment

Issue #1197 source-only campaign, retrieved 2026-10-06. Start with [the per-cell assessment](source-assessment.md). Its finding is that all six centres lie within 10.264 m of a DGT CAOP2025 `troços` feature marked `Portugal#Espanha` / `Definido`; exact centre side, sovereign owner and present wetness remain unresolved for every cell.

## Retained evidence

- `sources/dgt-trocos/` contains the exact DGT `trocos` collection description, schema/queryables, six full feature responses, HTTP headers, request URLs, byte hashes, and all nine failed Python TLS-verification attempts. The requests later succeeded with default TLS validation using curl.
- `scripts/measure_dgt_segment_proximity.py` is the immutable point-to-line producer. It checks the exact issue snapshot and BBOX/query context, response hashes/counts, native DGT segment IDs, source properties, and line/BBOX intersection before measuring distances.
- `outputs/dgt-segment-proximity.json` preserves each exact coordinate, source feature, source-byte hash, distance, and unresolved assessment.
- `validation/` records positive and negative controls and the two-run result.
- `evidence-quality.json` binds this campaign to issue subjects, grid/hierarchy pins, source/output hashes, the actual code runs, and the stated limits.

The complete administrative polygon and physical-water source packets remain in their existing source lanes; they are linked and discussed without copying or changing those files. No geometry, native grid, application data, ownership, or physical-water class is changed here. This issue does not close #972 or campaign #1202.

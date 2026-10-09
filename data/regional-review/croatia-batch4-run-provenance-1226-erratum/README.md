# Croatia batch 4 run-provenance erratum (#1396)

This additive packet corrects metadata provenance and fresh-run controls for the exact 224 Croatia batch 4 IDs examined by #1199/#1209. It does not change Croatian geography, Atlas IDs, parent assignments, source boundaries, historical pins or earlier reports.

## Reproduce

Use Python 3.10 or later from the repository root. The runner must already be committed because each run checks its own committed Git blob.

```sh
python3 data/regional-review/croatia-batch4-run-provenance-1226-erratum/reproduce.py --run-id unique-run-name
python3 data/regional-review/croatia-batch4-run-provenance-1226-erratum/controls.py --run-id unique-controls-name
```

Every name must be new. The report runner writes three report files and then a complete `run-record.json` under `evidence/runs/<name>/`. The controls runner performs two new complete report executions, compares all outputs with the retained #1199 result, exercises malformed-receipt, exact-subject-scope and write-safety controls, and writes its completion file last under `evidence/validation/<name>/`. It rejects duplicate, missing and fabricated subject IDs; ordinary-file, broken-symlink, escaping-symlink and live-symlink parents; and interrupted writes. It refuses to overwrite any existing vintage; retain partial failures and choose a new name.

The `issue_updated_at` value comes from the one complete captured #1209 API response. `issue_retrieved_at` comes separately from the retained retrieval receipt for that exact response. The captured #1396 task snapshot and its retrieval receipt are also separately identified. Run records include the exact report names and hashes, full consumed input list, 80-object issue source inventory, 62 historical pins, exact subject digest and actual decoded XLSX members. The reviewed `verified-20261008-r4` execution also exercises adverse exact-scope mutations against the real output validator and the filesystem edge cases above.

## Geographic limits

The source roles, vintages, license/access questions, neighboring batch context and unresolved Croatia findings are carried forward in [RESEARCH.md](RESEARCH.md) and the retained #1199 packet. This mechanical correction establishes no legal boundaries, independent county parentage, complete census-date polygons, island/coast completeness, source grant or regional approval. No data is imported or published.

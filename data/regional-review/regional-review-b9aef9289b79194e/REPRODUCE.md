# Reproduce issue #435 evidence

Run from the repository root at the pinned base commit recorded in `findings/scope-reproduction.json` (currently `4877ef4e99528615daf657a376b7605d1657f817`). The packet scripts write only beneath this owned directory. Inputs include the exact GitHub issue snapshots, `data/world-index.json`, `data/hierarchy.json`, the frozen macro inventory and the retained source files listed in `findings/source-register.json`.

```sh
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/reproduce_scope.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/check_source_coverage.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/reconcile_south_africa_neighbor.py
python3.12 -m pip install --target /tmp/worldatlas-geography-pydeps -r data/regional-review/regional-review-b9aef9289b79194e/requirements.txt
PYTHONPATH=/tmp/worldatlas-geography-pydeps python3.12 data/regional-review/regional-review-b9aef9289b79194e/scripts/reconcile_pinned_sources.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/classify_subjects.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/classify_parents.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/classify_areas.py
python3 data/regional-review/regional-review-b9aef9289b79194e/scripts/build_source_register.py
```

The successful reproduction used Python 3.12 (the host default `python3` is 3.8.5 and cannot install these pinned packages). Python geometry dependencies are pinned in `requirements.txt` (Shapely 2.1.2 and pyproj 3.7.2). The reconciliation measures intersection-over-union in EPSG:6933; `make_valid` is applied only for comparable area measurement and each row records invalidity before repair. It does not edit source or Atlas geometry. The south-Africa neighboring check uses the retained #436 API snapshot and completed #436 packet evidence.

Expected invariants: 226 unique issue IDs; 226 matched current-main Atlas locations; ID digest `75508666501c08b0aa422614a6df7518d7a442687c51639589ed400e2a2ec736`; five geoBoundaries layers (25 BWA, 10 LSO, 109 NAM, 53 SWZ, 213 ZAF); exact South Africa neighboring partition 17 + 196 = 213 with zero overlap, missing IDs, or extras. The ZAF layer check on this issue alone intentionally reports 196 sibling IDs not in #435. The issue-local coverage is in `pinned-source-coverage.json`; sibling union is in `south-africa-neighbor-coverage.json`.

Per-subject decisions and rationale: `findings/subject-assessments.jsonl` (226 rows) and its summary. Per-parent decisions: `findings/parent-assessments.jsonl` (47 rows). Per-area assessment and rationale: `findings/area-assessments.jsonl` (6 rows). Source/license/vintage/retrieval register: `findings/source-register.json`. Subject roster and exact original IDs: `findings/subject-roster.jsonl`. No script invokes GitHub mutation or writes beyond the owned packet.

# Invalid multipart prevention correction

Issue #1267 follows #920 and parent #1202 milestone 3. Original multipart members are validated together before clipping or dissolving, in the existing shortest-edge longitude domain. Periodic ±360 counterparts retain original member identities. Tiny positive overlap and shared-edge zero-area invalidity fail without an area exemption; valid disjoint members, point contacts, holes and supported dateline pointsets remain accepted. Complete baseline/candidate raw geometry is retained by the existing detector. An invalid old baseline remains blocked even if the candidate is valid.

Frozen implementation and complete control execution: `4397e0697f10432fb35004cf01324b747fb697a8`. Both retained runs contain all 29 tests, authenticate 11 whole ordinary code/input files, and have identical three-file receipts. The original replay capsules retain the old 09f557dd650098e3b6b89fab5950ac9fe5ef8809 counterexamples and original pointsets; their old success is historical defect evidence, not current approval.

Reproduce at the frozen commit with Python 3.12.14, Shapely 2.1.2, GEOS 3.13.1 and PyProj 3.7.2:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHON=/path/to/pinned/python /path/to/pinned/python test/geographic-regression.py --receipts NEW_ABSENT_DIRECTORY --code-commit 4397e0697f10432fb35004cf01324b747fb697a8
```

Run twice in distinct absent directories. The positive receipt lists expected detection/fail-closed cases; the negative receipt lists permitted non-regression cases. Actual trusted PR and two-parent combined Git candidates are exercised. Source-only research remains explicitly not-applicable and never certifies the unchanged atlas.

Additional targeted checks passed: 24 water adjudication/API/bootstrap Node tests after supplying their unchanged sparse Natural Earth and hosted catalog fixtures, plus eight shared geographic helper tests. The first aggregate Node invocation had six missing-sparse-fixture failures; this was not a geometry result. Applicable CI and independent final review remain required.

This packet supplies code prevention and synthetic topology evidence. It does not repair existing gaps, certify the entire atlas, allocate raster cells, establish release consistency, identify water or ownership, approve historical claims, or deploy production. GEOS diagnostic source-coordinate areas are square degrees, not ellipsoidal geographic measurements. No new geographic area/distance metric is claimed.

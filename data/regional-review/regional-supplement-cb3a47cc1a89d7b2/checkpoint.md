# Durable checkpoint — 2026-10-03

Issue #567, active reservation `codex-20261003-minamitorishima-5c872b56-4c5d-46c4-90b5-8bf63a4c90ed`; claim `5fd284bf-018d-4da1-a3a4-5c2216bbc454`; request `6e852b41-7925-4639-bdd8-298ff77ccafa`; branch `geography/minamitorishima-20261003`; lease through 2026-10-04T10:11:40Z. Exact owned paths are the original packet directory only. Original issue #524 is closed and its prior claim released.

Work so far: preserved exact issue #524 v5 assignment in `issue-524-scope.json`; preserved original audit bytes as `audit-v1-original.json`; labeled its v3 pin tuple historical and verified it is an actual v3 release record. `audit.json` now identifies v5 as the current assigned baseline while retaining v3 provenance. `baseline-reconciliation.json` records all release/gate/publication/hierarchy/region/envelope facts and hashes. Updated `reproduce-audit.py` validates all those pins, the exact subject, full location-to-continent chain, full 51-member NW Pacific scope, v5 envelope geometry, original source hashes, OSM relation conflict, and still-missing profile pointer (#554 remains separate).

`python3 data/regional-review/regional-supplement-cb3a47cc1a89d7b2/reproduce-audit.py` passes. No hierarchy, geometry, grid, certificate, source bytes, parent interpretation, or historical attributes have changed. The Bonin/Ogasawara relation still requires coordinated review under #275/#382.

Next: refresh main, run actual #567 lane/scope check, commit/push a single PR, pass package/scope CI and the serialized squash-merge queue, verify actual merge, release the #567 claim, and continue with another ready unclaimed bounded geography issue.

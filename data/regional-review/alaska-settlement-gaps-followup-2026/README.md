# Alaska settlement-source follow-up

Issue: [#603](https://github.com/ChengshuLi/WorldAtlas/issues/603), parent [#486](https://github.com/ChengshuLi/WorldAtlas/issues/486). This packet audits the issue's eight exact Alaska physical-fragment IDs. It is source evidence only: no membership, hierarchy, geometry, certificate, application, schema, or live-data changes are proposed.

## Result

All eight assigned subjects have a row in `assessment.json`. The parent packet screened each against 2024 Census TIGER/Line incorporated-place/CDP polygons and a USGS GNIS Populated Place query dated 2026-10-03; both screens had zero hits for each. I added a statewide Alaska Department of Commerce, Community, and Economic Development (DCCED), Division of Community and Regional Affairs (DCRA) community/locality point layer. A reproducible exact-geometry intersection of its 487 records in the Alaska query envelope returned zero records intersecting any of the eight current project polygons.

This is not evidence that the fragments contain no settlement. The DCRA source describes a Community Assistance Program eligibility class and a broad “Place of Interest” class that can include CDPs, localities, camps, seasonally inhabited places, vacant former places, and other points. The layer is a point inventory, not a comprehensive census of people or settlements, and its item metadata provides no explicit reuse license. Therefore the DCRA zero-hit screen is retained as a dated finding with restoration instructions and a response digest, but its raw response is not committed. All eight findings remain explicitly **unresolved** pending authoritative, finer-scale local evidence (for example, local government/community records or settlement polygons and dated inhabited-place information). No new work item is asserted to be unnecessary.

The assigned fragments remain pieces of their named 2018 Census-area predecessors. Census areas are statistical county equivalents, and DCRA's point categories do not define the complete inhabited extent or an administrative remainder. A point-screen non-hit cannot justify adding a remainder, changing a parent, or redrawing a fragment. The current source-derived parent chains and project polygons are preserved in the linked parent packet and pinned in `sources.json`.

## Complete scope and checks

`scope.json` pins all eight IDs and their labels. `assessment.json` records, for every ID, the full current parent chain, parent predecessor identity, geometry component/area summary from #486, both earlier settlement screens, the DCRA exact-intersection result, interpretation, and the unresolved evidence gap. The records also distinguish the ecological source identity from political ownership: a named ecozone fragment is not itself a local government.

Run `python3 verify.py` from the repository root. It verifies the pinned IDs, parent assessment, exact project polygons, live DCRA query and zero-hit result. It does not retain or overwrite source data. The DCRA service can change, so a future run may legitimately produce a different digest or hits; inspect those records as new evidence rather than treating this packet's response digest as a permanent service version.

## Source rights and restoration

See `sources.json` for canonical landing/REST URLs, provider, source and access dates, item modification date, license statement, response sizes/hashes and reproduction instructions. DCRA's own item metadata says its CDO content is informational, “as is,” and not warranted for accuracy, timeliness, or completeness; the item has no explicit open data license. No DCRA feature response bytes are retained. `verify.py` re-fetches the read-only service response. The project baseline polygons and inherited source material are not copied or modified by this packet.

## Limits and next action

This completes the bounded source review as far as the identified DCRA source can support it, while preserving the eight honest unresolved findings. A follow-up should be bounded to the same exact subjects and seek local authoritative place/community records with dated status and geometry sufficient to distinguish occupied settlements, seasonal use, former places, and no evidence. Do not infer absence from the current no-hit stack. If local review finds a candidate across a shared regional boundary, coordinate with affected neighbors and integration issue #484 before proposing any shared-boundary action. This packet does not approve Alaska or Western North America and does not enable historical imports.

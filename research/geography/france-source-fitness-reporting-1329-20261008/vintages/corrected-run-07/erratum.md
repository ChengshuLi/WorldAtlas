# Additive reporting erratum: France source-fitness packet

This correction applies only to reporting derived from the immutable complete runs in original issue #1310. It does not alter those runs or certify French boundaries.

## Corrections

- The full retained candidate relation records yield **6** candidate pointsets with no 2026 IGN whole-layer intersection, not four. The remaining candidates yield 42 intersections: 8 whole-feature covers and 34 intersections without whole-feature cover.
- The exact counts above are recalculated from all 48 complete retained candidate relation records and reconciled to the original frozen summary. The original `run-contract.json` limit phrase is stale; it is preserved unchanged.
- For all 16 complete original 2022 source contact geometries and all 16 complete current Atlas contact geometries, the retained run records comparison against the complete 333-feature 2026 IGN layer: 16/16 and 16/16 intersect; whole-feature covers are 0 and 0. The previous methods sentence understated this by describing only exact-name identity leads.
- Exact-name identity candidates are present for 15/16 contacts. Names remain leads; no one-to-one identity or boundary crosswalk is inferred.

## Preserved source meaning and limits

- The complete retained geoBoundaries source body is 6755489 decoded bytes, SHA-256 `318606bceafa5fea93412c66438f333e35bad41079dc756270e961a213a4d6a0`, and contains 320 unique French `ADM3` records. The pinned original transport receipt records retrieval 2026-10-06T22:17:21.962366+00:00 through 2026-10-06T22:17:22.894497+00:00 from https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09/releaseData/gbOpen/FRA/ADM3/geoBoundaries-FRA-ADM3_simplified.geojson. Its corpus catalogue records represented year 2022 and Etalab Open Licence 2.0 metadata; geoBoundaries separately states CC-BY 4.0 for derivative products. The source record itself does not provide a parent ID in its feature properties. These recorded terms do not resolve the underlying-source rights chain or establish legal boundary authority.
- The comparison layer is `ADMINEXPRESS-COG.2026`, edition 2026-01-01, retrieved 2026-10-07. Its exact 156,850,437-byte source is restoration-only because it exceeds the repository 32 MiB file limit; this erratum reuses the complete retained run relations and does not substitute a clipped or filtered layer.
- The retained source-fitness dispositions remain 11 compatible recorded subjects, 24 partial/unbound cases, 11 no-compatible-intersection cases, and 2 outside-domain cases. These remain source-fit dispositions, not factual boundary conclusions.
- The inherited physical summary remains 46 mapped-land-support records, 2 outside-L1 records and 48 unverified surface statuses. Physical-source license, coverage, observation dates and physical authority remain unresolved.
- This work independently verifies the arithmetic and identity correspondence of the retained complete run records and checks all 16 original contact features against the authenticated complete 2022 source bytes. It does not rerun the 156 MB 2026 spatial overlay, independently establish its intersections, certify France, change any parent/boundary, approve source rights, or complete original issue #1329.

## Reproduction and exact inputs

- Both frozen full result files are byte-identical, SHA-256 `b8566a52df9c2ed1e56f679434439567886cebaa43bc135cf08b66058b3ce7af` (820804 bytes each). The new CLI binds this whole hash, the issue-declared pins, the complete original source, its own code hash and the shared pinned writer helper in each fresh publication receipt.
- Run the documented `report.py run --repo <checkout> --vintage <fresh-name>` command twice with distinct fresh names. The control CLI records adverse cases separately; all failed and partial attempts remain failed.

Sources retained by original issue #1310:

- geoBoundaries France ADM3 simplified source, pinned upstream revision `9469f09`: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/FRA/ADM3/geoBoundaries-FRA-ADM3_simplified.geojson
- geoBoundaries derivative citation and attribution terms: https://www.geoboundaries.org
- IGN ADMINEXPRESS-COG.2026 product context and French Open Licence catalogue references are preserved in the original packet README; see https://geoservices.ign.fr/ and https://www.data.gouv.fr/datasets/admin-express-admin-express-cog-admin-express-cog-carto-admin-express-cog-carto-pe-admin-express-cog-carto-plus-pe
- Source retrieval and file hashes are historical observations recorded in the original packet; no new source download occurred for this report correction.

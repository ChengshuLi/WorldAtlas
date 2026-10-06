# North Macedonia #995 retained-source method erratum

Recorded 2026-10-06 (America/Los_Angeles). This additive erratum corrects the method description in the immutable #995 packet. It does not revise that packet, its source bytes, historical dates or findings.

## Corrected method record

The exact original files are identified by their byte sizes and SHA-256 hashes in `baseline-inputs.json`, all read from merge `b6cfaada43a1e0472cd833d16733d1fd6065eaec` (PR #1009). The prior packet's `SOURCES.md` line 20 says the retained HDX geometries were transformed to EPSG:3035, tested to a 1 mm Hausdorff limit, and emitted observed distance maxima. The corresponding retained `reproduce.py` source-to-source phase instead transforms EPSG:4258 to EPSG:4326 with longitude-first coordinates, calculates WGS84 ellipsoidal symmetric-difference **area fraction**, and uses `1e-8` as a dimensionless area-fraction screen. It contains no EPSG:3035 transform, Hausdorff computation, or distance output. The old `crosswalk-results.json` does not contain those distance results.

The new offline runner checks the exact 30 whole-file inputs, the original reproducer and shared scientific helper bytes, then compares each of the 84 native source subjects once. Two separate exclusive output files reproduce the same maximum fraction, `8.050588843771585e-12`; all 84 residuals are nonzero and all 84 pass the `1e-8` area-fraction screen. Run output SHA-256: `d3d23c61368d3db4fb5acf049cfaff9f3533a1da7c37c5b96d02070d50b3fef3` (both runs, 21,617 bytes). This substantiates only the retained HDX/geoBoundaries area comparison. It cannot establish the historical undocumented computation, a Hausdorff bound, legal boundary correctness, or equivalence with any of the 84 stored Atlas geometries. The eight parents in the run report are read-only contexts.

## Evidence and reproduction

- Original source metadata: retained HDX/RIMWGE 2016 archive (CC BY is stated, version and upstream third-party rights not established); retained geoBoundaries metadata calls its ADM2 boundary vintage 2016 and asserts CC BY 4.0, while its source/terms URL is malformed. Update/build dates (2023) do not establish boundary epoch. The lineage evidence points to EuroGlobalMap v8.0 and a 2015-10-27 append; this does not prove legal effective dates.
- Completeness: 84 named HDX ADM4 polygons pair bijectively by `Name4_E` / `shapeName` with 84 geoBoundaries ADM2 features and the exact 84 issue subject IDs. The archive contains 24 CRC-valid members and 387,976 decoded bytes. These counts describe the retained source phase only.
- Retrieval: the archive and geoBoundaries files were retained in the earlier packet and are pinned at the cited commit. No source was downloaded or replaced for this erratum. Reproduction performed 2026-10-06 from those immutable Git blobs, offline.
- Reproduce: `python reproduce-retained-phase.py data/regional-review/northern-macedonia-method-995-erratum/v1/run-one.json`, then repeat with `v1/run-two.json`. Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2 were used with the pinned WorldAtlas geometry helper. Outputs are exclusive; an existing path is rejected.

## Limits and engineering handoff

No independently retained EPSG:3035/Hausdorff evidence was found. Do not cite a distance result or treat `1e-8` as millimetres. If that historical distance is needed, create a separately dated reproduction with an explicit CRS, axis order, distance implementation and units; preserve the resulting new evidence without relabeling the 2016 run. The prior packet's area result may remain, but its method prose needs this correction. The mismatch and all resulting uncertainty are recorded here; original `SOURCES.md`, code, results, Atlas geometry/IDs, release pins and parent assignments remain unchanged.

This is a research erratum only: it does not certify the 2016 source epoch, validate any legal boundary, prove any stored Atlas geometry, approve a regional branch, or authorize source restoration, imports, publication or deployment. A separate engineering change would be required to edit the old packet's prose; this evidence-only PR intentionally preserves it.

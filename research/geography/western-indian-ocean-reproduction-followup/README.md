# Western Indian Ocean reproduction repair

**Issue:** [#662](https://github.com/ChengshuLi/WorldAtlas/issues/662), follow-up to [PR #637](https://github.com/ChengshuLi/WorldAtlas/pull/637). This packet repairs the reproduction and reporting path; it does not revise or approve the Western Indian Ocean geography.

## Frozen inputs and scope

The exact 144 subject IDs come from the issue scope committed with PR #637 (`f592b3d8b72f40036218803d2c70c733112e4d37`). Reproduction of the original measurements uses geographic baseline `3d87880a274269b549a847333c35474e065c07f3`, the commit recorded in that packet's evidence manifest. Both commits are ancestors of the main branch used to prepare this packet. The manifest binds the eight original baseline files and maps each subject to its containing part. The runner additionally verifies the full world index and SHA-256 pins for all 36 indexed geography files (34 numbered parts plus two additions) before scanning them for duplicate assigned IDs.

The source scope, source descriptors, original scripts, and original result bytes are pinned separately to PR #637's exact merge commit. Source data remain retained in that earlier packet; this PR records exact restoration paths and hashes and does not duplicate or alter those source files. The prior packet's README is preserved here byte-for-byte as a small historical metric input. Original result JSON remains untouched.

## Reproduction results

The corrected scripts reproduce the same numeric measurements and dispositions as the retained original outputs: zero changed values at the stated tolerance. The 139 geoBoundaries comparisons include 119 Madagascar ADM2, 12 Mauritius ADM1, and 8 Seychelles ADM2 features; 28 exceed the 5% overlay triage threshold and the maximum symmetric difference is 77.419521%. The COD-AB comparison matches all 119 assigned Madagascar locations to its 120 ADM2 source units and retains the 24 ADM1 source regions, including one unmatched source district. The source union versus current location union symmetric difference remains 0.149449%.

No compared original source or current geometry needed repair in this run. This means the unsupported geometry-method branch was latent for these inputs; it does not mean the repaired code path is unnecessary. The invalid bowtie control confirms `shapely.make_valid` works, records raw validity before repair, and leaves the supplied geometry unchanged. Invalid repair results outside Polygon/MultiPolygon are rejected.

`geometry-comparison.json`, `madagascar-current-COD-AB-review.json`, and `metric-comparison.json` are separate reproduction-vintage candidates. `compare-vintages.py` compares them with immutable historical outputs. All output creation is exclusive; `--check-only` calculates and validates without writing.

## Source reference limits

- geoBoundaries 2020 Madagascar ADM2, 2017 Madagascar ADM1, 2017 Mauritius ADM1, 2020 Seychelles ADM2, and 2017 Comoros ADM1 extracts: [geoBoundaries](https://www.geoboundaries.org/) and upstream dataset citations/terms in the retained `sources.json`. The Madagascar ADM2 record cites BNGRC/OCHA ROSA and CC BY 3.0 IGO; the 2017 ADM1 extracts cite OSM/Wambacher and ODbL 1.0; the Seychelles ADM2 record is CC BY 4.0. Each exact retained file hash is in the evidence manifest and prior packet source registry. These administrative vintages do not establish current legal boundaries, physical land presence, or political ownership.
- Natural Earth 1:10m admin-1 extract: [pinned Natural Earth source commit](https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19); public domain with requested attribution. Its undated reference features identify comparison subjects only.
- OCHA/HDX Madagascar COD-AB: [canonical dataset](https://data.humdata.org/dataset/cod-ab-mdg), CC BY-IGO. The retained package was reviewed 2026-07-06 but the limits state `valid_on` 2018-08-10. The source is an administrative comparison, not a 2026 legal-boundary determination. Restore the full source archive using the URL and member hashes in the prior packet's `sources.json`; exact scoped ADM1/ADM2 bytes are already retained at the pinned PR #637 commit.

The original #482 review remains 99 justified and 45 explicit insufficient-evidence location assessments, with separate provenance for 47 provinces and 8 areas. This reproduction does not change those findings, settle the named source gaps, or authorize shared-boundary changes, publication, or historical imports.

## Commands

```sh
python research/geography/western-indian-ocean-reproduction-followup/reproduce-geometry.py --check-only
python research/geography/western-indian-ocean-reproduction-followup/compare-current-codab.py --check-only
python research/geography/western-indian-ocean-reproduction-followup/reproduce-geometry.py
python research/geography/western-indian-ocean-reproduction-followup/compare-current-codab.py
python research/geography/western-indian-ocean-reproduction-followup/compare-vintages.py
python research/geography/western-indian-ocean-reproduction-followup/test-reproduction-controls.py
node scripts/evidence-quality.mjs research/geography/western-indian-ocean-reproduction-followup/evidence-quality.json
```

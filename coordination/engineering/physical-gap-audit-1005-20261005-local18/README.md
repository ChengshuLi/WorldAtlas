# Independent physical land before water, #1005 part 1

This detector preserves the old water-screened detector and every original result. It computes the unchanged Natural Earth physical-land reference minus unchanged native location polygons before any water screening. Every positive planar-area candidate survives. Original point/line and clipping remnants have separate lossless outputs. Modern lake overlaps and invalid lake bounds are diagnostics; neither excludes a candidate nor blocks discovery. Invalid physical land/location bounds and actual geometry-operation failures remain explicitly unchecked tiles.

This is discovery, not factual water classification, territorial assignment or repair. Original coordinates, source files, IDs, hierarchy, grid and release index remain unchanged. Exact location contacts retain their geometry and source metadata; point-only and positive-area numerical flags remain distinct. There is no nearest-neighbor assignment, snapping, tolerance waiver, buffer, simplification, minimum-area discard or MakeValid. Geodesic measurement failure leaves the complete positive-planar shape and an explicit error. Natural Earth 1:10m cannot certify fine shorelines or a complete island inventory.

Use Node24 and Python dependencies pinned in requirements.txt (this stage needs numpy, shapely and pyproj). The meaningful controls run through the ordinary test runner:

```sh
node --test test/physical-gap-audit.test.mjs test/geographic-gaps.test.mjs
```

Commit the exact executed code before generation; the runner verifies its ordinary committed bytes. Generate twice into distinct new owned vintages:

```sh
python3 scripts/audit-physical-gaps.py \
  --commit 548c5f89f00271050823076a84695bb41e1b8454 \
  --water-reference coordination/engineering/coverage-gaps-907-20261005-local01/sources \
  --water-commit ff566eab31ef072084c548f67dee8ee727ab3d47 \
  --output coordination/engineering/physical-gap-audit-1005-20261005-local18/detection-v1
```

Repeat with a fresh detection-v2 path. Compare every complete candidate/residue file by relative filename, exact bytes and SHA256, and every report field after replacing only the output-vintage prefix. Reports retain all checked/unchecked tiles, including empty tiles and invalid-water diagnostic bounds. No successful worldwide result or two-run equality is claimed until both actual runs finish and their complete products are compared.

Parts 2 and 3 remain required: complete connected components; lossless relationships to every old fragment/component and all five unmeasured shapes; all three formerly blocked tiles; exact-contact/source-vintage/global issue partitions and prioritization of every component, including tiny and no-contact cases. The global repair goal also requires source-backed coordinated factual repairs, release/certificate/content revalidation and eventual verified delivery. This packet does not change geography, default grid selection, live data or hosting, and does not request publication.

The initial detection-v1 run at e67eeafc1aa130aa5c1a6d1222d39116625fd003 completed all2160tiles, finding96963positive-planar fragments and343remnants, with no unchecked land/location domain. It is retained as an earlier diagnostic vintage, not final acceptance. Preliminary independent review identified three corrections: real shoreline on an aligned tile edge must survive; any nonfinite original coordinate makes its unchecked extent unknown even if computed bounds are finite; clipping residues must name their original land feature/location source. The corrected detector adds those controls and source identities. New corrected generations and their exact comparisons remain required; the earlier run is not overwritten or retrospectively certified.

Final generations `detection-v4` and `detection-v5` at `b6e0d0d21cfd6dde68c3c292c9513d3a24896a11` completed all 2,160 tiles: 96,963 positive planar fragments, 343 remnants and five geodesic measurement uncertainties. Every output file is byte-identical between those two runs. Every original candidate/remnant geometry and identity is unchanged across all five retained generations. Final shoreline diagnostics use the whole original physical-land union boundary, retaining actual coast on tile edges while excluding internal seams between land-reference features. Earlier diagnostic vintages remain unapproved and immutable.

`input-envelope-v1` is a later lossless transport of all 45 complete original files (219,022,871 original bytes); the scientific runs consumed the original Git files, not these later envelopes. The required regression restores every original byte, checks its immutable Git blob, checks complete source-roster closure and verifies all five scientific products. `execution-code-v1` retains complete archived code snapshots, also checked against original execution commits. The mandatory upstream evidence manifest accounts for all original files and envelopes under the existing byte budget; it is not an extract or a waiver. Source authority and actual water truth remain unverified.

```sh
node --test test/physical-gap-audit.test.mjs test/lossless-audit-inputs.test.mjs \
  test/physical-audit-ledger.test.mjs test/physical-audit-evidence.test.mjs
python3 scripts/validate-physical-audit-evidence.py \
  --manifest coordination/engineering/physical-gap-audit-1005-20261005-local18/evidence-quality.json
```

The full-product gate verifies source validity/unknown diagnostics, identities, tile accounting, complete products, measurement uncertainty and byte equality. It does not independently repeat every worldwide geometry difference operation or grant factual approval. Connected-component crosswalks, global investigation partitions, factual repairs and delivery remain required subsequent work.

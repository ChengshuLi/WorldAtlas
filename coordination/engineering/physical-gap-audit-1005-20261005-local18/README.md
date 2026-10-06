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

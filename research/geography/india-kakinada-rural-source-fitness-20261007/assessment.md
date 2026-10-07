# Kakinada (Rural) source fitness assessment

**Scope:** one complete source-fitness family, one original physical component and one current Atlas contact. This records evidence only. It does not approve a boundary, parent, land or water status, or authorize data changes.

## Disposition

The retained geoBoundaries `IND-ADM3` 2018 feature with `shapeID=7132399B91549871673633` is a strong geometric match for the frozen physical gap component: it is the sole positive-area compatible source record, and its polygon covers the full component in a direct planar overlay of the stored longitude/latitude coordinates. This supports source availability and geometric correspondence. It does not establish current administrative validity, legal boundary authority, or the correct present-day hierarchy. **Source fitness remains unapproved pending provenance/reuse verification and an authoritative current administrative record.**

## Identity and scope

The complete family roster contains only `physical-component:81713fe9120ee5e30d3e0e4ceb1785ca890e6fb6327a4939026c276d448141eb` and its one compatible contact, `atlas:local:IND:7132399B91549871673633` (Kakinada (Rural)). Its recorded current parent is `atlas:province:IND:d7cc05599eb6`. The original component geometry digest is `5c68774784a2d75180bd200e2a7a2d34ea900a32d8ae132268292c98bd9244f7`; full original component-feature digest is `26d4ada18b01926a37bd8cc9f6e9d1d34a32d4ede5de1a9e5e1db0554af8a211`. The component was recovered uniquely from the whole custody payload pinned in `evidence-quality.json`, at original commit `79ffb2ed04702e16f009e4675a8d74ef9bd09d4f`.

The retained source collection is pinned by compressed bytes and metadata. It contains 6,822 features; exactly one feature has this shape ID and name, with `shapeType=ADM3`. Metadata identifies the product as `IND-ADM3`, represented year 2018, canonical type “Sub-District,” and attributes the boundary source to Pathways Data Pvt. Ltd. / lgdirectory.gov.in. It reports ODbL 1.0 and a source data update date of 2023-01-19; the retained collection contains 6,822 features while metadata reports an administrative unit count of 6,836, a 14-unit inventory discrepancy whose cause is unresolved. The pinned geoBoundaries release commit is `9469f09592ced973a3448cf66b6100b741b64c0d`, with build date 2023-12-12. These are provider-reported provenance and terms, not an independently verified grant or proof that the polygon was legally adopted by a government authority.

## Geometry check

I decoded the exact original component feature, retained 2018 source feature, and current Atlas contact. All three geometries are valid Polygon geometries. Using Shapely 2.1.2 on the coordinates as stored, without CRS transformation or snapping:

- The 2018 source polygon covers the complete physical component (`source.covers(component) = true`); `component - source` is empty.
- The source polygon is much larger than the component; `source - component` is non-empty. This is consistent with the component being a small gap contained inside an administrative polygon, not a proposed boundary reconstruction.
- The current Atlas polygon is not topologically equal to the retained source polygon. Its symmetric difference from the 2018 source is non-empty (about `0.0000782053` square degrees in this direct planar calculation). The source and current polygons share bounds but differ in shape. Neither full polygon covers the component in the current version; this is consistent with the tiny component not being part of the current stored contact geometry.
- The comparison dataset independently records one compatible source feature, complete component coverage, and an empty component-minus-source result. The direct check above confirms that coverage from the pinned raw geometries.

The area figures in square degrees are only overlay diagnostics in raw longitude/latitude coordinates. They are not area estimates on the ground. The inherited priority area (`799.9893 m²`) and inherited fragment area are not new measurements.

## Provenance, time, and authority limits

The geoBoundaries source is a 2018 represented-vintage administrative dataset assembled by geoBoundaries, with the exact source attribution and reported ODbL term stated above. The Government of India Local Government Directory currently describes itself as a unified and authoritative directory of land regions and local governments and says it maintains updated administrative lists. That current directory context makes it a promising verification route, but it does not prove that this retained 2018 geometry was supplied, approved, or legally authoritative. No current official geometry or legal order for this exact Kakinada (Rural) boundary was acquired for this assessment.

The Census of India 2011 catalog records Kakinada (Rural) as a sub-district, separate from Kakinada Urban. This supports historical name/type existence only. A 2001 Census administrative map also depicts Kakinada Rural and Kakinada Urban, but is too old and not a current boundary authority. Neither record resolves current parentage, boundary vintage, or legal status.

Current Atlas metadata ties the contact to the retained geoBoundaries member and cites reference year 2018. It records source footprint share `1.007199`, framework overlap `1.0`, greatest-overlap parent East Godavari at 100%, and a separate regional match. Those are inherited matching outputs, not an administrative ruling. The current hierarchy and the recorded parent relationship remain subject to the existing semantic-review state.

## Uncertainty and follow-up evidence

The family summary says the component touches a reference shore, while the original physical component feature in the pinned custody payload says `touches_reference_shore=false`; I retain both values as a source-record inconsistency. Water status remains unverified. Cause remains unknown. The 2018 polygon's coverage does not settle whether the component is land, water, a coastline artifact, or a later administrative change.

Before approving source fitness, obtain a current official LGD or state-government record for Kakinada (Rural), including its code, parent, effective date, geometry or legal schedule, and reuse terms. Reconcile that evidence against the 2018 source and current Atlas shape; then separately resolve the shoreline/water and parent uncertainty. Do not infer approval from source coverage alone.

## Source references

- [Pinned geoBoundaries IND-ADM3 metadata](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3-metaData.json)
- [Pinned geoBoundaries IND-ADM3 simplified source](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/IND/ADM3/geoBoundaries-IND-ADM3_simplified.geojson)
- [Government of India Local Government Directory](https://lgdirectory.gov.in/)
- [Census of India 2011 Andhra Pradesh H-03 catalog](https://censusindia.gov.in/nada/index.php/catalog/10013)
- [Census of India 2011 A-01 catalog](https://censusindia.gov.in/nada/index.php/catalog/42526)
- [Census of India 2001 East Godavari administrative map](https://censusindia.gov.in/nada/index.php/catalog/27672/download/30841/DH_28_2001_EGOD.pdf)

## Reproducibility and bounded evidence

The initial byte-identical pair is retained at `verification/historical-narrow-runtime-unbound-20261007/` as historical narrow proof only. It authenticated the complete source/family joins but did not authenticate runtime callable bodies, exercise directed geometry-method branches, guard candidate file symlinks/size before reading, or retain per-run execution receipts. It is not the accepted runtime/method result.

The corrected pair was run as two separate CLI processes against one frozen closure (`closure-freeze.json` and `verification/execution-reproducibility.json`). Both exited 0, produced byte-identical results, and ran from the recorded working directory with the exact invoked venv interpreter, its resolved binary, and start/end UTC timestamps. The closure binds execution commit `307cf801644076b347da4100c989983d37380c5c`, whole interpreter/native geometry runtime files, loaded Shapely import-file hashes and callable body fingerprints. The routed family join still authenticates the full 8 MiB decoded containing shard, the exact 5,040-byte row at byte offset 6,232,978, and its complete one-member component/contact/count/status relation. The whole routed row hash is `b2ac5aaf19131ff0cf778c56f56fb0a8eae60a6d1b4198bfeb5b80be897e2fbd`; the independent complete component comparison row hash is `3e2e95f7d9ff4ce6c17ed5f3acf81c35d5b8c44750379f17fd1b027064befa9c`.

The actual CLI boundary suite rejects 22 source, family, symlink and oversize cases, including coherent foreign source/feature and component/context rebinds. A separate actual-entry geometry control binds the coverage, difference, symmetric-difference and validity outputs to a directed positive fixture and rejects uncovered source, current contact coverage, and invalid geometry. The detailed execution and control receipts are listed in `evidence-quality.json`. Earlier preflight failures and the first narrow pair remain historical and are not counted as accepted runs.

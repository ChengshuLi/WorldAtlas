# Norway seven-component physical-applicability evidence

This packet records bounded source custody and one exact seven-case geometry measurement for issue #1510. It preserves the #1492 identities and all 15 selected candidates, 400 family members, and 36 positive-length neighbors. It changes no Atlas geography, hierarchy, database, or publisher output.

## Result

The seven candidate-minus-target geometries reproduce their pinned #1492 receipts. The run emitted seven case rows and 252 neighbor rows: seven own-target preservation rows plus 245 measured relations to the other members of the 36-neighbor context.

The measurement does **not** establish physical applicability. All seven cases remain unknown for component class, independent water or ice status, territorial authority, history, cause, rights, and ownership. No correction proposal is made.

Kartverket's retained Sjøkart Dybdedata WFS is saltwater-only and dynamically served. Its Kystkontur layer represents mean high water, but the captured records expose no positional-quality or coastline-category property. The Landareal chart product and coastline therefore provide source predicates, not a survey-grade land/water truth. Uncovered area is not classified as water.

The exact run found three invalid Landareal source polygons and excluded them without repair. Their coordinate bounding boxes flag Dønna and Sortland, so those cases have additional unresolved source overlap. The other five have no invalid-source bbox overlap. The valid Landareal intersection fraction is recorded per case, but is not interpreted as a physical classification.

## Topology and controls

- All seven added-area geometries equal the pinned #1492 receipts.
- 252 of 252 relation rows are present, including seven preserved own-target rows and 245 evaluated neighbor relations.
- The recorded `parent_coverage_pass` tests whether the *entire projected proposed union* `T ∪ C` is covered by the pinned simplified 2022 ADM1 parent. It reports false for all seven. The parent feature ID is present in the pinned ADM1 source; this result does not indicate an ID-join failure. It is distinct from #1492's prior predicate, which tested candidate component `C` alone against its recorded parent.
- Strict no-loss is exactly empty for five cases. Lurøy retains a measured difference area of `3.0329804438897386e-9 m²`; Vefsn retains `1.1650589381911533e-7 m²`. Both are reported as failed strict predicates. No tolerance, snapping, repair, or rounding is used to convert them into passes.
- Source validity, CRS/datum, projected measurements, per-case shoreline predicates, and all unresolved limits are in `physical-applicability-v1.json`. The tiny strict no-loss residuals are exact results of the projected geometry operations; they are not erased or converted to passes. A separately evaluated raw longitude/latitude set-preservation predicate is not present in this run.

## Reproduction receipts

`geometry-run-admission-004.json` records live memory, storage, process, source-size, runtime, and coordinator admission immediately before launch. `geometry-run-runtime-004.json` records the bounded process result; peak sampled process-group RSS was 172,687,360 bytes, elapsed time 1.135 seconds, exit code 0, with an empty terminal process group. `geometry-run-console-004.json` retains stdout and stderr. Failed pre-result attempts 001–003 are preserved alongside them; they emitted no geometry result.

The producer is `measure_norway_physical.py`; the supervisor is `run_geometry_phase.py`. `bounded-measurement-plan.json` pins the exact source and geometry inputs. The 14 raw WFS responses and their byte/hash/member custody are under `sources/sjoekart-dybdedata-wfs-20261008/`, checked by `verify_sjoekart_capture.py`.

`validate_result_controls.py` runs after the measurement and does not rerun GIS. Its positive control checks seven subject identities, exact 15/400/36 context, seven #1492 area-receipt matches, and all 252 relation rows. Its negative controls confirm that a shortened family roster and a missing neighbor relation are rejected. These controls validate ledger closure and scope; they do not establish the truth of any physical classification.

## Limits and contract note

The source evidence cannot resolve registration accuracy or all shoreline-sensitive distinctions. A failed parent predicate and the two nonempty strict no-loss residuals also prevent treating this run as a clean topology acceptance. These outputs support review and follow-up only.

The issue prose and embedded `worldatlas-work:v1` scope now agree that GIS requires GEO5 and the admitted root numerical cohort to be terminal, no overlapping root GIS, and a fresh live combined RAM/storage admission; completion of the entire worldwide replay is not required. The issue also now specifies additive predicates in original coordinates: exact gain, no original target loss, gain support, and no new parent exclusion or neighbor overlap. Run 004 predates that clarification and reports only the projected union parent predicate and projected no-loss diagnostic. Those raw-domain additive predicates remain unmeasured; no correction proposal is made.

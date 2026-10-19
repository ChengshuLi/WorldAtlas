# TUV45 retained-geometry correspondence and unresolved disposition

This packet supplements the original `gb-TUV-ADM1--repair-evaluation` contract for all 45 exact native land keys in 16 half-open intervals. Every exact tuple `(y, x, recorded owner, source feature, land)` is proposed as a documented-unresolved exception, not a repair. `accepted` remains false; accepted repair cells, accepted exception cells, repair credit, and exception credit are all zero; all 45 cells remain held.

## Retained evidence and limits

The pinned OSM/Wambacher 2017 ODbL source-census archive geometry classifies all 45 original cell centers inside their named source feature. The distinct retained regional-review GeoJSON has matching declared CRS/source metadata/vintage labels, but classifies 42 centers inside the named feature and three outside all eight retained features. Those divergent keys are `(136550, 261216, 43466, 59797)`, `(136973, 260982, 43461, 59798)`, and `(136978, 260982, 43461, 59798)`. Neither scan has a center-boundary tie. These are center classifications, not whole-cell containment or proof of current applicability.

The unresolved question for each of the 45 tuples is whether the retained 2017 source view, or a documented dated successor/crosswalk, is applicable to the recorded owner at that exact native location. The packet preserves all 42 agreeing observations and all three contrary regional-review observations. The source identity is known; its present applicability is not established.

The geometry uses OGC:CRS84, width 262166, with center longitude `360*(x+0.5)/262166 - 180` and center latitude `atan(sinh(pi*(1 - 2*(y+0.5)/262166)))*180/pi`. The project method classifies centers only. The retained metadata identifies `OpenStreetMap, Wambacher`, boundary year 2017, ODbL 1.0, and its update/build dates. The geoBoundaries citation names a project contact, not a per-feature OSM/Wambacher editor.

The complete candidate-contact check is bounded to pinned source-candidate block 033 and finds only the three expected feature/owner pairs for these 45 keys, with no additional candidate feature or foreign owner in that block. Physical support for the same 45 keys is 45 land and 0 inland water. The package has `source_relative_cells=0`; 101 other same-block source-relative cells are outside this contract. Issue #615 concerns Niulakita/Niutao and is excluded; its evidence does not transfer to Nui, Vaitupu, or Nukufetau. Administrative polygons are not sovereignty evidence.

## Selected-owner receipt and disposition

The exact selected-owner observation is durably published at [PR #2536 receipt comment](https://github.com/ChengshuLi/WorldAtlas/pull/2536#issuecomment-6261850166): 34,567 bytes, SHA-256 `b3611a1d61727baddb1b8a716bd2b50bb0a3ab1ea7cd6b9bd448a2d8f8feec97`, data head `2819b7231c24217511155c43c32f704597c07422`, reader code commit `21a38f0b531c8c647467f3ddc75043b138e7608d`, exact package `gb-TUV-ADM1--repair-evaluation`, and query SHA-256 `52a8b53b8ecd69ff8ba60b20d7c69cf737a622a45248732057efc7a4c7e2aff8`. It reports base/additive/effective owners `0/0/0` for all 45 cells, 45 unassigned, and zero overlaps. The receipt consumes normative native latitude bytes from `coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz` at `5b32388df0501b013ac9a3ba97864932db493d59` (compressed SHA-256 `ab0becdda100da3473d7bb5d34ccda6510aa1c0490c407082072c7201ad1e147`; decoded SHA-256 `66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23`). This binds the native center-latitude input; it does not validate source polygons, full-cell intersections, or current applicability.

The receipt's selector, sidecar, patch, and ledger Git blob IDs were independently compared at PR base `77609a1f159bfee954e52d48a883c5fe3e4b59f5` and data head `2819b7231c24217511155c43c32f704597c07422`; all four match. The exact pins and receipt binding are recorded in `geometry-correspondence.json`. This is a selected-owner observation only, not qualification or acceptance.

### Documented-unresolved acceptance

Issue #1881 provides a precedent for accepting documented unresolved dispositions without a positive assignment; its accepted 170 outcomes earned zero repaired cells and did not close the package. For TUV45, acceptance requires an independent exact FINAL remote-head review and explicit acceptance of these 45 documented-unresolved original tuples under their contract. The applicability question may remain unresolved. Until that review and acceptance occur, this proposal is not accepted, all 45 remain held, and every credit count remains zero.

### Separate prerequisites for any repair

A future positive repair requires a dated applicable source/version or documented successor/crosswalk for each exact key, together with the original contract's source, physical, contact, selected-native, and independent acceptance requirements. Any proposed repair for the three divergent keys must also explain the two retained geometry outcomes. This packet does not make an owner assignment, alter geometry, adopt a source, determine legal status or sovereignty, or close the package.

## Scope exclusions

Do not include the 101 other same-block source-relative cells, the separate larger physical scope, or issue #615's Niulakita/Niutao evidence in TUV45 counts or conclusions.

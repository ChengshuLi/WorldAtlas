# #972 exact-boundary engineering preflight — 2026-10-06

Read-only, scratch-only engineering investigation. No owner assignment, legal-water inference, release audit, claim, tracked edit, PR, deployment, or provider/database operation. The persistent goal was unbudgeted.

## Executed evidence

Pinned original Git commit `1ba7ef86a046db62c2c19d731faf8118e6cee124` in WorldAtlas common repository. All twelve whole original source byte lengths and SHA256 pins independently verified against the retained brief. Original compressed gap shard hash verified; original gap geometry compact JSON hash recomputed as `cfc1adf66c9f064a23eb937995527b14e7ebb8ec9ddaaf5db97db9c1637c2567`. Runtime: author A's pinned Python 3.12.14, Shapely 2.1.2, GEOS 3.13.1, PyProj 3.7.2 / PROJ 9.5.1. CRS84 source endpoints projected to EPSG25829 with always_xy. Source coordinates and existing four-way partition remain untouched. Pre-generation disk check: 27 GiB available.

`probe.py` enumerated 64,957 original nonzero source segments and all 65 gap edges. Bounding-box candidates were filtered by exact rational segment intersections and exact parameter ranges. It found 204 incidences, representing 198 unique rational crossing coordinates. Every incidence has at least one non-dyadic coordinate. Fractions interpret the projected IEEE64 endpoints exactly; this does not claim an exact transcendental geodetic projection or ground truth.

Every one of the retained 88 outside output vertices was traced to an exact gap/source crossing with original path, feature key, ring/segment index, geographic/projected endpoints, rational intersection, and parameters. None of those 88 Float64 vertices is exactly on its original gap segment or traced original source segment. For 74, the four-way vertex equals both the nearest Float64 rounding of the exact crossing and direct GEOS intersection of the two original segments. For 14, it differs by up to 7 x-coordinate ULPs / 1 y-coordinate ULP. `stages.py` resolves all 14: the actual intermediate operand boundary segment has at least one endpoint off the original source segment under exact arithmetic; the exact intersection of that derived segment with the gap rounds precisely to the retained output vertex. A direct GEOS intersection also reproduces each of those 14. The first source union followed by Portugal-minus-Spain / Spain-minus-Portugal / both / combined operands introduced intermediate rounded nodes; repeated clipping propagates their altered segments. Full per-vertex predecessor evidence is retained in `stage-provenance.json`.

The rational boundary-splitting prototype emits all original corners and every exact source crossing as numerator/denominator nodes. It creates 263 gap boundary subsegments with zero exact collinearity/order failures, preserves all 65 original edges as the same exact point sets, and has an exactly identical rational signed area. Two complete `probe.py` runs produced byte-identical `report.json` and `rational-boundary-split.json` (receipt in `reproducibility.json`). This is an executed exact boundary preservation prototype, not a full rational face overlay.

## Meaningful counterexample and impossibility limit

`verify.py` executed GEOS on G = triangle [(0,1),(1,-1),(1,1)] and P = triangle [(0,0),(1,1),(0,1)]. G∩P and G−P are valid; pairwise intersection area is zero; assembled union is valid. Union.equals(G) is false while both directional GEOS differences are empty. The introduced vertex is (Float64(1/3), Float64(1/3)) and G.covers(vertex) is false. This reproduces the retained partition's pathology with small integer endpoints.

The mandatory crossing of the unchanged segments (0,0)–(1,1) and (0,1)–(1,−1) is uniquely (1/3,1/3). Every finite Float64 is dyadic, so no Float64 coordinate pair can represent that crossing exactly. The nearest exported point satisfies y=x but has exact residual 2x+y−1 = −1/18014398509481984. The real pinned source-gap crossings exhibit the same non-dyadic obstruction. An explicit ordinary Float64 polygon face mesh that nodes these unchanged segments at their mathematical intersections cannot meet exact preservation of both sets of segment incidences. This is not a proof that every possible data representation is impossible, nor a claim that equals alone proves all other required properties.

## Practical engineering recommendation

Keep unchanged original source and gap geometries as authoritative inputs to the numerical diagnostic. Implement a rational planar arrangement with original-segment IDs, rational node parameters/coordinates, exact incidence and ordering, rational face winding/coverage labels for all four classes, and complete lower-dimensional/remainder ledger. The executed rational boundary-split artifact can supply its gap boundary nodes, but the full source/source intersection arrangement, face assembly, member incidence, exact pairwise disjointness and reconstruction checks still require implementation and tests.

If the consumer must retain Float64 GeoJSON/GEOS materialized faces, treat export as an approximation with a typed exact-preservation failure receipt. Do not approve it as an exact repair, and do not clear these failures through epsilon, snapping, buffering, MakeValid, vertex removal, area-only equality or source-accuracy waivers. A practical alternative for a read-only diagnostic is to retain G intact and expose symbolic region predicates G∧P∧¬S, G∧S∧¬P, G∧P∧S, G∧¬(P∨S) backed by exact source segment arithmetic rather than pretend the materialized Float64 faces preserve the unchanged boundary. This representation alternative is a next engineering step, not an implemented production solution.

Source/legal/geography limitations and root's centre classifications remain separate: no reconciliation of five both / one neither sourcepoint cases and no authority or owner proposal arises from this numerical investigation.

## Files

- `report.json`: full pinned input/runtime and 88 original-segment provenance records.
- `rational-boundary-split.json`: executed exact rational boundary nodes.
- `verification.json`: direct original-segment comparisons, ULP ledger and controlled full partition counterexample.
- `stage-provenance.json`: all 14 intermediate-segment predecessor reproductions.
- `reproducibility.json`: two-run byte identity.
- `probe.py`, `verify.py`, `stages.py`: actual executed scratch producers.

## Existing GeoJSON-number acceptance contract

With the current requirement that exported ordinary GeoJSON numeric face vertices preserve exact incidence on all unchanged projected source and gap segments, this preflight finds a genuine representational blocker. All 198 unique mandatory rational gap/source nodes have a non-dyadic coordinate. Retaining original corners is possible (and executed); representing every new mandatory node exactly as Float64 numeric coordinates is not. Exact symbolic source-segment provenance cannot silently make a deviating materialized Float64 edge exact. A rational certificate records the mathematical segment/node arrangement, while the numeric export remains a different approximation. No source-accuracy allowance changes this statement.

A remedy requires an explicit contract change: either (1) allow rational numerator/denominator coordinates or an exact symbolic segment/parameter sidecar to define accepted geometry, with ordinary GeoJSON used only for display; or (2) accept an unchanged-original-geometry + exact symbolic region predicate diagnostic, with normative cell membership evaluated from originals and the rational certificate, and cease requiring materialized Float64 clipped faces to be the exact acceptance geometry. If unchanged literal numeric GeoJSON and exact incidence both remain mandatory, this packet demonstrates the blocker and must fail that acceptance gate. This is not a proposed waiver.

Normative cell membership and geometric reconstruction are distinct checks. The current root preview counts (21,325 Portugal-only, 244 Spain-only, 5 both, 1 neither among 21,575 strict-gap centres) remain sourcepoint evidence, not an owner proposal, and the five both / one neither remain unknown. Evaluating those centres directly against unchanged original segments avoids using rounded partition vertices as membership authority, but does not prove the materialized Float64 face boundaries are exact. This preflight did not rerun or assign those centres.

`runtime-hashes.json` records SHA256/byte lengths of the invoked resolved Python executable, Shapely/GEOS binaries, PyProj/PROJ binaries and projection database where present. `manifest.json` records every scratch code/report byte hash; the retained root brief and source pins identify all original inputs without relabeling them as new source packets.

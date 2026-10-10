# Private future indexed exact-source feasibility — 2026-10-06

This is a private feasibility experiment alongside #1188 PR1190, with no new claim,
tracked changes, second PR, owner assignment, materialized-face acceptance or repair.
PR1190's reviewed head remains unchanged. The generic merged helper's current limits
remain truthful; this private execution does not silently extend that contract. A later full normative-native consumer must re-read/validate every native part and original owner registry and recompute centre completeness; byte-verifying this retained preview is not a replacement for that complete consumption.

## Actual inputs and execution

All twelve original whole-file inputs were independently reverified against Git
commit 1ba7ef86a046db62c2c19d731faf8118e6cee124 and their original SHA256/byte pins.
Total original source bytes: 8,517,055. Original gap shard hash verified unchanged.
The retained root native-centre report and compressed/decoded 21,575 point rows were
whole-byte verified. All 63 native original receipts (63,492,819 bytes in total,
maximum file 10,164,089 bytes) were independently read from their pinned commits and
verified; the consumer did not repeat full native grid extraction or install owners.
Report pins retain candidate405f75ce2280dc44172ba596b9ee08513abe437c as a preview.

Pinned author-A Python3.12.14 / Shapely2.1.2 GEOS3.13.1 / PyProj3.7.2 PROJ9.5.1 used;
whole runtime binary/PROJ database hashes are in runtime-hashes.json. Shapely STRtree
is used strictly as a bounding-box broadphase; no geometric GEOS predicate or
validity result substitutes for an exact decision. All incidences, contact tests,
ray intersections and parity rules use Fraction values of unchanged Float64 endpoints.
Input context1 is original CRS84 straight segments and original normative lon/lat
centres. Context2 is always_xy EPSG25829 projection of each endpoint and centre,
reconnected with straight projected segments. These are different segment models.

## Executed topology and membership findings

The complete originals contain 64,957 source segments; G adds65, for65,022 total.
The four DGT originals contain25,315 /12,211 /11,251 /10,199 segments. Every retained
member is one Polygon; IGN1172975 has one hole, all other members and G one ring.
The full per-member/per-context count ledger is in report.json.

Naive per-geometry topology testing entails512,892,394 unordered pairs. Conservative
closed AABB candidates contain65,050 pairs in CRS84 (65,022 adjacent,28 nonadjacent)
and65,048 projected (65,022 adjacent,26 nonadjacent). Every nonadjacent candidate
was tested exactly; there are zero contacts. Independently completed checks confirm
all original rings closed, every rational signed ring area nonzero, zero adjacent
backtracking/zero-length segments, and the IGN hole strictly inside its shell in
both contexts. No vertex was dropped. Actual originals have no multipart components;
generic multipart negative controls remain a separate PR1190 test domain.

Naive centre/segment evaluation entails1,402,849,650 checks. Full conservative
ray-box indexing reduced exact candidate processing to152,879 CRS84 and155,393
projected edges. Every original member ID remains in the classification output;
no first-owner selection occurs. The point source-membership records match every
retained root preview member in both contexts:21,325Portugal-only,244Spain-only,
5both-source and1neither-source; no source-boundary centres. The five both and one
neither remain unresolved sourcepoint observations, not affiliations or proposals.
The indexing/arithmetic stage ran in approximately13s in this private environment;
this is a dated measurement, not a performance guarantee or production claim.

## Retained context failure: three gap centres

All21,575 points are exact-strict inside original CRS84 G. Projected straight-endpoint
G contains21,572 and excludes3. Independent brute-force exact half-open tests confirm
all three inside original / outside projected:

- cell[126011,99417], lon/lat[-6.964060938489354,39.824192554622506]
- cell[125948,99571], lon/lat[-7.050571012259411,39.661589641842795]
- cell[125762,99579], lon/lat[-7.305981706247195,39.65313225547874]

Exact nearest-edge squared-distance fractions, endpoint provenance and independent
ray results are retained in topology-completion.json. Display-only projected outside
distances are approximately0.0450m /0.2711m /0.00905m. These are strict domain failures
regardless of size. Nonlinear projection of original long gap straight segments
changes the reconnected straight-edge model; projecting endpoints does not preserve
the original segment point set. Area diagnostics in EPSG25829 must not redefine the
original CRS84 gap-cell domain. No densification, snap, source-accuracy allowance,
owner proposal or literal Float64 face repair is introduced by this observation.

Both complete contextual point record files are retained separately. Their source
class labels are observations of the supplied point against sources; gap_state is
separate, so the three outside projected G rows do not claim to be projected four-class
strict-gap assignments. Reconcile no observations across the contexts by omission.

## Bounded engineering followup justified

A focused followup could add exact indexed original-source support for this complete
large-input closure, retaining all PR1190 semantics and strict export failures.
Use min/max of unchanged finite Float64 endpoint coordinates as exact ordered bounds;
closed AABB overlap cannot exclude a real original-segment contact. A ray through p
uses [p.x,max_source_x] × {p.y}; every boundary point and rightward ray intersection
lies in that box. Filter candidates with exact boundary and half-open predicates,
never a GEOS intersects/contains/validity predicate. Test the broadphase independently
against brute-force fixtures, including equal endpoint events, horizontal/vertical
segments, adjacent overlap, thin holes, scales and byte/context/roster corruption.

A portable index can use an x-event sweep for topology candidates and a y-interval
index for query candidates. Float64 comparison on unchanged finite endpoints is
exact ordering; do not compute rounded cutoffs/interpolated bucket boundaries.
Independent source-endpoint x-event and y-interval sweep indices have now been executed. Every topology pair set and every point-ray candidate set for all twelve originals plus G, all21,575 points and both contexts exactly matches STRtree. Per-point all-member candidate maxima are25CRS84/34projected, with p95 counts14/16. The complete perpoint count vectors and per-member active/candidate maxima are retained in independent-index-completeness.json. This independently validates actual candidate completeness; synthetic equal-event/degenerate/adversarial controls remain required before general tracked implementation.

Keep32MiB ordinary file /256MiB total /512descriptor limits unchanged. Read originals
without copies, cache rational endpoints once, stream queries/candidates, and require
explicit global candidate/segment/member/point caps plus failure receipts when those
caps are reached. Do not merely raise the old quadratic per-geometry segment budget.
Retain original CRS84 membership as the normative gap domain, and separate projected
area/segment observations. Any future approved owner repair still requires the
unresolved GEO/source authority, member/crosswalk, numeric export and integration gates;
this followup would supply honest full-input sourcepoint diagnostics only.

No new goal/claim or tracked implementation started before PR1190 readback/release.

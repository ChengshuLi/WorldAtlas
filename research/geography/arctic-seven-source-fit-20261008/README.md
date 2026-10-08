# Arctic seven-component AAFC source-fit assessment

This packet answers the bounded source-fit question in issue #1481 for exactly two ECO15 and five ECO25 candidate components from #1295. It is a source-only proposal; it makes no geometry change to Atlas data.

## Reproduction

From the repository root, with Shapely 2.1.2 available:

```sh
python research/geography/arctic-seven-source-fit-20261008/prepare_sources.py
python research/geography/arctic-seven-source-fit-20261008/reproduce_fit.py
python research/geography/arctic-seven-source-fit-20261008/build_manifest.py
node scripts/evidence-quality.mjs research/geography/arctic-seven-source-fit-20261008/evidence-quality.json
```

`prepare_sources.py` reconstructs the registered 45,601,680-byte AAFC semantic archive from its six immutable baseline Git blobs, verifies the archive SHA-256 `9ed454c129cc92cd999dae6877587997c25cec47bdfdc35a8b3f20863858430e`, extracts the exact `aafc-ecoregions.geojson` member and proves it equals the retained native file byte for byte. It also makes deterministic gzip copies of the complete official AAFC v2.2 ecoregions and baseline ArcGIS ecoprovinces files and verifies their decompressed hashes against the pinned source manifest.

`build_manifest.py` writes the geography-lane evidence manifest against the ready issue’s 51 actual file pins. `reproduce_fit.py` checks each candidate against both complete ecoregion editions, all named source envelopes, its exact current Atlas target, all 36 active geometry files (49,625 features), the relevant parent ecoprovince records, the complete 64-component/four-family context, and five exact retired administrative reference records reassembled from their seven authenticated archive pieces. It uses Shapely/GEOS exact predicates and union operations on the stored longitude/latitude coordinates. No snapping, buffering, repair, or tolerance is used. `candidate-decisions.json` retains each candidate geometry, target union, gain and loss geometries, full active-feature contact list, source version coverage, parent-source comparison, retired-member comparison, and decision. `proposed-additions.geojson` contains only the three strict exact-addition outputs.

## Findings

All seven candidates are valid polygons and each is wholly covered by exactly one named ecoregion in each edition: ECO15 “Banks Island Lowland” and ECO25 “Foxe Basin Plain.” Both source editions fully cover each candidate, and each candidate intersects only its intended Atlas target among the 49,625 active features. The v2.2 and native source envelopes are not geometrically identical; their per-candidate symmetric differences are recorded in the result file. Coverage agreement is not proof that the two editions have the same coastline or date-specific authority.

| Candidate | Retired cartographic reference context | Exact target union | Disposition |
| --- | --- | --- | --- |
| `12c9ec981349…` ECO15 | Candidate contained by Region 1, Unorganized; Sachs Harbour is disjoint | Valid, zero target loss, full candidate gain, no new positive-area neighbor overlap | Repair-ready geometric proposal |
| `52452c5923a0…` ECO15 | Line contact with Region 1, Unorganized; Sachs Harbour is disjoint | Nonempty target residual, `1.9737900550098608e-16` square degrees; candidate gain otherwise preserved | Unresolved: strict zero-loss topology predicate fails at a tiny residual; retained residual coordinates are in JSON |
| `add031b71953…` ECO25 | Line contact with Baffin, Unorganized; Hall Beach and Igloolik are disjoint | Valid, zero target loss, full candidate gain, no new positive-area neighbor overlap | Repair-ready geometric proposal |
| `2aca267603c8…` ECO25 | Positive-area overlap with Baffin, Unorganized; Hall Beach and Igloolik are disjoint | Target overlap is `1.000117608858264e-18` square degrees; union gain and candidate differ by a nonempty line-only GEOS symmetric difference, although its planar area is zero | Unresolved: the candidate is not wholly new, so the exact-addition predicate fails; overlap and symmetric-difference coordinates are retained |
| `265c983a6123…` ECO25 | Line contact with Baffin, Unorganized; Hall Beach and Igloolik are disjoint | Nonempty target residual, `2.5685191484904345e-17` square degrees; candidate gain otherwise preserved | Unresolved: strict zero-loss topology predicate fails at a tiny residual; retained residual coordinates are in JSON |
| `17bb5b7f043b…` ECO25 | Candidate contained by Baffin, Unorganized; Hall Beach and Igloolik are disjoint | Valid, zero target loss, full candidate gain, no new positive-area neighbor overlap | Repair-ready geometric proposal |
| `54dc96cd3d0e…` ECO25 | Line contact with Baffin, Unorganized; Hall Beach and Igloolik are disjoint | Nonempty target residual, `1.0722759485881639e-16` square degrees; candidate-target overlap is `1.0473876316424694e-17` square degrees; exact union gain and candidate differ by `1.314106384930676e-16` square degrees | Unresolved: strict zero-loss and full-gain predicates fail; retained residual and symmetric-difference coordinates are in JSON |

For ECO15, the current target is Banks Island Lowland under Victoria Lowlands; its source IDs and member IDs are consistent with the retained hierarchy and retired context. For ECO25, the current target is Foxe Basin Plain under Foxe–Boothia Lowlands; all five candidates are covered by the source parent feature `ECOPROVINCE_ID=2.7` (piece/object 63). These checks establish consistency with retained source and hierarchy records, not boundary authority. The current parent hierarchy entries remain open/retained-reference records; this packet shows compatible parent identity, not semantic approval of the hierarchy or any member boundary.

## Source, version, and interpretation limits

- Native source: exact original AAFC `aafc-ecoregions.geojson` member, 2,756,674 bytes, SHA-256 `a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf`; 218 features, 194 unique ecoregion IDs, one feature each for IDs 15 and 25. The registered original archive and its six parts are pinned by the baseline semantic-source registry. Its archive is retrieved in the repository snapshot dated 2026-10-01; the underlying effective date is not established.
- Comparison: complete AAFC Terrestrial Ecoregions of Canada v2.2, 13,567,291 decoded bytes, SHA-256 `f2c7ac1cabc601c364479c4616c245c993443ac61f6842f01a12078844a71e6b`.
- Parent comparison: AAFC ecoprovinces baseline ArcGIS layer 0, 7,164,752 decoded bytes, SHA-256 `5602aa328b64c3db9236cf610056d8375f164a51651dec34dc63334ecd4bc51f`.
- These products are licensed under the Open Government Licence – Canada as stated in the retained source records. The ecological framework describes physical regions, not administrative boundaries.
- The retired archive identifies itself as an undated cartographic reference archive with no historical effective year. Its member coverage is context only; it cannot identify the cause or date of the current gaps.
- The component source properties mark water status unverified. The analysis makes no land/water/ice classification and does not establish historic processing cause, boundary authority, legal status, or permission to publish changes.
- “Repair-ready” means only that the retained geometric/source-fit criteria pass exactly in this bounded assessment. It is not approval to apply or publish geometry. The four unresolved candidates need the exact topology condition noted above addressed in a reviewed proposal; this packet does not use tolerances to erase nonzero residuals or overlaps.

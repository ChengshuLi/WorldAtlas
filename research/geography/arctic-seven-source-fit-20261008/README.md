# Arctic seven-component AAFC source-fit assessment

This packet answers the bounded source-fit question in issue #1481 for exactly two ECO15 and five ECO25 candidate components from #1295. It is a source-only proposal; it makes no geometry change to Atlas data.

## Reproduction

The files at the packet root are the preserved earlier vintage. Their `execution-budget.json` and phase outputs predate the admission controls described here and do not constitute a qualified rerun. New phase products are written only to fresh `vintages/r5-*` directories. Superseded setup attempts are retained under `exploratory/`: the first native receipt undercounted the plan read, the next publication named the prior vintage, and the following fit stopped at a stale vintage assertion. They are disclosed for audit and are not part of the qualified run.

The admitted rerun is tied to an immutable code commit. On the exact Python 3.12.14 / Shapely 2.1.2 environment recorded by `runtime-lock.json`, first commit the phase runner, its source bridge, phase scripts, native tool lock, runtime lock, and lock builders. Then use that exact commit as `EXECUTION_COMMIT` below. The plan builder verifies that all materialized source and code files match the commit and that the issue-pinned inputs retain their original hashes. It creates `phase-plan.json` once; the plan is immutable for the run. If the runtime or code changes, preserve the plan and start a separately reviewed execution vintage.

```sh
PYTHON=/Users/chengshuli/.cache/worldatlas-evidence-python/f28ad176e64a6a5ea260-py3.12.14-arm64/bin/python
NODE=/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_phase_plan.py --execution-commit "$EXECUTION_COMMIT"
read -r PLAN_SHA _ < <(sha256sum research/geography/arctic-seven-source-fit-20261008/phase-plan.json)
read -r NATIVE_TOOLS_SHA _ < <(sha256sum research/geography/arctic-seven-source-fit-20261008/native-tools-lock.json)
bash research/geography/arctic-seven-source-fit-20261008/native_archive_extract.sh "$EXECUTION_COMMIT" "$PLAN_SHA" "$NATIVE_TOOLS_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py retired-context --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-a --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-b --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-c --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-d --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py source-fit --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA"
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_run_record.py
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_manifest.py
"$NODE" scripts/evidence-quality.mjs research/geography/arctic-seven-source-fit-20261008/evidence-quality.json
```

Each wrapper checks the exact plan and execution commit, computes the prospective phase charge before reading source bodies, verifies whole-file runtime/code/source pins, and rejects a used or unsafe output vintage. Python phases admit their outputs through a narrow bridge and publish a completion record last. Every later phase authenticates predecessor output, publication, and execution receipts before using it. The native archive phase separately locks its shell tools and host platform, verifies all six archive-part hashes and the full 45,601,680-byte archive hash, streams the 162,109,440-byte decoded tar payload, and compares the extracted `aafc-ecoregions.geojson` member byte for byte with the retained native file.

The enforced cap is 268,435,456 bytes (256 MiB) per phase, including input bytes, decoded-source and scratch reservations, code, installed runtime, predecessor evidence, outputs, and receipts. This is a cumulative byte budget, not a memory estimate. The plan builder reports prospective charges; only a completed phase's execution receipt records an observed charge. No new `r5-*` phase is qualified until its receipt and publication record exist.

`retired-context` authenticates all seven retired-archive parts before decoding, streams their 56,672,580 decoded bytes to a temporary file, verifies the reconstructed digest, and extracts only the five exact retired location records. The four `neighbor-scan-*` phases partition the complete 36-part active geometry index into four disjoint groups of nine parts. Each records its full feature-ID roster and exact candidate intersections. The final `source-fit` phase requires all four authenticated scan vintages, proves that their rosters are disjoint and together equal all 49,625 indexed features, then checks both complete ecoregion editions, target geometry, hierarchy, parent ecoprovinces, four-family context, and five retired reference records. It uses Shapely/GEOS exact predicates and union operations on stored longitude/latitude coordinates. No snapping, buffering, repair, or tolerance is used.

The final `candidate-decisions.json` retains each candidate geometry, target union, gain/loss and candidate/gain symmetric-difference geometries, the full active-feature contact list, source-version coverage, parent-source comparison, retired-member comparison, all ten decision premises, and candidate-specific missing premises. `proposed-additions.geojson` contains only the three strict exact-addition outputs. New fit products are emitted into the fit vintage, never over the preserved root outputs.

The completed run uses execution commit `a4649c264adbb74a4e98a36522f336604b7ba2c8` and phase-plan SHA-256 `7db470923274a09477023def89ce55562c8165479c921ecfbc10ca0a2ca55224`. Every phase stayed below the 268,435,456-byte cap:

| Phase | Charged bytes | Headroom |
| --- | ---: | ---: |
| Native archive extraction | 263,776,415 | 4,659,041 |
| Retired-member context | 235,267,399 | 33,168,057 |
| Neighbor scan A | 234,161,047 | 34,274,409 |
| Neighbor scan B | 228,027,666 | 40,407,790 |
| Neighbor scan C | 228,584,478 | 39,850,978 |
| Neighbor scan D | 241,003,835 | 27,431,621 |
| Source fit and controls | 222,702,482 | 45,732,974 |

The machine-readable `r5-execution-budget.json` binds each phase’s plan maximum, observed charge, predecessor receipts, publication receipt, and output hashes. The packet manifest checks 143 file bodies and reports `limited` for the declared boundary-authority and undated-context gaps. It does not report a schema, hash, or byte-inventory failure.

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

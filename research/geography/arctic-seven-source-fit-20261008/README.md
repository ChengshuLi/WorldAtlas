# Arctic seven-component AAFC source-fit assessment

This packet answers the bounded source-fit question in issue #1481 for exactly two ECO15 and five ECO25 candidate components from #1295. It is a source-only proposal; it makes no geometry change to Atlas data.

## Reproduction

The original `r7` run and its receipts are preserved for audit, but an independent review found that its native commands were not bound to the executables whose hashes were recorded, its runner read two inputs before enforcing their size bounds, and its negative control overstated the scope of its decision-gate checks. Treat r7 results as recorded exploratory outputs, not qualified reproduced results. The first corrected budget plan, r8, was rejected before execution: its source-fit reservation was 275,356,788 bytes, above the 268,435,456-byte cap. The abbreviated-commit r9 plan was rejected before execution. Its subsequent native extraction exposed a macOS Bash portability issue in the plan-size read, so its native receipt undercounted the charge; that output is preserved as exploratory evidence only. The r8 and r9 rejected artifacts are retained under `exploratory/`. The r10 run completed, but independent review found its baseline blob reads could resolve Git through `PATH` rather than the pinned absolute executable. Treat all r10 results as unqualified exploratory evidence; they are preserved under `exploratory/r10-path-git-unbound/`. The first r11 qualification attempt completed native extraction, then stopped before source reads because the platform fingerprint differed at the interpreter processor-alias field. Its plan and native output are preserved under `exploratory/r11-platform-admission-mismatch/`. The r12 runner checks the stable system, OS release, and machine fields individually; the current qualification attempt uses fresh immutable `r12-*` vintages and a frozen `phase-plan-r12.json`.

The r12 rerun is tied to an immutable code commit. Its baseline blob and tree reads use the exact absolute Git executable admitted by the native-tools lock, including reads through the inherited immutable baseline API. On the exact Python 3.12.14 / Shapely 2.1.2 environment recorded by `runtime-lock.json`, generate the r12 native executable lock, then commit the phase runner, source bridge, phase scripts, both locks, and builders. Use that exact full 40-character commit SHA as `EXECUTION_COMMIT`. The plan builder verifies the materialized sources and code against the commit and checks the issue-pinned inputs. It writes `phase-plan-r12.json` once; that plan is immutable for this run. Before execution, inspect every prospective charge and stop if any phase exceeds the cap. The r12 source-fit phase reserves 2 MiB for each neighbor-scan predecessor, above the observed r7 scan output sizes (about 0.35–0.52 MiB); the runner still enforces each bound and rejects an output that exceeds its declared reservation.

```sh
PYTHON=/Users/chengshuli/.cache/worldatlas-evidence-python/f28ad176e64a6a5ea260-py3.12.14-arm64/bin/python
NODE=/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_native_tools_lock.py --vintage r12
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_phase_plan.py --execution-commit "$EXECUTION_COMMIT"
read -r PLAN_SHA _ < <(sha256sum research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json)
read -r NATIVE_TOOLS_SHA _ < <(sha256sum research/geography/arctic-seven-source-fit-20261008/native-tools-lock-r12.json)
/bin/bash research/geography/arctic-seven-source-fit-20261008/native_archive_extract.sh "$EXECUTION_COMMIT" "$PLAN_SHA" "$NATIVE_TOOLS_SHA"
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py retired-context --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-a --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-b --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-c --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py neighbor-scan-d --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
PYTHONEXECUTABLE="$PYTHON" "$PYTHON" research/geography/arctic-seven-source-fit-20261008/run_source_phase.py source-fit --baseline "$EXECUTION_COMMIT" --plan-sha256 "$PLAN_SHA" --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_run_record.py --phase-plan research/geography/arctic-seven-source-fit-20261008/phase-plan-r12.json --output r12-execution-budget.json
"$PYTHON" research/geography/arctic-seven-source-fit-20261008/build_manifest.py
"$NODE" scripts/evidence-quality.mjs research/geography/arctic-seven-source-fit-20261008/evidence-quality.json
```

Each wrapper checks the exact plan and execution commit, computes the prospective phase charge before reading source bodies, verifies whole-file runtime/code/source pins, and rejects a used or unsafe output vintage. Python phases admit their outputs through a narrow bridge and publish a completion record last. Every later phase authenticates predecessor output, publication, and execution receipts before using it. The native archive phase separately locks its shell tools and host platform, verifies all six archive-part hashes and the full 45,601,680-byte archive hash, streams the 162,109,440-byte decoded tar payload, and compares the extracted `aafc-ecoregions.geojson` member byte for byte with the retained native file.

The enforced cap is 268,435,456 bytes (256 MiB) per phase, including input bytes, decoded-source and scratch reservations, pinned Python and native runtimes, predecessor evidence, outputs, and receipts. Native extraction reads each of the six archive parts once, hashing each part and the full archive while streaming them to tar. The Python runner rejects a phase plan over 1 MiB and checks each runtime file's opened size against its reservation before reading. The negative control combines real cross-group envelope comparisons with decision-gate unit checks; it is explicitly not described as an adverse-input pipeline fixture.

`retired-context` authenticates all seven retired-archive parts before decoding, streams their 56,672,580 decoded bytes to a temporary file, verifies the reconstructed digest, and extracts only the five exact retired location records. The four `neighbor-scan-*` phases partition the complete 36-part active geometry index into four disjoint groups of nine parts. Each records its full feature-ID roster and exact candidate intersections. The final `source-fit` phase requires all four authenticated scan vintages, proves that their rosters are disjoint and together equal all 49,625 indexed features, then checks both complete ecoregion editions, target geometry, hierarchy, parent ecoprovinces, four-family context, and five retired reference records. It uses Shapely/GEOS exact predicates and union operations on stored longitude/latitude coordinates. No snapping, buffering, repair, or tolerance is used.

The final `candidate-decisions.json` retains each candidate geometry, target union, gain/loss and candidate/gain symmetric-difference geometries, the full active-feature contact list, source-version coverage, parent-source comparison, retired-member comparison, all ten decision premises, and candidate-specific missing premises. `proposed-additions.geojson` contains only the three strict exact-addition outputs. New fit products are emitted into the fit vintage, never over the preserved root outputs.

The r7 charge record and the unqualified r10 charge record remain available with their original receipts. The qualified r12 run used the same seven-phase plan and completed every phase below the 268,435,456-byte cap. `r12-execution-budget.json` records each planned maximum, actual charge, output hash, and headroom; the largest actual charge was 251,812,591 bytes (neighbor scan D), and source-fit charged 233,513,028 bytes.

The manifest continues to report `limited` for the declared boundary-authority and undated-context gaps.

The qualified r12 source/GIS execution is complete. Its candidate decisions, proposed additions, and both control files are byte-identical to the preserved unqualified r10 outputs. The r10 execution remains unqualified, so cross-run repeatability is not claimed. The small reporting-writer preflight ran in a credential-free environment: `build_run_record.py` recreated the same retained record at a fresh output path, and both it and `build_manifest.py` rejected existing sentinel files, dangling-symlink destinations, and traversal paths without changing the sentinels. A fresh manifest output passed the local evidence-quality check. These writer checks do not independently re-establish the geographic result.

## Findings

The qualified r12 result confirms all seven candidates are valid polygons, each wholly covered by exactly one named ecoregion in each edition: ECO15 “Banks Island Lowland” and ECO25 “Foxe Basin Plain.” The four authenticated neighbor scans cover 49,625 active features in four pairwise-disjoint ID rosters. The v2.2 and native source envelopes are not geometrically identical; their per-candidate symmetric differences are recorded. Coverage agreement does not prove that the two editions have the same coastline or date-specific authority.


| Measure | Value | Unit |
| --- | ---: | --- |
| Active features | 49625 | features |
| Candidates | 7 | components |
| Repair-ready geometric proposals | 3 | components |
| Unresolved candidates | 4 | components |
| Exact one-envelope matches | 7 | components |

The seven detailed candidate rows and their exact residual measurements are in `vintages/r12-fit/candidate-decisions.json`. In summary, candidates `12c9ec981349…` (ECO15), `add031b71953…` (ECO25), and `17bb5b7f043b…` (ECO25) pass the exact additive predicates. Candidates `52452c5923a0…`, `2aca267603c8…`, `265c983a6123…`, and `54dc96cd3d0e…` remain unresolved under the strict zero-loss/full-gain predicates; their residuals and symmetric-difference geometries remain in the JSON.

For ECO15, the retained target is Banks Island Lowland under Victoria Lowlands; its source IDs and member IDs are consistent with the retained hierarchy and retired context. For ECO25, the retained target is Foxe Basin Plain under Foxe–Boothia Lowlands; all five candidates are covered by the source parent feature `ECOPROVINCE_ID=2.7` (piece/object 63). These checks establish consistency with retained source and hierarchy records, not boundary authority. The retained parent hierarchy entries remain open/retained-reference records; this packet shows compatible parent identity, not semantic approval of the hierarchy or any member boundary.

## Source, version, and interpretation limits

- Native source: exact original AAFC `aafc-ecoregions.geojson` member, 2,756,674 bytes, SHA-256 `a565563a6aef794df831dc9251fb4108018e20a4f0172acbc36b599f9b7f4abf`; 218 features, 194 unique ecoregion IDs, one feature each for IDs 15 and 25. The registered original archive and its six parts are pinned by the baseline semantic-source registry. Its archive is retrieved in the repository snapshot dated 2026-10-01; the underlying effective date is not established.
- Comparison: complete AAFC Terrestrial Ecoregions of Canada v2.2, 13,567,291 decoded bytes, SHA-256 `f2c7ac1cabc601c364479c4616c245c993443ac61f6842f01a12078844a71e6b`.
- Parent comparison: AAFC ecoprovinces baseline ArcGIS layer 0, 7,164,752 decoded bytes, SHA-256 `5602aa328b64c3db9236cf610056d8375f164a51651dec34dc63334ecd4bc51f`.
- These products are licensed under the Open Government Licence – Canada as stated in the retained source records. The ecological framework describes physical regions, not administrative boundaries.
- The retired archive identifies itself as an undated cartographic reference archive with no historical effective year. Its member coverage is context only; it cannot identify the cause or date of the current gaps.
- The component source properties mark water status unverified. The analysis makes no land/water/ice classification and does not establish historic processing cause, boundary authority, legal status, or permission to publish changes.
- “Repair-ready” means only that the retained geometric/source-fit criteria pass exactly in this bounded assessment. It is not approval to apply or publish geometry. The four unresolved candidates need the exact topology condition noted above addressed in a reviewed proposal; this packet does not use tolerances to erase nonzero residuals or overlaps.

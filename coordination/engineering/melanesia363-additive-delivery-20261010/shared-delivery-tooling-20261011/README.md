# Reusable delivery preflight and emitted-consumer smoke

This tooling removes repeated manual dependency discovery and UKR-specific consumer edits. The first adoption stage keeps all 28 selected-reader code bodies and the selected map unchanged. It also installs the finite trusted bootstrap and separate policy catalogue needed to remove the programme self-registration cycle.

## Use the existing build

`npm run build:cloudflare` now runs the preflight before copying its package input image. The preflight aggregates absent declared Git objects/materialized files, actual current project imports absent from the declaration, installed locked npm packages, and the three Python build imports pinned in `requirements.txt`. It does not fetch or install anything. Browser launch capability is reported separately; absence does not turn a package build into a browser pass.

To inspect before building:

    node scripts/package-build-preflight.mjs --root REPO --browser probe --out NEW_REPORT

For a caller that genuinely requires ancestry, supply repeated `--ancestor COMMIT`. Ordinary package CI is deliberately shallow; it does not acquire a new historical ancestry requirement. Existing immutable selected/source readers still authenticate historical custody. `--browser required` fails when installed Playwright cannot launch; `off` explicitly records that capability was not requested. No browser download or alternate executable is selected by this tool.

## Check an actual emitted release

    node scripts/selected-delivery-smoke.mjs --root REPO --emitted-directory EMITTED_CLIENT --expectations EXPECTATIONS_JSON --output NEW_REPORT

The expectations file contains the selected ledger byte hash, expected cumulative native cells, and complete caller-reviewed original cohort/member expectations. `completed-ukr-expectations.json` is the already-completed UKR example. Future batches change this data, not executable constants. Original batch labels are supplied expectations; this check does not grant source approval or independently infer original rosters.

The command uses production asset loading, effective primitives, picking and packed renderer sampling. It checks every cumulative patch cell and one occupied stable-owner control in every retained observed row, and verifies each expected selected row and actual primitive in the emitted feature. Missing/changed assets or incomplete expectations fail. Existing full native/continuous conservation gates and the actual hosted GPU/Canvas test remain authoritative.

## Measured result and limits

The completed UKR emitted output from PR1705 was reused, without rebuilding or rerunning SOURCE, NATIVE, current-rebind or assembly. The generalized command passed in **4.38 seconds**, GNU time maximum RSS **1,188,364,288 bytes**, checking **49,625 features**, **353 cumulative native cells**, **262 stable-owner samples**, and the expected UKR zero-cell primitive. The initial generalization rejected an actual supported native startup descriptor because it lacks encoded `bytes`; the corrected branch preserves its encoded SHA and production decoded-word checks. Both the initial refusal and successful timing remain retained with the author’s test output.

An initial actual warm dependency preflight completed in **0.78 seconds**. Its first run caught an omitted materialized input before any copy/build. A final frozen-head measurement is recorded with the PR results. This is measured preparation/consumer cost, not an end-to-end delivery forecast.

Previously, a missing Python import was discovered only after a **187.767-second failed build**. The new import probe demonstrates early detection of that failure class. It does not claim every future build or CI failure is eliminated. Cached immutable inputs and locked dependencies are reused; no repeated dataset download was needed here. The finite migration below removes the recurring programme-code edit; avoided PR/CI wall time remains anticipated until a subsequent cohort uses it. Per-cohort request assembly remains separate optimization work. The existing complete successful package/build/readback remains useful validation, not wasted time.

Local bundled-browser availability remains unavailable in this cloud environment. The prior actual hosted GPU/Canvas result is retained as prior evidence; this Node smoke is not a new GPU/Canvas execution.

Focused validation: 11 preflight controls, 9 existing package-boundary controls, and 21 smoke controls passed. Existing current-execution controls use explicit programmatic readiness fixtures for their deliberately minimal synthetic repositories; ordinary build CLIs expose no disable flag or environment bypass. No new source batch or scientific qualification ran.

## One-time programme migration

The former literal programme array belonged to its own 17-body executed vector: appending a record changed the helper and invalidated the just-recorded current vector. The dedicated `supported-programs.json` preserves all twelve legacy records and admits the independently reviewed stable caller/helper pair once. The accepted SOURCE caller and current caller differ only in the NATIVE registry branch; review6105261214 explicitly approves SOURCE-stage equivalence without relabelling the historical execution. Policy is authenticated from the actual trusted module checkout, separately inventoried and charged; candidate policy cannot authorize candidate code.

Two adoption stages are necessary only once. This PR keeps the old28 executable bodies and installs the catalogue plus finite trusted orchestration. The next PR applies exactly the reviewed helper and its focused test, with the catalogue byte-identical and all other tree paths unchanged. The bootstrap authenticates those exact ordinary files and complete28 vectors, then runs the genuine original baseline proof. It does not execute candidate code or call the baseline proof a new candidate qualification. The one exact old471-to-stable28 policy record preserves the completed UKR qualification. Future cohorts with this identical complete method reuse the stable record and update only their accepted source/authority data. Actual executed17/28 vectors, runtime custody and numerical acceptance remain explicit.

Before staging that finite transition, the stable helper was exercised against the completed current selection at `01bfa7c564468252953b190f0d2565d91183295d`. The real selected reader and package declaration guard passed in 26.59 seconds with GNU maximum RSS 362,748 KiB. Its 142 consumed descriptors include the whole trusted catalogue; 353 cumulative native cells remain present and the logical phase is 230,294,600 bytes. `programme-selected-readback.json` retains the actual result and inventory. This was existing-output consumption, with no SOURCE/NATIVE/current-rebind/assembly producer. The helper and catalogue remain identical at the frozen migration source `68731bab38c17d3b1ca5f3d7584c14bdacb17728`; its test only replaces repeated historical Git access with the already-authenticated twelve-record canonical identity.

Focused migration validation passed eight policy controls and 36 trusted-geography controls. The one existing synthetic lazy-fetch fixture used a fixture-local environment override; all real-repository reads retained no-lazy-fetch. The ordinary wrapper's initial 35/36 result is retained honestly. The final warm preflight at the original frozen tooling head took 0.718 seconds with the explicitly selected complete Python environment. These measurements do not claim a measured future batch-completion speedup.

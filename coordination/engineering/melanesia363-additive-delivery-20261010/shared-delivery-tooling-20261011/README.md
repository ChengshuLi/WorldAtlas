# Reusable delivery preflight and emitted-consumer smoke

This tooling removes repeated manual dependency discovery and UKR-specific consumer edits. It does not change the source/native method, selected map, source authority or programme admission.

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

Previously, a missing Python import was discovered only after a **187.767-second failed build**. The new import probe demonstrates early detection of that failure class. It does not claim every future build or CI failure is eliminated. Cached immutable inputs and locked dependencies are reused; no repeated dataset download was needed here. Avoiding repeated programme support PRs, repeated CI and per-cohort request assembly remains separate optimization work, with savings still anticipated until exercised. The existing complete successful package/build/readback remains useful validation, not wasted time.

Local bundled-browser availability remains unavailable in this cloud environment. The prior actual hosted GPU/Canvas result is retained as prior evidence; this Node smoke is not a new GPU/Canvas execution.

Focused validation: 11 preflight controls, 9 existing package-boundary controls, and 21 smoke controls passed. Existing current-execution controls use explicit programmatic readiness fixtures for their deliberately minimal synthetic repositories; ordinary build CLIs expose no disable flag or environment bypass. No new source batch or scientific qualification ran.

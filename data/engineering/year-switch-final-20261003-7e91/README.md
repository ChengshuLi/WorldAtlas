# Site 23 year-switch production verification

Issue #22; worker engineering-night-20261003-7e91f438. Application implementation was merged in PRs 553 and 618. This final bounded PR retains publication and production evidence; it does not establish full completion of the performance acceptance target.

Production version 23: source 8aaeb86cdfe9fc49a3ca52c76151989ec994ece1, application primary squash 79624f7695fa2e564a465bb9a4fb499af75d97f8, deployment appgdep_6ac132614ab08191b1dab4d525bdae4c. Site 22 is the retained rollback. Full publication gate passed 551 unit checks, 15 geographic preparation checks and all 51 exact ownership buckets. All 539 deployment files matched their source Git blobs. Local upload and native canonical archive have separately recorded hashes and sizes in the owned coordination record.

## Conditions and results

Actual private production responses and client were served through a fixed-origin GET-only localhost proxy. The private header stayed server-side, supplied through hidden terminal stdin. Headless Chromium ran at 1440x1080 without CPU/network throttling. This is not a physical-device certificate. Fresh browser context/cache initialization is distinct from navigation; provider idle/wake state is unknown.

| Suite | Initial browser loading | Ordinary year selections | Rapid latest-selection settlement |
| --- | --- | --- | --- |
| Site 21 historical baseline | 100.063 s | 68.310, 63.852, 63.463, 65.017 s | 68.245 s |
| Site 23 historical | 36.325 s | 2.913, 2.534, 2.835, 2.686 s | 3.045 s |
| Site 23 supported evidence | 34.713 s | 4.166, 3.184, 4.085, 2.555 s | 4.014 s |

Every sample is retained. The normal warm-navigation budget is 3 seconds. All historical ordinary samples meet it. The supported suite has three ordinary samples exceeding it, so issue #22 must remain open. A populated 2020 response is 2,864,137 bytes and takes 2.62–2.95 seconds through the verification transport; total browser task CPU for those switches is 1.43–1.46 seconds, overlapping transport. These measurements do not individually establish Neon query duration or provider wake overhead. Current empty-history navigation is one 1,100-byte combined scalar/temporal response instead of 57 scalar pages followed by two temporal stream reads. Supported 2020 is also one complete response instead of four sequential scalar pages followed by the temporal reads.

Both suites completed without page errors or year errors; all navigation ownership compilation/upload deltas were zero. Unsupported year zero made no request and preserved the visible map. Six-continent selected profiles retain eight displayed attributes, six hierarchy tiers and explicit present-day name context; all fourteen map modes completed rendered palette uploads. Zoom/resize navigation retained ownership compilation/upload counts. Historical 1800 loaded without error.

Fault/recovery evidence is separately labeled: errors/revision changes are injected into the verification transport, never the production database. Do not represent it as an actual production outage or content mutation.

## Proposed bounded follow-ups

1. One reviewed engineering item (maximum two PRs) for the remaining populated-year 3-second target. Start from these exact supported-year receipts; measure hosted query/connection phases and complete 2.8 MiB payload decode/resolution separately. Evaluate bounded response/source dictionary optimization or revision-safe reuse only with withdrawal authority, original provenance, release pins, atomic selected-year cache and zero navigation ownership recompile/upload preserved. Validate actual production 2020/2021/distant/rapid sequences against the same 3-second budget, retain every sample, and attribute remaining cold limitations only when measured.
2. Separate one-PR investigation of fresh browser loading (34.7–36.3 seconds here). Measure asset transfer/decode and map ownership startup independently from provider wake. Do not call Linux headless checks physical-mobile acceptance or loosen existing provider/package limits.

These are proposals for coordinator scope/dependency review, not self-approved ready claims. The original three-PR budget remains hard.

## Reproduce and resume

Use docs/YEAR_SWITCH_VERIFICATION.md and the committed benchmark, browser and fault scripts. Obtain private verification through native Sites get_site and documented OAI-Sites-Authorization mechanism; never paste credentials into chat, arguments, logs or Git. Do not rotate a working bypass token unnecessarily.

If the workspace GitHub credential remains HTTP 401, restore the managed runtime GitHub authorization with Actions workflow-dispatch/read and normal branch write access through its connection/settings mechanism. The native GitHub connector can retain evidence and open a draft PR but exposes no authoritative claim/merge workflow dispatch. Do not use direct merge or comment-only claim/release as a substitute.

After access recovers, inspect the canonical issue claim and current PR/head, settle live_work=false only after all checks/receipts finish, validate scope and required exact-head CI, submit the final partial PR through scripts/queue-pr-merge.mjs, verify the matching bot result and actual squash, then release the claim. Issue #22 remains open for reviewed bounded follow-up. Continue with one freshly confirmed ready issue (initial next candidate #23) from fresh main, rechecking claims/dependencies and active PRs first.

Binary receipts are durably retained in `site23-evidence-transfer.json` as base64 with original filenames, byte counts and SHA-256. Decode each file into an empty evidence directory, check byte count/hash, then decompress the JSON/trace gzip files or view the PNGs. The original local binary files are not separately committed by the UTF-8-only fallback. Existing package/staging receipts remain ordinary gzip files from the initial pushed commit. This transport changes no receipt bytes and includes no private-access credential.

# Shallow-clone geography applicability correction

Issue #1749, recorded 2026-10-11. Baseline1098d766a9f5f90f04bdf5bbefc3f0cf8d5c7629 includes the completed #1747 activation. This correction changes neither its finite transition nor selected scientific data.

## Actual failure

NOR PR #1738 head47680888460cb772da6eb7cbab4a05f6b8474fa0 ran against8a346ba7c957220b34c5cc3368d5d835de533ad4. All157 authored paths were eligible source publication; relevant consumed identities were unchanged. The actual hosted geography job https://github.com/ChengshuLi/WorldAtlas/actions/runs/38177061465/job/114581689075 lasted12m27s. Retained stage lines show an immediate45ms applicability decline followed by25.658s prefetch,263.162s native and438.196s continuous, finally not-applicable. Prefetch imported245,816,424 bytes. The original wrapper suppressed the decline reason, so the log alone cannot identify it.

The exact baseline depth-one blob:none fetch followed by the exact candidate blob:none fetch, in an isolated bare repository with no shared object store, reproduces the defect. Setup took13.374s and produced693 commits,6561 trees and zero blobs. Ordinary shallow-aware merge-base returns the baseline. The previous collector instead unconditionally ignores the shallow boundary and fails while parsing missing baseline parent6149104603dec4cc4967a10cba9bfb1e90a119b7. The recorded collector result is full-check-required/immutable-object-unavailable:merge-base, before any acquisition. No missing history was silently hydrated.

## Narrow correction and controls

Use ordinary merge-base first. Only a failed normal query may use already-present hidden ancestry with the existing read-only boundary override. Missing necessary history still declines; no graph fetching is introduced by this query. Exact current consumed-input/code equality remains separately mandatory.

The wrapper now logs a fixed decline category, selected allowlisted collector category and optional fixed Git operation. It never echoes arbitrary child stderr, error text, locators, commit arguments or environment values. Timeout, process failure, output bounds, malformed output and invalid provenance remain conservative full fallback. Baseline==baseline still requires genuine full proof.

All16 collector controls passed, including the exact missing-parent shallow-descendant case, divergent shallow heads with already-present history, missing-history refusal, strict/fallback custody and scientific-leaf exclusions. All52 Python wrapper controls passed through the normal Node test wrapper, including safe bounded diagnostics, timeout/group cleanup and invalid provenance. No skipped controls. Actual outputs are retained here. No scientific suite was rerun locally.

## Exact cold correction result

The corrected collector ran against the same still-cold failed fixture and returned unchanged-selected-inputs. It acquired112 routing bodies totaling4,120,159 bytes in10 batches, plus600 graph objects totaling1,715,409 uncompressed bytes across2 strict-origin batches. Scientific leaf imports were zero. The original shallow marker stayed unchanged. Executed collector/transport code byte pins are recorded in cold-after-timing.json; the historical policy commit is not falsely claimed to contain the new executed implementation.

The observed interval from redirected output-file creation immediately before process launch to final JSON write was52.4078 seconds. This is explicitly a filesystem-timestamp boundary, not a monotonic process timer or hosted whole-job measurement. The13.374-second metadata setup is separate. These measurements establish the repaired cold path, not universal or hosted sub-minute latency. A subsequent real source-only hosted job remains the production timing check.

Reproduction uses an empty isolated bare Git fixture, `fetch --depth=1 --filter=blob:none` of the exact baseline, then `fetch --filter=blob:none` of the exact candidate, without changing the shallow file. Run the committed collector with that repository and the two immutable commits. The replay had a120-second process limit and the initial diagnostic harness a128MiB disk bound; existing collector transport and identity guards remain unchanged. Do not use a warm shared object store to claim a cold measurement.

Required author CI, exact-head review and current combined-tree integration are separate merge gates. This PR will not be queued ahead of an already-frozen priority delivery without coordination. No source approval, scientific qualification, geographic publication or consumer validation is asserted by applicability.

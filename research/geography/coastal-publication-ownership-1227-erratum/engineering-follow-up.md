# Evidence baseline-vintage compatibility follow-up

Date: 2026-10-07 America/Los_Angeles; revalidated against fresh main `97291daccaa44e9c67bba9ae87ceaada641226da` at 2026-10-07 19:17 PDT. This is an implementation handoff, not a change to the one-PR geography scope.

## Reproduction

The #1381 issue's `evidence_quality.pins` map has 63 unique `baseline_*` hashes and 58 `original_1227_*` rows (30 unique byte hashes). A GitHub API read of PR #1227 reports 58 changed files; matching every changed-file SHA-256 against the `original_1227_*` pin multiset succeeds exactly.

The 63 `baseline_*` descriptors are the exact old #1218 evidence inventory at commit `a37ad37b94168f9b458617489a702bbb72afbd3d`. All 58 #1227 original outputs are absent at that commit and first coexist with the later merge `a1cf4cd86fd07d00ae592b4705e4b39f50628df7`. At #1227's merge and at issue #1381's fresh-main base `97291daccaa44e9c67bba9ae87ceaada641226da`, two of the old source pins no longer match their original paths:

| Pinned source | Original #1218 SHA-256 | At #1227 merge / fresh main |
| --- | --- | --- |
| `data/geography/part-11.json` | `97271c7b246c44dcb1f2c349590fd7b2e590f5b6c79087e8140c5ae49b5e941f` | `d1b2fb15c9427497de740eb33a529ef382b58cb319028f2aa38f5878de4c9b02` |
| `data/geography/part-17.json` | `5e79cd74b4bafb8259ce6f7b95ae256d10aaeb2ccd4980c7155c900930c923db` | `1ae1a9ef25c1f71b66084aadf57933132383d4271b888ab38866905da5678af3` |

## Why the current gate cannot bind this declaration

Evidence manifest v1 stores one `baseline.commit`. `validateEvidence` resolves every `baseline.files` row and every `baseline.pins` `pin_files` binding from that one commit. The hosted premerge gate additionally requires this commit to be an ancestor of the PR base. Therefore a single valid ancestor cannot simultaneously provide the 63 original #1218 bytes and the 58 post-#1227 outputs at their exact original paths: at `a37ad...` the latter do not exist; by `a1cf...` the two geography part bytes have changed. Using newer files, relabeling hashes, or using a candidate output as an ancestor would misstate evidence and is not a valid workaround.

Relevant checks: `scripts/evidence-quality.mjs` calls `validateEvidence` with all issue contract pins; `scripts/premerge-evidence.mjs` checks pin-to-file bindings and that baseline commit is an ancestor of the PR base. Read-only verification used Git commit objects and GitHub API file metadata; no files outside the owned path were modified.

## Engineering handoff

The issue contract or trusted evidence model needs an explicit source-vintage-aware pin representation. A safe v2 could bind each baseline descriptor and named issue pin to its own immutable ancestor commit, while preserving current `baseline.commit` semantics for current metrics and retaining global raw/decoded byte limits. The trusted hosted gate, issue contract binding and reviewer receipt should verify that each per-file commit is an ancestor of the PR base and that exact path/whole-file bytes match. Geography owns no shared scripts or gate implementation, so this PR leaves the mismatch visible and does not report a passing evidence gate or full issue completion.

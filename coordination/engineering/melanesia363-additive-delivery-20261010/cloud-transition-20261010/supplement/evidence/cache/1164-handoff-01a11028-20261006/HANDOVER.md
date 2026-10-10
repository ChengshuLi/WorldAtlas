# Issue #1164 account-switch handover

Captured after queue merge and safe owner release on 2026-10-06 UTC. This handover preserves the full #1164 objective; it does not mark the issue complete or narrow its acceptance.

## Current state

- Issue [#1164](https://github.com/ChengshuLi/WorldAtlas/issues/1164) remains **open and incomplete**. The previous claim is released, so a different chat can claim the remaining work using its own exact identity.
- PR [#1168](https://github.com/ChengshuLi/WorldAtlas/pull/1168) merged at `2026-10-06T18:15:11Z` as `48fef180ea85dffa3c335a94a56d3def35a50f3a`.
- Exact reviewed PR head: `1c032b7aa5a5ed8cddaa4d5b52beea00bc35d029`. Queue request `62ce9c99-8af7-451e-9ecf-eab973d308b1`, workflow run [37507684878](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37507684878), accepted result comment `6022589619`. Tested base `f6ddb61a853a488901af5cad6c83de5b7cfa7600`, tested candidate `90207007a8e66b99ecf7db7a5b8753627003b198`; all integration/geography checks passed. Queue deleted its owned temporary candidate and remote author branch.
- Manifest `coordination/engineering/global-successor-audit-1164-20261006-local01/evidence-quality.json` has exact raw SHA-256 `248bdbab114544f100c433a2ac4b40509817493ca018c5bf275b855589279401`.
- Independent merge readback verified all seven actual GitHub PR paths and modes byte-for-byte equal in the reviewed head, squash merge commit and current `origin/main`. Current main tip at readback was the merge commit above. Durable report: `merge-readback-v1.json`, SHA-256 `af24a67fd054cf9f8afaf991867bf4bcfa1aaee2c1eae0b8cbd1a6207109a602`.
- PR [#1150](https://github.com/ChengshuLi/WorldAtlas/pull/1150) remains open at candidate `405f75ce2280dc44172ba596b9ee08513abe437c`; it is not an installed/current geography release.

## Account and ownership handoff

The previous exact worker ID was `01a11028-e91d-7fa1-bf6a-32390106d41d`; claim ID `a7f6c15b-40c9-413d-977f-33fbf0cd9915` on branch `engineering/global-successor-audit-1164-20261006-local01` is now inactive. The official release request `bb55daf7-8b5f-46ca-8a6f-f1cd198feed2` completed successfully in workflow [37510111629](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37510111629), with bot result comment `6022631028` at `2026-10-06T18:17:21.777Z`. Receipt `claim-release-v1.json` SHA-256 `88606129507e4ac2596d04aeee6d71acdfb09a669e3fb8867a44a7d0340755c2` records `accepted:true` and `active:false`.

The own managed work slot was released only after the full ignored cache had been copied and reverified. The local recovery ref `refs/worldatlas-local-recovery/[workspace-ownership-token-omitted]` preserves reviewed head `1c032b7`; the managed worktree and registry slot are gone. No other worker’s slot or claim was touched. A new chat/account must use its own actual `CODEX_THREAD_ID`, submit a fresh #1164 claim, and allocate a fresh managed author workspace; it must not reuse the former ID, claim ID, token, or branch.

## Preserved private audit files

The entire ignored audit cache (733 files, 614,634,457 bytes) is preserved outside the worktree at `audit-cache/`. Every source and destination file was rehashed against the inventory before the source copy was removed. Preservation manifest SHA-256: `9e3b3ad23536f6e4e0f73a454811aeab4a12ae6440fd305dc9ec239359f4a7c8`. The worktree is clean after cache removal.

The cache includes both private full-world preview runs and outputs, the complete 95,174-row legacy-status/three-order preview, candidate native and fresh-priority previews, independent readbacks, earlier failed probes, and checkpoints. `audit-cache/1164-resume-checkpoint-v2.json` and `audit-cache/1164-two-run-independent-readback-v2.json` are useful starting points. All remain **private precommit previews**; no full successor stage is accepted by them. The two-run preview verifies 69 output files but still records a summary-path relocation limit; it is not the required committed-code two-run receipt.

## Remaining acceptance

The accepted #1168 PR covers only generic immutable-input reuse code and synthetic controls. #1164 still requires the actual authenticated successor run, complete global fragment/contact/connectivity/crosswalk evidence, all 95,174 legacy component statuses in all three priority orders, and committed-code two-run receipts with meaningful controls. Native-context and current three-queue work linked to #1184 remains required by #1164. Preserve original measurement vintages, all unknowns and unresolved source limits. Do not claim source authority, water status, ownership, legal/political boundary, geographic approval, or publication/deployment. Do not start a new stage during account transfer until the coordinator authorizes it.


## Public checkpoint

Posted the final public issue checkpoint at https://github.com/ChengshuLi/WorldAtlas/issues/1164#issuecomment-6022667995. Its exact body SHA-256 is `4e7386ea28f7576b75771b198234d9047d542f4e59fb8d04ae897c5aa05defd0`. GitHub API readback confirmed the published body.

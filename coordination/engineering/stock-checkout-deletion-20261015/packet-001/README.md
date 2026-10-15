# Reviewed stock-checkout deletion packet

This is a portable reviewed patch, not an adopted live implementation or integration request. Apply `checkout-only.patch` by hunks to the coherent actual union; do not overlay stale whole files. The source manifest binds all seven postimages and the helper deletion against explicitly composed published PR2046/2047/2048 preimages. Actual accepted publication parent is5a02b6c609fa281ee1b9fcc052c18a941632e8b8, which preserves Papua675cf628 and accepts2046. Components2047/2048 remain reviewed and unmerged in this packet.

The eight-path change replaces the custom full-checkout bootstrap/executor with pinned actions/checkout, retaining exact SHA/tree/detached/source assertions, read-only transient credentials, and existing selected-data sparse selection. It deletes scripts/acquire-ci-checkout.py and its obsolete executor tests without adding a timer, cache or acquisition framework. Pure patch:233 additions/1480 deletions, net1247 lines removed.

Distinct reviewer /root/worktree_lifecycle_pruning_sol accepted the exact bounded packet. Both changed test files passed in full:23 passed,0failed,0skipped;12.507seconds. See validation.json and independent-review.md. Raw private task receipts remain preserved; public copies omit machine checkout locations and do not claim a full accepted composite integration.

Papua run38816577800 completed successfully. Its shard1 acquisition took1464.692seconds: initial filtered fetch0.873seconds, Git materialization1463.792seconds, including1434.996seconds before first file-update progress and28.796seconds of visible materialization. The log does not split network, object processing and disk costs. No wrapper retry/deadlock or stock-checkout timing gain is claimed. The next actual integrated run is the throughput observation.

This packet changes no ownership selection, scientific result, source evidence, accepted authority, map data, current artifact hook or running workflow. No standalone PR or queue request is created. Final actual-head reconciliation and normal integration remain necessary.

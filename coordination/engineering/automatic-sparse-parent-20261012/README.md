# Automatic sparse-parent continuation and truthful proof failures

Refs #1785. This partial engineering delivery preserves the original issue's subsequent adoption/timing obligation.

## Actual failures

After accepted `4278a6176e5530ccafe39f57bb1ab58a60992701`, Native102 automatic continuation prepared its original authority and stopped at temporary-index `git write-tree`: it demanded an absent unrelated inherited promisor blob. The existing managed index could write its tree. The preserved original authority remains the source of the next commit; no SOURCE/NATIVE/rebind result is manufactured.

Hosted package proof run [38323094289](https://github.com/ChengshuLi/WorldAtlas/actions/runs/38323094289) stopped before a receipt existed. The observer's ENOENT concealed the captured frozen subprocess reason, and the failed run retained no artifact. Its actual first cause and package equivalence remain unproved.

## General invariants repaired

- A stage commit extends an exact parent tree. Unchanged inherited objects need not be locally materialized. Only the temporary index uses `write-tree --missing-ok`; the real index remains strict. Exact declared additions and per-product mode/OID checks reject unrelated modifications/deletions anywhere in the tree.
- Every new product is authenticated against the completed journal, written through Git and independently read back, both initially and on interrupted recovery. The one-tree index merge preserves inherited sparse state. No filename-specific exception or unrelated object fetch is added.
- Every returned frozen subprocess outcome is sanitized, bounded and logged before receipt/storage handling. Failure diagnostics are retained separately, including spawn errors, signals, timeout/output limits, missing or malformed receipts and unrelated errors. A diagnostic does not establish assembly or proof success; original assembly/source admissions remain unchanged.

## Verification and limits

`env -u NODE_PATH TMPDIR=<managed-slot>/.cache/test-tmp node --test test/delivery-handoff-advance.test.mjs test/delivery-handoff.test.mjs test/selected-package-proof-driver.test.mjs`

164 tests passed, zero failures/skips. This includes genuine local blobless Git clones with an unavailable origin, absent deep/unrelated and nested sibling objects, exact inherited-entry conservation, intent/object/ref interruption and restored new products, missing-new-product refusal, undeclared modification/deletion refusal, and reproduction of the old strict scratch writer failure. Existing claim, ownership, terminal, collision and once-only controls also passed. The fixture allocator correctly refused the 4.9 GiB `/tmp` mount; running fixtures within the admitted managed workspace satisfied the unchanged storage gate.

No scientific execution, current selection, hosted package equivalence or actual subsequent automatic adoption is claimed. The next steps after ordinary reviewed integration are to resume the preserved Native102 journal and perform the sole genuine hosted proof under the package owner's existing frozen inputs.

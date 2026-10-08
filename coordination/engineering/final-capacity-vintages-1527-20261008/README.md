# Final-capacity historical vintage repair

Issue #1527 repairs the quota-planning inventory, not the geography packet.
The existing shared baseline parser resolves explicit v2 per-file commits and
retains v1 behavior. Every declared historical commit is checked against the PR
base. Complete ordinary Git trees, descriptor/unique-commit/byte budgets,
independent review and subsequent full evidence verification remain mandatory.
Tree reuse is scoped to one fresh inventory invocation.

## Checks

Node 24: `node --test test/final-capacity.test.mjs test/premerge-evidence.test.mjs test/evidence-quality.test.mjs`.
All 72 tests pass with zero skips. Controls include different bytes at the same
path, an input missing from the default baseline, unsupported/missing commits,
nonancestor history, duplicate descriptors, excessive commits, truncated trees,
symlinks, oversized ordinary files and aggregate bytes across vintages. Existing
full final-capacity/merge controls and legacy baseline controls remain active.

The read-only live replay binds the exact reviewed #1512 head in the adjacent
receipt. Both old and corrected inventories use the same API response snapshot:
the old code rejects its legitimate historical path; the corrected inventory
succeeds, retaining 142 distinct OIDs. No merge, scientific approval, full evidence
acceptance or actual quota reservation is inferred from this capacity estimate.
The snapshot is not a new long-term issue authority; normal hosted merge gates
must reread mutable state.

The scheduler wakeup investigation is separate (existing issue #1326). No
scheduler cadence or workflow trigger changes are part of this repair.

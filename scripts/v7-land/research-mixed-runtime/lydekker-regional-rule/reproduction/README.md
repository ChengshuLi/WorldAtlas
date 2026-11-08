# V8 regional policy preparation

The [original policy](../selected-regional-policy.json) records how the
selected island groups were worked out. V8 uses a copy with updated runtime
code pins and the same group choices. The original policy is registered as
`lydekker-whole-island-regional-v1` on decision revision
`v7-list1-wgs84-draft-170` in `atlas.regional_island_rule_sets`.

1. `reconstruct_current_replay.py` reconciles earlier source resolution
   reports with the selected Neon snapshot.
2. `apply_reconciled_current.py` produces the first regional diagnostic.
   The `preview_*` scripts extend it in order through source extents,
   named source groups, nearest groups, government named groups, and reef
   groups. Each consumes a hash-pinned earlier result.
3. The selected choices were recorded in the original policy.
   `prepare_neon_transaction.py` prepares the SQL that registered it.
   `compare.py` checks the regional changes against the historical comparison
   window.

These scripts preserve the original working paths and hash checks. To run
them, first recreate their input workspace with the named snapshot, source
archives, physical components and resolver reports. The two original feature
previews are preserved in `atlas.structured_documents` as
`v8-regional-residual-source-feature-preview` and
`v8-regional-residual-unnamed-feature-preview`. Export their stored JSON text
unchanged to the filenames in the scripts. The original policy records their
SHA-256 values.

The normal [V8 pipeline](../../../../v7-pipeline/README.md) starts from the
already selected policy, regional snapshot and line in Neon. It applies the
policy to the physical components of the current run.

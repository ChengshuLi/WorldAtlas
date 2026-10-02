# Macro reference installation

Issue #33 owns the initial macro release. Preparation and installation are separate from semantic approval, hosting, and regional interior approval. All three ordered source receipts, original inspection ledgers, predecessor identities, historical products, and canonical location footprints remain retained.

From the release-2 prepared baseline, follow `MACRO_FOUNDATION_PREPARATION.md`, then:

```sh
node scripts/install-macro-reference.mjs
```

Inspect the exact report and validation SHA. Apply only that unchanged prepared result with `--apply --expected-validation SHA`. The installer verifies all originals, archives them, writes a crash journal, updates geographic metadata/province lookup only, and rolls back on failure. Retained source inspections remain immutable; current review names/chains are a separately validated projection.

Freeze envelopes with `python scripts/prepare-macro-envelopes.py`; independently check each frozen file, every source location's inclusion, membership pins, child containment and same-tier overlap with `python scripts/verify-macro-envelopes.py --output REPORT`. Numerical overlay ribbons are measured and retained under explicit finite precision. Geometry collections may retain zero-area overlay segments; those segments are not land territories.

Hosted provisioning uses hidden credential stdin:

```sh
node --use-env-proxy scripts/bootstrap-geographic-release.mjs SITE data/geographic-releases --stage-only
node --use-env-proxy scripts/bootstrap-geographic-release.mjs SITE data/geographic-releases --finalize-only
```

Stage sources, identities, bounded memberships and retained archives before publishing matching assets. Finalization verifies the complete staged release server-side and atomically publishes it without re-uploading membership batches. A staging receipt is not public read-back proof. Verify release pins, preserved claims and archives after publication. Keep provider credentials out of Git, logs and command arguments; preserve the Site audience and PostgreSQL/R2 bindings.

After installation, original producer scripts require the pinned release-2 baseline, not the newly installed generation. Its exact changed inputs are gzip archives under `data/reference-migrations/global-macro-reference-v3/before`; original review inputs are separately retained under `data/macro-foundation/retained-inspections`. Restore into a separate checkout, never overwrite current live data to rerun preparation.

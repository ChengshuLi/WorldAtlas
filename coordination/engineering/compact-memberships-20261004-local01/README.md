# Compact membership contract rehearsal

Issue #783, first bounded implementation part. This contract keeps the original
seven public membership fields, exact raw evidence, external IDs and original
identity/geography guard functions. Private integer maps and shared raw evidence
back a guarded public view. Original physical rows remain intact in a private
relation during the isolated rehearsal; rollback refuses to discard new rows.

The service writer stays unchanged. Its existing conflict clause works with the
guarded view: the original guard rejects changed rows and skips exact retries,
including after publication. The isolated rehearsal takes the shared advisory
lock and an explicit table lock. Frozen deployed schema and migrations stay
unchanged. PostgreSQL/PGlite tests do not model concurrent remote sessions.

The initial head's complete test log and evidence manifest are retained. That
head unnecessarily changed the writer; a direct PostgreSQL probe confirmed the
original SQL works, so the final contract tests cover it without the change.

Tests exercise actual PGlite PostgreSQL, original and compact service publication,
byte-distinct JSON spellings, invalid parents and sources, append-only behavior,
failed/corrupt copy, rollback and application-role access with adverse default
privileges. No fixture asserts source geography or historical factual approval.

This is **not yet a production migration**. The helper has no production CLI or
provider credentials. Current-schema/runtime-role/export/recovery inventories,
streamed current backup proof, full-scale compatible measurements and bounded
publisher capacity/maintenance/rollback orchestration are remaining issue parts.
Do not install this representation on Neon before those gates are implemented,
reviewed and handed to the designated publisher. No production storage was
reclaimed and no provider plan was changed by this work.

The prior full six-release benchmark and all its limits remain immutable at
`coordination/engineering/membership-storage-20261004-local01/`. Its physical
measurements describe that prototype, not this forward contract or Neon.

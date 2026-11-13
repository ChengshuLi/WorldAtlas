# Working geography and release records

Neon stores the raw-source catalog, editable geographic records, construction
settings, entity bindings and release manifests. R2 stores the actual raw files
and versioned map/viewer files. GitHub stores the algorithms and schema.

## Connect

Use the existing `worldatlas` database in the WorldAtlas project's working
`continent-review-v1` branch. Copy its direct connection URL from Neon's Connect
dialog into `NEON_DATABASE_URL`. Use the branch selected for the work; do not
create another permanent database. Release publication requires a direct URL,
without `-pooler` in its host, because it uses a session lock.

The selected decision revisions are in
[`scripts/map-build/config.json`](../scripts/map-build/config.json). They are
groups of geographic records inside this database, not Neon branches.

## Find the selected construction

Run these queries with `psql "$NEON_DATABASE_URL"`. The geometry itself need not
be printed. The JSON reference identifies a row in `atlas.structured_documents`:

```sql
SELECT revision, feature_id, evidence->'construction_ref' AS construction
FROM atlas.decision_features ORDER BY revision, feature_id;

SELECT revision, boundary_id, provenance->'construction' AS construction
FROM atlas.decision_mainland_boundaries ORDER BY revision, boundary_id;

SELECT line_id, provenance->'construction' AS construction
FROM atlas.geographic_line_observations ORDER BY line_id;

SELECT revision, route_id, evidence->'construction' AS construction
FROM atlas.decision_routes ORDER BY revision, route_id;
```

Feature references use `source_id`/`version`; boundary, line and route references
use `recipe_id`/`recipe_version`. Read the selected record:

```sql
SELECT document->>'method' AS method, document
FROM atlas.structured_documents
WHERE source_id = 'CONSTRUCTION_ID' AND version = 'VERSION';
```

Its `method` selects the reusable constructor listed in the
[source-import guide](../scripts/source-imports/README.md). Run that command with
the record ID/version and destination revision. Sources resolve through
`atlas.source_assets`; the catalog supplies R2 object locations and hashes.
Construction versions are immutable. Insert a new version for changed settings,
then run it to update the editable output and its construction reference.
Older retained versions may be inputs or evidence for an existing release.

Use PostgreSQL dumps for database backups. A JSON export of immutable documents
must also retain `document::text`: parsed JSON alone loses the original spacing
and key order that its stored checksum verifies.

Map building reads the selected records in one short consistent transaction,
saves that selection locally, and calculates from it after closing the
transaction. Publishing uses those saved inputs, never a fresh live query for
geography or colors. See [map building](../scripts/map-build/README.md) and
[release commands](../scripts/map-releases/README.md).

## Schema and tests

For an empty database only:

```bash
psql "$NEON_DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_initial_schema.sql
```

This creates schema only. Catalog entries, constructions, editable geography,
entity colors and release records are loaded separately from an existing
database backup or source imports. An empty schema cannot produce a map.

`upgrades/` contains schema-only changes for an already initialized database.
The initial schema already includes them; do not apply them again as a setup
sequence. Test future schema changes on disposable PostgreSQL and keep the
initial schema in sync. The working database already has the checked-in upgrades.

`tests/` contains rollback-based SQL checks for source lineage, immutable
documents, entity hierarchy, geographic references, colors and release integrity.
Run `bash database/tests/run.sh` from the repository root. It creates and removes
a local database. Python importer/storage tests add real transaction and
concurrency checks; CI runs both kinds of tests on macOS and Linux.

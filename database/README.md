# Database

Neon holds editable geography, versioned construction settings and the catalog
of raw R2 files. The website reads completed release files. Building a new map
freezes the selected Neon records before calculating cells.

## Schema organization

[`schema.sql`](schema.sql) creates the complete schema for an empty database.
It loads these files in dependency order, within one transaction:

| File | Contents |
| --- | --- |
| [`sources.sql`](schema/sources.sql) | Raw-file identities, source credits and versioned construction documents. |
| [`entities.sql`](schema/entities.sql) | Stable entity IDs/colors, revisioned names/parents and grid-code bindings. |
| [`geographic_decisions.sql`](schema/geographic_decisions.sql) | Imported geometry, decisions, shared explanations, citations, ocean routes and assignment policies. |
| [`mainland.sql`](schema/mainland.sql) | Editable boundaries, raw-source links, assembled seed regions and component witnesses. |
| [`releases.sql`](schema/releases.sql) | Immutable release manifests, approval and official-version/homepage pointers. |

Each table's constraints and supporting functions are kept beside its definition.
These files define structure only. Source records, colors, geographic choices and
construction settings are loaded separately into Neon.

## Initialize an empty database

Use the project environment and a connection URL supplied outside the code:

```bash
psql "$NEON_DATABASE_URL" -X -f database/schema.sql
```

Run the entry point rather than individual schema files. Its relative includes
work regardless of the current directory. A failure rolls back the complete
initialization. An existing `atlas` schema causes initialization to fail.

The working database is already initialized. Creating the schema does not load
the data required to build a map. Restore a database backup to recover existing
records, or load new records through the supported source-import workflow.

## Change an existing database

Update the relevant schema definition. When an existing database needs an
upgrade, put the explicit change under `database/migrations/` in the same PR.
Preserve applied upgrade scripts rather than editing their meaning afterward.

Test the upgrade against a disposable copy of working data before applying it.
Check that upgrading and creating a fresh database produce the same intended
structure. Schema upgrades stay separate from geographic data imports.

Existing databases that still have `source_assets.provenance` can apply
[`001_remove_source_provenance.sql`](migrations/001_remove_source_provenance.sql)
after backing up the source catalog. For databases that still store checksums
and sizes in `structured_documents`, apply
[`002_simplify_structured_documents.sql`](migrations/002_simplify_structured_documents.sql)
after backing up those rows. It also converts `document` to `jsonb`. Fresh
databases already have both changes:

```bash
psql "$NEON_DATABASE_URL" -X -v ON_ERROR_STOP=1 -f database/migrations/001_remove_source_provenance.sql
psql "$NEON_DATABASE_URL" -X -v ON_ERROR_STOP=1 -f database/migrations/002_simplify_structured_documents.sql
```

Documents store their ID, version and `jsonb` content. Importers validate the
settings. Spacing and object-key order do not identify a document. Frozen build
selections include the document values without per-document checksums or sizes.
Existing saved selections and released files remain unchanged. Retain original
contributing records and released input selections when assessing data for deletion.

## Tests

SQL checks cover database guarantees:

| Check | Purpose |
| --- | --- |
| `source_catalog.sql` | Raw-file identity, metadata corrections and source references. |
| `structured_documents.sql` | JSON values, formatting-independent content and immutable document versions. |
| `entity_registry.sql` | Stable IDs, hierarchy relationships and grid-code bindings. |
| `geographic_entity_colors.sql` | Optional colors and valid RGB values. |
| `geographic_decisions.sql` | Geometry records, shared explanations, citations and entity targets. |
| `editable_boundaries.sql` | Editable lines, construction references and retained source links. |
| `policies.sql` | Editable assignment policies and valid policy definitions. |
| `map_releases.sql` | Immutable bundles, approval and publication relationships. |

Run the database checks locally with the same runner used by CI:

```bash
python .github/scripts/run_tests.py --suite database
```

Omit `--suite` to run all Python and SQL suites concurrently. The runner starts
one temporary PostgreSQL server, gives each database-using suite its own empty
database, loads `schema.sql`, and removes the databases afterward. PostgreSQL's
`initdb`, `pg_ctl` and `psql` must be available in the project environment.

Python integration tests stay beside source-import and map-building code. They
cover real writes, rollback, concurrent edits and consistent input selection.
CI runs all suites on macOS and Linux without live Neon credentials.

## Find and regenerate a construction

A construction version describes how to regenerate geometry. A decision revision
selects editable records. A release freezes a completed result.

Features, mainland boundaries, ocean endpoints/routes and selected geographic
lines reference their construction through `construction_id` and
`construction_version`. For example:

```sql
SELECT revision, boundary_id, construction_id, construction_version
FROM atlas.decision_mainland_boundaries
ORDER BY revision, boundary_id;

SELECT document FROM atlas.structured_documents
WHERE source_id = 'CONSTRUCTION_ID' AND version = 'VERSION';
```

Use that exact version with the [source-import command](../src/worldatlas/source_imports/README.md).
The document's `method` selects the constructor. Changed settings get a new
construction version. Successful imports save geometry and its references
together, preserving unrelated notes and relationships. Failed imports leave
the previous record intact. Original supporting
observations can remain without an automatic constructor.

Working decisions are editable directly. Publication approval applies to an
exact release bundle. Raw-file identities remain immutable. Source titles and
credit descriptions can be corrected without uploading duplicate bytes. The raw
catalog has no catch-all metadata column. Construction settings belong in versioned construction records.

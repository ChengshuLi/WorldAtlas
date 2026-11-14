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

Applied upgrades are retained in `migrations/`:

| Upgrade | Existing-database change |
| --- | --- |
| `001_remove_source_provenance.sql` | Remove unused raw-source metadata. |
| `002_simplify_structured_documents.sql` | Remove redundant document checksums/sizes and use JSONB. |
| `003_rename_construction_records.sql` | Rename the construction table and its supporting objects. |

Apply only upgrades that the existing database has not received. Fresh databases
already have their final schema. Back up and test existing data before an upgrade.
Historical input archival/removal is a separate data backfill, after verified R2
uploads; it is not geographic data embedded in the schema SQL.

`construction_records` holds current versioned construction instructions. Importers
validate their settings; no method-specific database validation has been added.
Original/intermediate geographic records still in use remain in their own tables.
Historical release snapshots and superseded pipeline inputs live in the release's
R2 `inputs.json.gz`, tracked by `map_releases`. The archive preserves their original
IDs and versions. Its captured data is separate from editable working records.

## Tests

SQL checks cover database guarantees:

| Check | Purpose |
| --- | --- |
| `source_catalog.sql` | Raw-file identity, metadata corrections and source references. |
| `construction_records.sql` | JSON values, formatting-independent content and immutable document versions. |
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

SELECT document FROM atlas.construction_records
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

# Database

Neon stores editable geography, its source links and versioned construction
settings. Raw files live in R2. Map building freezes the selected records before
calculating cells; publishing serves those completed files rather than querying
editable geography from the website.

## What belongs here

| Records | Purpose |
| --- | --- |
| `source_assets` | One exact raw R2 file per row: source/version, object key, size, checksum and source credit. |
| `structured_documents` | Immutable construction settings, released input snapshots and original processing evidence. |
| Entity registry and category bindings | Stable entity IDs/colors, versioned names/parents, and each grid code's entity and land/water meaning. |
| Features, boundaries and line observations | Imported geometry, its coordinate reference, checksum and construction reference. Original contributing observations remain. |
| Cases and case sources | Shared geographic reasoning and exact source citations. Affiliations can also have their own explanation. |
| Geographic rules | Component selections, mainland witnesses/regions, selected basins, ocean routes/seeds and policies. |
| `map_releases` | One immutable file manifest per numbered candidate or retained official release. |
| `map_publications` | Which release represents each official version and which publication owns the homepage alias. |

A construction version describes how to regenerate geometry. A decision revision
selects editable geographic records. A release freezes a completed result.
Working geography needs no draft/research/acceptance status. Publication approval
applies to the exact release bundle.

The catalog's source identity, original capture provenance, object location, size
and checksum are immutable. Correcting a title, provider description or source
credit does not require uploading another copy of the same bytes.

## Find the selected construction

Geometry records use ordinary foreign keys to the versioned document:

```sql
SELECT revision, feature_id, construction_id, construction_version
FROM atlas.decision_features ORDER BY revision, feature_id;

SELECT revision, boundary_id, construction_id, construction_version
FROM atlas.decision_mainland_boundaries ORDER BY revision, boundary_id;

SELECT line_id, construction_id, construction_version
FROM atlas.geographic_line_observations ORDER BY line_id;

SELECT revision, route_id, construction_id, construction_version
FROM atlas.decision_routes ORDER BY revision, route_id;
```

Read that exact document, then use the shared
[source-import command](../scripts/source-imports/README.md):

```sql
SELECT document FROM atlas.structured_documents
WHERE source_id = 'CONSTRUCTION_ID' AND version = 'VERSION';
```

Its `method` selects the reusable constructor. For changed settings, insert a
new construction version and run it against the intended decision revision.
The importer saves the new geometry and reference together. It preserves
unrelated notes and relationships; a failed calculation leaves the old record.
Some original observations are supporting evidence and have no automatic
constructor. They remain distinct from the selected constructed output.

## Schema and tests

For an empty database:

```bash
psql "$NEON_DATABASE_URL" -v ON_ERROR_STOP=1 -f database/migrations/001_initial_schema.sql
```

The initial SQL creates schema only. Load catalog records, constructions,
editable geography, entity colors and releases from a database backup or the
source-import workflow. Empty tables cannot produce a map.

Test schema changes against disposable PostgreSQL and a copy of the working
data before applying them. Keep the initial schema current. One-off upgrades
are retained with their migration backup, rather than becoming a setup chain.

```bash
bash database/tests/run.sh
```

These SQL checks create a disposable local database and roll back their fixtures.
Importer and map-input tests add real save, rollback, concurrent-edit and replay
checks. CI runs all Python and database suites on macOS and Linux.

Database backups must retain exact document text. Parsing and reformatting a
`document` would invalidate its byte checksum. During cleanup, follow current
construction/source relationships, original contributing records and retained
release manifests, including their frozen input selections. A missing active
reference alone does not make original released input safe to delete.

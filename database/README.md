# Database

Neon holds editable geography, editable construction settings and the catalog
of raw R2 files. The website reads completed release files. Building a new map
freezes the selected Neon records before calculating cells.

## Schema organization

[`schema.sql`](schema.sql) creates the complete schema for an empty database.
It loads these files in dependency order, within one transaction:

| File | Contents |
| --- | --- |
| [`sources.sql`](schema/sources.sql) | Raw-file identities, source credits and editable construction documents. |
| [`construction_contracts.sql`](schema/construction_contracts.sql) | Generated checks for typed construction parameters. |
| [`geographic_entities.sql`](schema/geographic_entities.sql) | Entities with generated IDs, names, hierarchy links and colors, plus grid-code bindings. |
| [`geographic_decisions.sql`](schema/geographic_decisions.sql) | Imported geometry, geographic assignments and citations, ocean routes and assignment policies. |
| [`mainland.sql`](schema/mainland.sql) | Editable boundaries, raw-source links, assembled seed regions and component witnesses. |
| [`releases.sql`](schema/releases.sql) | Immutable release manifests, approval and official-version/homepage pointers. |

`geographic_entities` stores each entity's generated ID, name, hierarchy links and
color together. The top hierarchy level currently uses `continent` for both
continents and top-level oceans. Location-level entities have a land/water class;
map-code bindings also distinguish land from water.

`map_category_bindings` maps grid codes to geographic entities and land/water
classes. Water ownership remains distinct even when every water cell uses the
same display color.

`source_features` stores imported points, polygons and constructed source-figure
lines, with their raw-source and construction links. All five columns are
required. Composed areas retain their contributing feature IDs in the construction
record; the source columns identify their primary provider contribution.
Geometry is always WGS84 longitude first, latitude second, in degrees.
Its database checks enforce supported shape
types, coordinate nesting, finite two-dimensional values, WGS84 ranges and closed
polygon rings. Importers also check geometric validity with GEOS. They select
provider IDs from checksum-verified raw files without copying provider attributes
or maintaining duplicate attribute expectations in Neon.

`geographic_assignments` stores one independently editable whole-component rule
per row: `assignment_id`, `entity_id`, `rationale` and `selection`. The selection
is exactly one object with `relation` and `feature_id`. Supported relations are
`point_component` (the land component containing a point), `contains_component`
(all of a component's land-cell centers inside a polygon), and
`intersects_component` (at least one land-cell center inside a polygon).
`majority_component` selects a whole component when more than half its land-cell
centers are inside the area. This matches broad group outlines without requiring
every coastal cell to fit a coarse source boundary. An exact half is not a match.
Independent alternatives are separate rows. There are no case groups, compound
AND/OR selectors or unrestricted evidence objects in working assignments.

`geographic_assignment_sources` links each assignment to its supporting raw
sources, with a citation section and an interpretation that includes any relevant
limitations. A feature's raw-source link establishes where its geometry came
from; an assignment citation supports why the selected land belongs to its
chosen entity. Those are different relationships.

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

## Updating the working database

`schema.sql` and its included files describe the complete current database.
There is no migration chain to run after creating a fresh database.

For an existing working database, back up its data and test the specific schema
transition on a disposable copy before applying it. Keep one-off transition
scripts with the local maintenance backup, and update the authoritative schema
in the same change as its code and tests. Geographic values are loaded through
imports or edited in Neon, not embedded in schema SQL.

`construction_records` contains one editable recipe per ID. Its structural checks
are generated from the Python constructor signatures and nested types. See
[source-import validation](../src/worldatlas/source_imports/README.md#document-validation).
A changed validator must be applied to the working database and must recheck
existing rows. CI rejects stale generated schema checks.

Builds freeze complete working records. Historical release snapshots live in
R2 `inputs.json.gz` files tracked by `map_releases`; they are not working records
in Neon. Restoring an archive never replaces today's editable geography.

## Tests

SQL checks cover database guarantees:

| Check | Purpose |
| --- | --- |
| `source_catalog.sql` | Raw-file identity, metadata corrections and source references. |
| `construction_records.sql` | Valid construction shapes, required fields, JSON types and editable recipes. |
| `entity_registry.sql` | Stable IDs, hierarchy relationships and grid-code bindings. |
| `geographic_entity_colors.sql` | Optional colors and valid RGB values. |
| `geographic_decisions.sql` | Geometry records, single-feature assignments, citations and entity targets. |
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

One construction ID identifies one editable recipe. Geometry references it by
`construction_id`. Raw assets have immutable IDs; changed bytes get a new ID.
Builds freeze the complete records they read, and releases archive those inputs.

```sql
SELECT boundary_id, construction_id FROM atlas.decision_mainland_boundaries;
SELECT document FROM atlas.construction_records WHERE source_id = 'CONSTRUCTION_ID';
```

Run that ID through the [source-import command](../src/worldatlas/source_imports/README.md).
The document's `method` selects the constructor. Edit settings and rerun the ID
to update working geometry. The old coordinates and settings remain in retained
build/release inputs. Successful imports save geometry and references together;
failed imports preserve existing results and unrelated notes/relationships.

Working decisions are editable directly. Publication approval applies to an
exact release bundle. Raw-file identities remain immutable. Source titles and
credit descriptions can be corrected without uploading duplicate bytes. The raw
catalog has no catch-all metadata column. Construction settings belong in editable construction records.

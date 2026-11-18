# Source imports

These tools read raw geographic files from R2 and save geographic records in Neon. The source catalog identifies each exact file by one immutable `source_id`, its R2 location, byte size and checksum. Changed raw bytes get a new source ID.

- [`osm/`](osm/README.md): archived OpenStreetMap boundaries and selected features.
- [`iho/`](iho/README.md): Complete IHO S-130 sea areas.
- [`features/`](features/README.md): selected vector points and polygons.
- [`traces/`](traces/README.md): boundaries from reviewed points on source figures.
- [`watersheds/`](watersheds/README.md): boundaries from terrain and natural drainage.
- [`atlas_sources/`](atlas_sources/README.md): catalog lookup and verified downloads.

Geographic choices live in editable `atlas.construction_records.document` values. Each construction has one ID and one current recipe. Imported geometry links to that construction by `construction_id`. There are no decision revisions or recipe versions to select. Each map build freezes the full recipes, geometry and raw catalog records it used; release archives retain those copies for replay.

Raw-source arguments use the `SourceId` type. The generated database code follows those declared fields through typed objects and lists, then synchronizes `atlas.construction_sources` on each document save. These foreign-key links make every feature's dependencies queryable through its construction. Source IDs are ordinary strings passed directly to Python; no wrapper or separate primary source is stored on a feature. Lists preserve calculation order; dependency links are unique. Untyped descriptive JSON is not searched for possible source IDs.

## Run one construction

Install the project using the root [environment](../../../environment.yml). Set `NEON_DATABASE_URL` and the required AWS profile outside the code.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

Figure traces need only the construction ID:

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The document's `method` selects a typed function registered once in [`run_import.py`](run_import.py). A record's name does not select Python code. Read the referenced construction rather than assuming a name or remembering a command from a previous chat:

```sql
SELECT id, construction_id FROM atlas.source_features;
SELECT document FROM atlas.construction_records WHERE id = 'CONSTRUCTION_ID';
```

Edit the recipe and rerun the same ID to update working geometry. A successful import saves the geometry under its construction ID. Neon maintains the raw source links when the construction document changes. A failed import leaves its previous geometry intact. Workers calculate independently. At save time, the import verifies the construction is still the one it read and keeps existing feature IDs associated with that construction.

## Regenerate working geometry

```bash
worldatlas-import --all \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The command follows construction links from `source_features`. Each construction runs once and commits independently, so an interrupted batch can be repeated. Receipts under `inputs/receipts/` identify the construction and its result.

The map builder uses the same verified raw-file cache. Both commands check the catalog's byte sizes and checksums before reusing downloads.

Every construction consumes cataloged raw sources and its interpretation settings. No construction depends on another structured feature; grouping existing features belongs to geographic assignments in map building.

## Document validation

Each constructor's typed keyword-only arguments define its fields. An argument without a default is required; a default makes it optional. `NonEmptyText` rejects empty or whitespace-only text. Nested `TypedDict` definitions describe feature selections. `runtime` supplies connections, work paths and the construction ID; it is not a field in the stored document.

[`contracts.py`](contracts.py) derives command validation and PostgreSQL checks from those signatures. Both reject unknown methods/fields, missing required fields and incorrect types. Algorithms additionally check source identities, coordinates, joins and the relationships between geographic choices.

After changing signatures or nested types, regenerate the initial-schema checks:

```bash
python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql
```

For the existing working database, back up and test a one-off upgrade before applying the changed validator. Replacing it must recheck existing rows. Keep the transition script with that maintenance backup. The initial-schema file only creates the function and constraint. CI fails if the committed generated file differs from the Python declarations. Do not maintain another field list in a validator or README.

## Code and tests

`run_import.py` reads the recipe and dispatches to a typed function in a `build_*.py` module. Those modules handle Neon/R2; other modules implement calculations. `features/geometry.py` validates and atomically saves imported geometry. `__init__.py` files define importable packages and enable test discovery.

Tests live beside their code. `test_run_import.py` checks dispatch; `test_contracts.py` checks Python/PostgreSQL agreement and direct SQL writes; `atlas_sources/test_catalog.py` checks file acquisition. Package READMEs describe their algorithm and storage tests.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

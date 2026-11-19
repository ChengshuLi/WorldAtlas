# Source imports

These tools read raw geographic files from R2 and save geographic records in Neon. The source catalog identifies each exact file by one immutable `source_id`, its R2 location, byte size and checksum. Changed raw bytes get a new source ID.

- [`osm/`](osm/README.md): archived OpenStreetMap boundaries and selected features.
- [`iho/`](iho/README.md): Complete IHO S-130 sea areas.
- [`features/`](features/README.md): selected vector points and polygons.
- [`traces/`](traces/README.md): boundaries from reviewed points on source figures.
- [`watersheds/`](watersheds/README.md): boundaries from terrain and natural drainage.
- [`atlas_sources/`](atlas_sources/README.md): catalog lookup and verified downloads.

Each row in `atlas.construction_records` contains an `id`, a `method` and its named `arguments` in JSONB. Imported geometry links to that construction by `construction_id`. Each map build freezes the recipes, geometry and raw catalog records it used. Release archives retain those copies for replay.

Raw-source arguments use the `SourceId` type. The generated database code follows those declared fields through typed objects and lists, then synchronizes `atlas.construction_sources` when the method or arguments are saved. These foreign-key links make every feature's dependencies queryable through its construction. Source IDs are ordinary strings passed directly to Python; no wrapper or separate primary source is stored on a feature. Lists preserve calculation order; dependency links are unique. Untyped descriptive JSON is not searched for possible source IDs.

## Run one construction

Follow the [project setup instructions](../../../README.md#pipeline-code) to install the package and set `NEON_DATABASE_URL`. Methods that download files also need R2 credentials, an endpoint, and a local work directory.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

Figure traces and explicitly stored geometry use coordinates from the construction record. For these methods, `--recipe` is the only flag needed.

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The `method` column selects a typed function registered in [`run_import.py`](run_import.py). Query the construction that produced a feature to see the method and the arguments it takes.

```sql
SELECT id, construction_id FROM atlas.source_features;
SELECT method, arguments FROM atlas.construction_records WHERE id = 'CONSTRUCTION_ID';
```

Edit the recipe and rerun the same construction ID to update working geometry. A construction can produce several features. Each feature is saved under its own ID and links back to the construction. Neon updates the raw-source links when the construction arguments change. A failed import leaves the previous geometry intact. At save time, the importer checks that the recipe still matches the one it used and rejects any feature ID already linked to another construction.

The command prints its result as JSON. `--work-dir` is the local raw-file cache, shared with the map builder. Both commands check the catalog's byte sizes and checksums before reusing downloads.

Every construction cites cataloged raw sources. Figure traces and explicitly stored geometry use coordinates from the construction record. Other methods read the cataloged files. Grouping existing features belongs to geographic assignments in map building.

## Argument validation

Each constructor's typed keyword-only parameters define the keys in `arguments`. A parameter without a default is required. A default makes it optional. `NonEmptyText` rejects empty or whitespace-only text. Nested `TypedDict` definitions describe feature selections. The command supplies `runtime` separately with connections, work paths and the construction ID.

[`contracts.py`](contracts.py) uses Pydantic to turn the signatures into JSON Schema and generates the SQL that calls `pg_jsonschema`. Neon rejects unknown methods and fields, missing required fields, and incorrect types when a recipe is saved. Constructors check source identities, coordinates, joins, and the relationships between geographic choices when the recipe runs.

After changing signatures or nested types, regenerate the initial-schema checks:

```bash
python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql
```

For the existing working database, back up and test a one-off upgrade before applying the new argument validator and source-ID extractor. Recheck existing rows against the new validator. Keep the transition script with that maintenance backup. CI checks that the generated SQL matches the Python declarations.

## Code and tests

The `IMPORTERS` registry in [`run_import.py`](run_import.py) shows which function runs each method. Constructors coordinate file access, calculations, and saving. [`features/geometry.py`](features/geometry.py) validates and saves imported geometry in one transaction.

Tests live beside their code. `test_run_import.py` checks dispatch, `test_contracts.py` checks the generated constraints against database writes, and `atlas_sources/test_catalog.py` checks file acquisition. Package READMEs describe their algorithm and storage tests.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

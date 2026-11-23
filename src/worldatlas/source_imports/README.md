# Source imports

These tools read raw geographic files from R2 and save geographic records in Neon. The source catalog identifies each exact file by one immutable `source_id`, its R2 location, byte size and checksum. Changed raw bytes get a new source ID.

## Use

### Run one construction

Follow the [project setup instructions](../../../README.md#pipeline-code) to install the package and set `NEON_DATABASE_URL`. Methods that download files also need R2 credentials and a local work directory.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

Figure traces and explicitly stored geometry use coordinates from the construction record. For these methods, `--recipe` is the only flag needed.

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The `method` column selects a typed function registered in [`run_import.py`](run_import.py). Query the construction that produced a feature to see the method and the arguments it takes.

```sql
SELECT id, construction_id FROM atlas.source_features;
SELECT method, basis, arguments FROM atlas.construction_records WHERE id = 'CONSTRUCTION_ID';
```

Edit the recipe and rerun the same construction ID to update working geometry. A construction can produce several features. Each feature is saved under its own ID and links back to the construction. Outputs omitted from an edited recipe stay in Neon until explicitly removed. Neon updates the raw-source links when the construction arguments change. A failed import leaves the previous geometry intact. At save time, the importer checks that the recipe still matches the one it used and rejects any feature ID already linked to another construction.

The command prints a JSON result identifying the saved features. `--work-dir` is the local raw-file cache, shared with the map builder. Both commands check the catalog's byte sizes and checksums before reusing downloads.

Every construction cites cataloged raw sources. Figure traces and explicitly stored geometry use coordinates from the construction record. Other methods read the cataloged files. Grouping existing features belongs to geographic assignments in map building.

## How it works

[`shared/`](shared/) holds the recipe contracts, input acquisition, and storage workflow used by the import methods. Source imports and map building use [`worldatlas.source_assets`](../source_assets/README.md) for catalog lookup and verified downloads and [`worldatlas.geodesy.geojson`](../geodesy/geojson.py) for GeoJSON validation.

Each row in `atlas.construction_records` has an `id`, a `method`, a nonblank `basis` explaining the construction, and the method's named `arguments` in JSONB. The importer passes the arguments to the method. Imported geometry links to the construction by `construction_id`. Each map build freezes the recipes and their explanations along with the geometry and raw catalog records it used. Release archives retain those copies for replay.

Raw-source arguments use the `SourceId` type. The generated database code follows those declared fields through typed objects and lists, then synchronizes `atlas.construction_sources` when the method or arguments are saved. These foreign-key links make every feature's dependencies queryable through its construction. Source IDs are ordinary strings passed directly to Python; no wrapper or separate primary source is stored on a feature. Lists preserve calculation order; dependency links are unique. Untyped descriptive JSON is not searched for possible source IDs.

### Argument validation

Each constructor's typed keyword-only parameters define the keys in `arguments`. A parameter without a default is required. A default makes it optional. `NonEmptyText` rejects empty or whitespace-only text. Nested `TypedDict` definitions describe feature selections. The command supplies `runtime` separately with connections, work paths and the construction ID.

[`shared/contracts.py`](shared/contracts.py) uses Pydantic to turn the signatures into JSON Schema and generates the SQL that calls `pg_jsonschema`. Neon rejects unknown methods and fields, missing required fields, and incorrect types when a recipe is saved. Constructors check source identities, coordinates, joins, and the relationships between geographic choices when the recipe runs.

After changing signatures or nested types, regenerate the initial-schema checks:

```bash
python -m worldatlas.source_imports.shared.contracts database/schema/construction_contracts.sql
```

For the existing working database, back up and test a one-off upgrade before applying the new argument validator and source-ID extractor. Recheck existing rows against the new validator. Keep the transition script with that maintenance backup. CI checks that the generated SQL matches the Python declarations.

## Code and tests

- [`vector/`](vector/README.md) implements `selected_vector_features` for provider vector datasets.
- [`interpreted/`](interpreted/README.md) implements `interpreted_geometry` for reviewed coordinates stored in a recipe.
- [`osm/`](osm/README.md) implements `selected_osm_features` and `osm_way_chain` for archived OpenStreetMap objects.
- [`iho/`](iho/README.md) implements `s130_areas` for complete IHO sea areas.
- [`traces/`](traces/README.md) implements `geodesic_trace` for lines from reviewed source-figure points.
- [`watersheds/`](watersheds/README.md) implements `watershed_boundary` for lines derived from terrain and natural drainage.

The `IMPORTERS` registry in [`run_import.py`](run_import.py) points to each typed method. [`shared/sources.py`](shared/sources.py) resolves the method's file and evidence IDs in one catalog query, then acquires the files it reads. [`shared/storage.py`](shared/storage.py) validates the output and saves it in one transaction after checking the recipe snapshot.

Tests live beside their code. `test_run_import.py` checks dispatch. The tests in `shared/` cover generated SQL and database constraints, mixed file acquisition, and atomic feature saves. `worldatlas.source_assets.test_source_assets` checks the raw-file cache. Package READMEs describe their construction tests.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

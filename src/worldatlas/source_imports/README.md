# Source imports

These tools read raw geographic sources and save the selected geometry and
construction decisions in Neon. Raw source files stay in R2; Neon's source
catalog identifies their versions and checksums.

- [`osm/`](osm/README.md): assemble archived OpenStreetMap boundaries and selected features.
- [`iho/`](iho/README.md): import selected IHO S-130 routes and sea areas.
- [`features/`](features/README.md): import selected vector and point-table geometry into Neon.
- [`traces/`](traces/README.md): construct final boundaries from reviewed points
  traced from source figures.
- [`watersheds/`](watersheds/README.md): construct boundaries from elevation,
  natural waterways and source basin geometry.
- [`atlas_sources/`](atlas_sources/README.md): shared Neon recipe/catalog reads and verified
  R2 downloads.

Geographic selections belong in Neon construction records. Reusable parsing and
construction code belongs here. The [map builder](../map_build/README.md)
uses the selected structured records, together with large raw raster/vector
inputs, to produce map cells.

## Code organization

`run_import.py` selects the method. After installing the project, use `worldatlas-import`. Each method's `build_*.py` coordinates its
Neon/R2 workflow; the other modules implement the calculations. `atlas_sources`
contains the catalog and verified-file functions also used by map building.
`source_io.py` saves mainland boundaries and validates their assembled regions. Calculation modules do not query Neon or R2.
Workers calculate independently. Saves affecting the same mainland region wait
for one another so validation sees both committed edits.
The assembled region must close and form a valid polygon before the save commits.

Tests live beside the code they exercise. The root `test_run_import.py` covers
method selection; `test_contracts.py` checks Python/PostgreSQL agreement and direct SQL rejection.
`atlas_sources/test_catalog.py` covers downloads and multipart files.
Each package README identifies its calculation and storage tests.
The `__init__.py` files mark importable packages and enable test discovery.

The project [`environment.yml`](../../../environment.yml) pins Python, GDAL/PROJ and Python
packages for these importers. It also installs PostgreSQL for disposable database
tests and the dependencies used by related pipeline checks in CI. One file
defines the environment; a separate Python requirements file is unnecessary.

## Choose a construction record

Use one entry point for all construction methods:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID VERSION
```

The command reads the record from `atlas.construction_records`. Its JSON
`method` selects the constructor through the authoritative
[`IMPORTERS` mapping in `run_import.py`](run_import.py). The supported methods
and their handlers are maintained there; this README does not duplicate the list.

The record ID identifies data; its name does not select Python code.
All file-backed imports additionally require `--revision`,
`--r2-endpoint` and `--work-dir`. Traced boundaries need only the record ID and
version. Set `NEON_DATABASE_URL` and any required AWS profile outside the code.
A supplied work directory also receives a JSON receipt after a successful run.

Use the [database queries](../../../database/README.md#find-and-regenerate-a-construction)
to find the construction ID/version selected by an editable record. Use that
reference rather than assuming that the largest version number is selected.
The destination revision is the record's revision, also selected by the map
configuration. Import changed source geometry first, then run map building.

For example, the Lydekker construction record can be run with:

```bash
worldatlas-import \
  --recipe lydekker-boundary-construction 1
```

## Document validation

Each constructor in `build_*.py` declares its document fields as typed keyword-only
arguments. An argument without a default is required; a default makes it optional.
`NonEmptyText` rejects empty text and text containing only spaces, tabs or line
breaks. Nested `TypedDict` definitions describe selected features and routes.
The function's name supplies `method`; `IMPORTERS` registers the functions once.

[`contracts.py`](contracts.py) reads those signatures for both command validation
and generated PostgreSQL checks. Unknown methods, unknown fields, missing required
fields and incorrect JSON types are rejected, including direct SQL inserts.
Defaults are applied when Python calls the constructor. `runtime` contains the
connections, work directory, destination revision and construction identity;
it is created by the command and is not part of the stored document.

The constructors still check source identity, coordinates, selections and joins
while calculating geometry. Typed fields do not replace those geographic checks.
For compound geographic operations, dictionary settings are interpreted and
checked by the corresponding algorithm.

After changing a signature or its nested types, regenerate the database checks:

```bash
python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql
```

Update the initial schema and add an explicit, transactional upgrade under
`database/migrations/` containing the generated SQL. Applying that upgrade
rechecks every existing construction. CI compares the generated SQL with the
committed file before running tests. Do not edit generated predicates or keep
another field list in a validator. Use the constructor signature for the current
required fields, optional fields and types; examples below explain their use.

## Regenerate the selected inputs

To rerun every construction contributing to selected decision revisions:

```bash
worldatlas-import \
  --revisions MAINLAND_REVISION REGIONAL_REVISION WATER_REVISION OCEAN_REVISION \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

Use the revisions from the map configuration. The command follows each record's
construction foreign key and uses that exact version. It includes enabled line
partitions and avoids repeating a construction selected by several output rows.
Each import saves atomically; if a later one fails, earlier successful imports
remain available and the command can be repeated. Then run the map builder.

Receipts include the construction ID, version and destination revision. Their
filenames are derived from the construction identity so provider identifiers cannot become file paths.

## Local source cache

Use `/absolute/path/to/worldatlas-work/inputs` as `--work-dir` for source
imports. The map command uses that same `inputs/` directory beneath its work
directory. Both tools verify the cataloged sizes and checksums and reuse the
same raw bytes. Import receipts live under `inputs/receipts/`.

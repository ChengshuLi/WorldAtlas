# Source imports

These tools read raw geographic files from R2 and save geographic records in Neon.
The source catalog identifies each exact file by one immutable `source_id`, its
R2 location, byte size and checksum. Changed raw bytes get a new source ID.

- [`osm/`](osm/README.md): archived OpenStreetMap boundaries and selected features.
- [`iho/`](iho/README.md): IHO S-130 routes and sea areas.
- [`features/`](features/README.md): selected vector and point-table geometry.
- [`traces/`](traces/README.md): boundaries from reviewed points on source figures.
- [`watersheds/`](watersheds/README.md): boundaries from terrain and natural drainage.
- [`atlas_sources/`](atlas_sources/README.md): catalog lookup and verified downloads.

Geographic choices live in editable `atlas.construction_records.document` values.
Each construction has one ID and one current recipe. Imported geometry links to
that construction by `construction_id`. There are no decision revisions or recipe
versions to select. Each map build freezes the full recipes, geometry and raw
catalog records it used; release archives retain those copies for replay.

## Run one construction

Install the project using the root [environment](../../../environment.yml).
Set `NEON_DATABASE_URL` and the required AWS profile outside the code.

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

Figure traces need only the construction ID:

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The document's `method` selects a typed function registered once in
[`run_import.py`](run_import.py). A record's name does not select Python code.
Read the referenced construction rather than assuming a name or remembering a
command from a previous chat:

```sql
SELECT boundary_id, construction_id FROM atlas.decision_mainland_boundaries;
SELECT document FROM atlas.construction_records WHERE source_id = 'CONSTRUCTION_ID';
```

Edit the recipe and rerun the same ID to update working geometry. Successful
imports save geometry and source relationships together, retaining unrelated
notes and links. A failed calculation or write leaves previous geometry intact.
Workers calculate independently; writes to boundaries sharing a region wait for
one another so region validation sees committed changes.

## Regenerate working geometry

```bash
worldatlas-import --all \
  --r2-endpoint R2_ENDPOINT \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The command follows construction links from features, boundaries, ocean routes,
endpoints and enabled geographic line rules. Each construction runs once. Each
successful import commits independently, so an interrupted batch can be repeated.
Receipts under `inputs/receipts/` identify the construction and its result.

The map builder uses the same verified raw-file cache. Both commands check the
catalog's byte sizes and checksums before reusing downloads.

## Document validation

Each constructor's typed keyword-only arguments define its fields. An argument
without a default is required; a default makes it optional. `NonEmptyText` rejects
empty or whitespace-only text. Nested `TypedDict` definitions describe feature
and route selections. `runtime` supplies connections, work paths and the
construction ID; it is not a field in the stored document.

[`contracts.py`](contracts.py) derives command validation and PostgreSQL checks
from those signatures. Both reject unknown methods/fields, missing required
fields and incorrect types. Algorithms additionally check source identities,
coordinates, joins and the relationships between geographic choices.

After changing signatures or nested types, regenerate the initial-schema checks:

```bash
python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql
```

For the existing working database, back up and test a one-off upgrade before
applying the changed validator. Replacing it must recheck existing rows. Keep the
transition script with that maintenance backup. The initial-schema file only
creates the function and constraint.
CI fails if the committed generated file differs from the Python declarations.
Do not maintain another field list in a validator or README.

## Code and tests

`run_import.py` reads the recipe and dispatches to a typed function in a
`build_*.py` module. Those modules handle Neon/R2; other modules implement
calculations. `source_io.py` saves mainland boundaries and validates their assembled
regions. `__init__.py` files define importable packages and enable test discovery.

Tests live beside their code. `test_run_import.py` checks dispatch;
`test_contracts.py` checks Python/PostgreSQL agreement and direct SQL writes;
`atlas_sources/test_catalog.py` checks file acquisition. Package READMEs describe
their algorithm and storage tests.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

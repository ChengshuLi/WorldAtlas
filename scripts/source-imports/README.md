# Source imports

These tools read raw geographic sources and save the selected geometry and
construction decisions in Neon. Raw source files stay in R2; Neon's source
catalog identifies their versions and checksums.

- [`osm/`](osm/README.md): join archived OpenStreetMap ways into a boundary.
- [`iho/`](iho/README.md): import selected IHO S-130 ocean boundary routes.
- [`traces/`](traces/README.md): construct final boundaries from reviewed points
  traced from source figures.
- [`watersheds/`](watersheds/README.md): construct boundaries from elevation,
  natural waterways and source basin geometry.
- [`source_io.py`](source_io.py): shared Neon recipe/catalog reads and verified
  R2 downloads.

Geographic selections belong in Neon construction records. Reusable parsing and
construction code belongs here. The [map builder](../map-build/pipeline/README.md)
uses the selected structured records, together with large raw raster/vector
inputs, to produce map cells.

## Code organization

`run_import.py` selects the method. Each method's `build_*.py` coordinates its
Neon/R2 workflow; the other modules implement the calculations. `source_io.py`
contains the catalog, verified-file and mainland-boundary save functions shared
by those workflows. Calculation modules do not query Neon or R2.
Workers calculate independently. Saves affecting the same mainland region wait
for one another so its saved polygon checksum includes both edits.
The assembled region must close and form a valid polygon before the save commits.

Tests live beside the code they exercise. The root `test_run_import.py` covers
method selection; `test_source_io.py` covers downloads and multipart files.
Each package README identifies its calculation and storage tests.
The four `__init__.py` files mark importable packages and enable test discovery.

The project [`environment.yml`](../../environment.yml) pins Python, GDAL/PROJ and Python
packages for these importers. It also installs PostgreSQL for disposable database
tests and the dependencies used by related pipeline checks in CI. One file
defines the environment; a separate Python requirements file is unnecessary.

## Choose a construction record

Use one entry point for all construction methods:

```bash
PYTHONPATH=scripts/source-imports python3 -m run_import \
  --recipe CONSTRUCTION_ID VERSION
```

The command reads the record from `atlas.structured_documents`. Its JSON
`method` selects the constructor through the explicit `IMPORTERS` mapping in
[`run_import.py`](run_import.py):

| Record method | Constructor |
| --- | --- |
| `osm_way_chain` | `osm.build_boundary` |
| `s130_rhumb_routes` | `iho.build_routes` |
| `smooth_latitude_trace` | `traces.build_boundary` |
| `watershed_boundary` | `watersheds.build_boundary` |

The record ID identifies data; its name does not select Python code.
OSM, IHO and watershed imports additionally require `--revision`,
`--r2-endpoint` and `--work-dir`. Traced boundaries need only the record ID and
version. Set `NEON_DATABASE_URL` and any required AWS profile outside the code.
A supplied work directory also receives a JSON receipt after a successful run.

For example, the Lydekker construction record can be run with:

```bash
PYTHONPATH=scripts/source-imports python3 -m run_import \
  --recipe lydekker-boundary-construction 1
```

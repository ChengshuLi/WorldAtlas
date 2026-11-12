# IHO S-130 route processing

Read selected rhumb construction lines from an IHO S-130 dataset and save their
endpoints, route definitions, and ordered endpoint links in Neon.

- [`s130.py`](s130.py) reads a local ZIP, checks the archive and GML checksums,
  selects the source lines, and extracts their endpoints in the chosen direction.
- [`build_routes.py`](build_routes.py) reads a construction record from Neon,
  downloads the cataloged source from R2, extracts the routes, and saves them.
- [`source_io.py`](../source_io.py) provides the catalog, document-reading, and
  download functions also used by the OSM tools.

## Construction record

Store the geographic selections in the existing `atlas.structured_documents`
table. Each record version contains a JSON object like this:

```json
{
  "method": "s130_rhumb_routes",
  "source_id": "raw-source-id",
  "source_version": "raw-source-version",
  "gml_member": "path/inside/archive.gml",
  "gml_sha256": "GML_FILE_SHA256",
  "max_step_km": 0.05,
  "basis": "An explanation of how the selected source lines define the routes.",
  "routes": [
    {
      "route_id": "target-route-id",
      "construction_line_id": "source-line-id",
      "reverse": false,
      "endpoint_names": ["Start", "End"]
    }
  ]
}
```

`reverse` chooses the direction of the source line. The names follow the chosen
direction. Coordinates come from the construction line itself and retain their
source decimal precision. `max_step_km` tells the map builder how closely to
sample each spherical rhumb route; it must be greater than zero and at most 1.
Endpoint IDs default to `ROUTE_ID-endpoint-0` and `ROUTE_ID-endpoint-1`. To update
existing endpoints with different IDs, supply `endpoint_ids` in the chosen order.

A meridian selection can set `extend_to_south_grid_edge` to `true`. Its southern
endpoint keeps the source coordinate in Neon and uses `grid_south_edge` as its
derivation. The map builder extends it to the outer edge of the final grid row.
It requires the source endpoint to fall within that row.

Add selections to the list to process more lines from the same dataset.
To change an immutable construction record, insert a new version.

## Run

Use Python 3.11 or later with `boto3` and `psycopg`. Set `NEON_DATABASE_URL` to
the working database and configure R2 access through `AWS_PROFILE`.
Run from the repository root, replacing the uppercase placeholders and local
work path with your settings:

```bash
PYTHONPATH=scripts/source-imports python3 -m run_import \
  --recipe CONSTRUCTION_ID VERSION \
  --revision DECISION_REVISION \
  --r2-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --work-dir /path/to/work-directory
```

The selected record identifies the raw source version in `atlas.source_assets`.
The download is checked against that catalog entry and reused on later runs.

The command saves the selected records in `atlas.decision_endpoints`,
`atlas.decision_routes`, and `atlas.decision_route_points` together in one
transaction. It updates those selections and retains other evidence fields.
Unselected routes are left in place. Evidence records the construction record,
raw source, GML line IDs, and checksums.

Endpoints carry exact coordinate fractions. The map builder uses those fractions
when constructing the final route and resolves the selected grid-edge rule.

## Tests

`test_s130.py` checks GML selection, exact coordinates and route settings.
`test_build_routes.py` checks the Neon/R2 workflow, exported source links and
database transactions.

Run these tools' tests, including the common source helpers and OSM regression
tests, from the repository root:

```bash
PYTHONPATH=scripts/source-imports python3 -m unittest discover \
  -s scripts/source-imports -p 'test_*.py'
```

Set `WORLDATLAS_TEST_DATABASE_URL` to a disposable local PostgreSQL database with
the [initial schema](../../../database/migrations/001_initial_schema.sql) to
include the database write and rollback tests.

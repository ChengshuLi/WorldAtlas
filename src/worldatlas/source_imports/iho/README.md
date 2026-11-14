# IHO S-130 geographic geometry

[`areas.py`](areas.py) imports selected complete sea areas into
`atlas.source_features` through the common
[`feature import workflow`](../features/README.md). Select areas by their stable
provider MRN. Linked parts sharing one MRN are combined; a parent with its own
surface retains that surface. Holes, dateline crossings and explicit polar caps
are preserved. `test_areas.py` covers those cases.

S-130 encodes area surfaces as `LinearRing` vertices and supplies separate
construction-line records. Area imports preserve the encoded surface. Route
imports apply each selected construction line's declared rhumb interpolation.

An `s130_areas` construction supplies `source_id`, `basis`,
`gml_member`, `gml_sha256` and `selections`. Each selection specifies the output
`feature_id` and provider MRN in `source_feature_id`.

The same `s130_areas` method can import ocean polygons used to verify selected
interior starting points. These polygons remain ocean inputs; they are not added
to the active nearest-continent basin list. An endpoint with derivation
`source_area_interior_point` names its imported `feature_id`; ocean assignment
checks that the point is strictly inside that polygon.

## Ocean boundary routes

Read selected rhumb construction lines from an IHO S-130 dataset and save their
endpoints, route definitions, and ordered endpoint links in Neon.

- [`s130.py`](s130.py) reads a local ZIP, checks the archive and GML checksums,
  selects the source lines, and extracts their endpoints in the chosen direction.
- [`build_routes.py`](build_routes.py) reads a construction record from Neon,
  downloads the cataloged source from R2, extracts the routes, and saves them.
- [`atlas_sources/catalog.py`](../atlas_sources/catalog.py) provides the catalog, document-reading, and
  download functions also used by the OSM tools.

## Construction record

The typed constructor signature defines required fields, optional fields and
types. [Shared validation](../README.md#document-validation) enforces these in
Python and PostgreSQL; the example below explains the settings.

Store the geographic selections in the existing `atlas.construction_records`
table. Each record contains a JSON object like this:

```json
{
  "method": "s130_rhumb_routes",
  "source_id": "raw-source-id",
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
Edit the construction record and rerun the same ID.

## Run

Use the shared [project environment](../../../../environment.yml). Set `NEON_DATABASE_URL` to
the working database and configure R2 access through `AWS_PROFILE`.
Run from the repository root, replacing the uppercase placeholders and local
work path with your settings:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID \
  --r2-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

The selected record identifies the raw source ID in `atlas.source_assets`.
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
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database and includes the write and rollback tests.

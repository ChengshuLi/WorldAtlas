# Ocean assignment

Assign residual marine water to the Atlantic, Pacific, Indian, or Arctic Ocean.
The pipeline first assigns continental water and named seas, then runs this
stage on the remaining water. Longitude wraps around the map.

## Inputs from Neon

The working `v8-ocean` revision contains:

- Four ocean seed points, selected inside the cataloged Natural Earth marine
  features.
- Boundary routes, endpoints, and ordered endpoint links imported from IHO
  S-130. The [source importer](../../../source-imports/iho/README.md) reads the
  construction selections from Neon and the original archive from R2.
- One ocean-fill policy listing the routes and seeds, four-edge connectivity,
  longitude wrapping, and boundary tie rules.

The pipeline freezes these records in a checksummed snapshot and binds it to
this run's physical grid and prefilled water assignments. Named-sea boundaries
are separate inputs and are not changed by the S-130 ocean route import.

## Routes and grid edges

`ocean_fill_runner.py` supports longitude/latitude polylines, meridians,
WGS84 geodesics, and spherical rhumbs. S-130's selected construction lines
specify rhumbs: constant-bearing curves interpolated in spherical Mercator
coordinates. The `max_step_km` parameter controls sampling, with values in
(0, 1]. Geodesic routes also require matching PyProj and PROJ version pins.

Endpoints preserve the source coordinates as exact fractions. A southern
meridian endpoint with the `grid_south_edge` derivation extends to the outer
edge of the final row, provided its source latitude lies within that row. This
closes the boundary when a whole grid row extends slightly beyond the source's
southern limit.

## Outputs and checks

The runner rasterizes routes into blocked cell edges and flood-fills from the
four seeds. It emits the ocean assignment layer, barrier edges, and a report
of unseeded components. Two different ocean seeds reaching the same component
stop the build. The pipeline handles unseeded enclosed water in the following
closed-water stage and verifies the final composition.

The end-to-end pipeline supplies the runner's snapshot, physical row/run files,
prefill directory and plan, candidate-build manifest, and their checksums.
Use the [pipeline command](../../pipeline/README.md) for a complete map build.

## Tests

```bash
python3 -m unittest discover -s scripts/map-build/stages/ocean -p 'test_*.py'
```

The tests cover separated basins, longitude wrapping, unseeded water, route
interpolation, southern grid-edge extension, input validation, and output checks.

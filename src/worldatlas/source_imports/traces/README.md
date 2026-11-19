# Boundaries traced from source figures

Build one final boundary by joining reviewed control points stored in Neon with WGS84 geodesics. Every control point is preserved. The points include the intended path through gaps and around islands; there is no later adjustment stage.

[`geodesic.py`](geodesic.py) contains `geodesic_trace` and the calculation that joins consecutive control points. The [shared WGS84 sampler](../../geodesy/wgs84.py) also serves watershed connectors. The constructor checks the cited raw sources and saves the final geometry to Neon.

## Construction record

The typed constructor signature defines required fields, optional fields, and types. [Neon validates the arguments](../README.md#argument-validation) when the recipe is saved. The constructor checks the geometry when it runs.

Set `method` to `geodesic_trace` on the construction row. Use `basis` to record the figure and page references, how the points were chosen, and any inferred connections. Store the settings below in the `arguments` column.

| Field | Meaning |
| --- | --- |
| `source_ids` | The contributing raw sources in Neon's catalog; a nonempty list without duplicates |
| `feature_id` | The output line in `atlas.source_features` |
| `points` | Selected `[longitude, latitude]` points in boundary order |
| `max_step_metres` | Maximum spacing between generated coordinates along each geodesic |

The path may run in any direction. Consecutive points must be distinct, and the boundary must not cross or retrace itself. The constructor produces one LineString and rejects paths that cross the antimeridian. Invalid coordinates or sampling settings stop before saving.

The original source figure stays in R2. A reviewer reads it and records the chosen points in `arguments` and the rationale in `basis`. The constructor uses the saved points directly.

The final boundary is generated directly from the chosen points. Intermediate traces and smoothed boundaries are not required inputs or separately saved outputs. To edit the construction, edit its record and rerun the same ID.

## Run

Use the shared [project environment](../../../../environment.yml) and set `NEON_DATABASE_URL` to the working database. The working recipes are `lydekker-boundary-construction` for Lydekker’s line and `aegean-boundary-construction` for the Aegean boundary. The command reads the recipe’s `method` and calls `geodesic_trace`.

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The command saves the geometry and its construction ID. Source links connect the construction to its raw files. Regional assignment rules reference the saved feature separately.

## Tests

[`test_geodesic.py`](test_geodesic.py) checks geodesic paths, control-point preservation, spacing, and invalid geometry. [`test_trace_import.py`](test_trace_import.py) checks stored constructions, source references, repeat runs, and failed writes.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner provisions a disposable PostgreSQL database and includes database writes, repeat runs, edits and rollback checks.

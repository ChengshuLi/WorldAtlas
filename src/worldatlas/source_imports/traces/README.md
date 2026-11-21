# Boundaries traced from source figures

[`geodesic.py`](geodesic.py) checks `source_ids` against the Neon source catalog and uses `points` and `max_step_metres` to generate one boundary. The [shared WGS84 sampler](../../geodesy/wgs84.py) joins consecutive control points while preserving each point and limiting the spacing along the line.

## Use

Use the shared [project environment](../../../../environment.yml) and set `NEON_DATABASE_URL` to the working database. The working recipes are `lydekker-boundary-construction` for Lydekker’s line and `aegean-boundary-construction` for the Aegean boundary. The command reads the recipe’s `method` and calls `geodesic_trace`.

```bash
worldatlas-import --recipe lydekker-boundary-construction
```

The command saves the geometry and its construction ID. Source links connect the construction to its raw files. Regional assignment rules reference the saved feature separately.

## How it works

### Construction record

The typed constructor signature defines required fields, optional fields, and types. [Neon validates the arguments](../README.md#argument-validation) when the recipe is saved. The constructor checks the geometry when it runs.

Set `method` to `geodesic_trace` on the construction row. Use `basis` to record the figure and page references, how the points were chosen, and any inferred connections. Store the settings below in the `arguments` column.

| Field | Meaning |
| --- | --- |
| `source_ids` | The contributing raw sources in Neon's catalog; a nonempty list without duplicates |
| `feature_id` | The output line in `atlas.source_features` |
| `points` | Selected `[longitude, latitude]` points in boundary order |
| `max_step_metres` | Maximum spacing between generated coordinates along each geodesic |

The path may run in any direction. Consecutive points must be distinct, and the boundary must not cross or retrace itself. The constructor produces one LineString and rejects paths that cross the antimeridian. Invalid coordinates or sampling settings stop before saving.

The original figure stays in R2. To revise its interpretation, update the control points in `arguments` and the rationale in `basis`, then rerun the same construction ID.

## Code and tests

[`test_geodesic.py`](test_geodesic.py) checks the sampled paths and rejects invalid geometry. [`test_trace_import.py`](test_trace_import.py) uses disposable PostgreSQL to check repeat imports, preserved links, and rejected edits.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

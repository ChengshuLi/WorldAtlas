# Boundaries traced from source figures

Build one final boundary by joining reviewed control points stored in Neon with WGS84 geodesics. Every control point is preserved. The points include the intended path through gaps and around islands; there is no later adjustment stage.

- [`geodesic.py`](geodesic.py) joins consecutive control points without smoothing. The [shared WGS84 sampler](../../geodesy/wgs84.py) also serves watershed connectors.
- [`build_boundary.py`](build_boundary.py) reads a construction record and its raw-source catalog entries, then writes the final geometry to Neon.

## Construction record

The typed constructor signature defines required fields, optional fields and types. [Shared validation](../README.md#argument-validation) enforces them in Python and PostgreSQL.

Set `method` to `geodesic_trace` on the construction row. Store the settings below in its `arguments` column.

| Field | Meaning |
| --- | --- |
| `source_ids` | The contributing raw sources in Neon's catalog; a nonempty list without duplicates |
| `feature_id` | The output line in `atlas.source_features` |
| `source_feature_id` | The selected figure or other identifiable part of the raw document |
| `basis` | How the figure was interpreted, including inferred connections and extensions |
| `points` | Selected `[longitude, latitude]` points in boundary order |
| `max_step_metres` | Maximum spacing between generated coordinates along each geodesic |
| `source_location` | Optional location or calibration notes for the source figure |

The path may run in any direction. Consecutive points must be distinct, and the boundary must not cross or retrace itself. Longitude-seam crossings require split source geometry. Invalid coordinates or sampling settings stop before saving.

The original source figure stays in R2. A person reads it and records the chosen points and geographic decisions in the construction record. The automatic constructor reads those choices directly; it does not download or retrace the figure. Preserve source-location and calibration details with the source and construction records as appropriate.

The final boundary is generated directly from the chosen points. Intermediate traces and smoothed boundaries are not required inputs or separately saved outputs. To edit the construction, edit its record and rerun the same ID.

## Run

Use the shared [project environment](../../../../environment.yml). Set `NEON_DATABASE_URL` to the working database, then run from the repository root:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID
```

The shared entry point reads `method: geodesic_trace` and selects this constructor. For example:

```bash
worldatlas-import \
  --recipe lydekker-boundary-construction
```

The command saves the geometry and its construction ID. The figure identifier stays in the construction arguments. Source links connect the construction to its raw files. Regional assignment rules reference the saved feature separately.

## Tests

`test_geodesic.py` checks geodesic paths, control-point preservation, spacing and invalid geometry. `test_build_boundary.py` checks stored constructions, source references, repeat runs and failed writes.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner provisions a disposable PostgreSQL database and includes database writes, repeat runs, edits and rollback checks.

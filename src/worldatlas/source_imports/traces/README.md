# Boundaries traced from source figures

Build one final boundary from reviewed control points stored in Neon. The points
already include the intended path through gaps and around islands. There is no
separate correction or adjustment stage.

- [`curve.py`](curve.py) interpolates longitude by latitude, smooths the curve,
  and preserves its endpoints.
- [`build_boundary.py`](build_boundary.py) reads a construction record and its
  raw-source catalog entry, then writes the final geometry to Neon.

## Construction record

Use the existing `atlas.construction_records` table. Its `source_id` identifies
the construction record and `version` selects its version. The following fields
are JSON keys inside its `document` column, not separate table columns. The
`source_id` inside that JSON identifies the raw source figure.

| Field | Meaning |
| --- | --- |
| `method` | `smooth_latitude_trace` |
| `source_id`, `source_version` | The original source in Neon's raw-source catalog |
| `line_id` | The final record in `atlas.geographic_line_observations` |
| `basis` | How the figure was interpreted, including inferred connections and extensions |
| `points` | Selected `[longitude, latitude]` points, ordered north to south |
| `step_latitude_degrees` | Maximum latitude spacing between generated coordinates |
| `smoothing_latitude_degrees` | Width of the Gaussian smoothing filter |

This method requires latitude to decrease along the line. Use another
construction method for a boundary that doubles back northward.
The generated line must retain valid longitudes without crossing the
antimeridian. Invalid smoothing or sampling results stop before saving.

The original source figure stays in R2. A person reads it and records the chosen
points and geographic decisions in the construction record. The automatic
constructor reads those choices directly; it does not download or retrace the
figure. Preserve source-location and calibration details with the source and
construction records as appropriate.

The final boundary is generated directly from the chosen points. Intermediate
traces and smoothed boundaries are not required inputs or separately saved
outputs. To edit the construction, insert a new version of its record and run
that version.

## Run

Use Python 3.11 or later with NumPy, SciPy, and psycopg. Set
`NEON_DATABASE_URL` to the working database, then run from the repository root:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID VERSION
```

The shared entry point reads `method: smooth_latitude_trace` and selects this
constructor. For example:

```bash
worldatlas-import \
  --recipe lydekker-boundary-construction 1
```

The command saves the geometry, checksum, raw-source reference, and construction
record ID/version together. Existing notes and links from other Neon records
are retained. `--expected-geometry-sha256 SHA256` optionally checks the generated
geometry before saving.

## Tests

`test_curve.py` checks interpolation, smoothing, endpoint preservation and
invalid geometry. `test_build_boundary.py` checks stored constructions, source
references, repeat runs and failed writes.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

Set `WORLDATLAS_TEST_DATABASE_URL` to a disposable local PostgreSQL database with
the [initial schema](../../../../database/schema.sql) to
include database writes, repeat runs, edits, and rollback checks.

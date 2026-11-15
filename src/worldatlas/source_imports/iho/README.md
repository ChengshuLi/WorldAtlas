# IHO S-130 geometry

Import complete named areas and selected ocean divider lines from the cataloged
S-130 archive into `atlas.source_features`. Map building reads the imported
geometry; it does not interpret S-130 files or interpolate source routes.

## Code

- `areas.py` imports complete surfaces and collections by provider MRN. It preserves
  holes, dateline crossings and polar caps; linked parts sharing an MRN are combined.
- `s130.py` reads selected construction lines and samples their declared spherical
  rhumb interpolation, preserving every provider vertex and the chosen direction.
- `build_routes.py` provides the typed line constructor and common transactional storage.
- `../features/build_features.py` provides the typed `s130_areas` constructor.

## Construction records

An `s130_areas` document supplies `source_id`, `basis`, `gml_member`, `gml_sha256`
and `selections`. Each selection contains the output `feature_id` and provider
MRN in `source_feature_id`.

An ocean-line construction uses this format:

```json
{
  "method": "s130_rhumb_routes",
  "source_id": "RAW_SOURCE_ID",
  "gml_member": "path/inside/archive.gml",
  "gml_sha256": "GML_FILE_SHA256",
  "max_step_km": 0.05,
  "basis": "How the selected source lines define the dividers.",
  "routes": [
    {"feature_id": "OUTPUT_FEATURE_ID", "construction_line_id": "SOURCE_LINE_ID", "reverse": false}
  ]
}
```

`reverse` chooses the source line's direction. `max_step_km` controls import
sampling and must be greater than zero and at most 1. Source vertex coordinates
are retained without rounding or smoothing.

## Assignment is separate

`geographic_partitions` references imported divider features, their two entity
IDs and the `ocean_barrier` method. A meridian can request extension to the current
grid's southern edge when its source endpoint lies in the final grid row.
That grid-dependent operation belongs to map building, not the source importer.

`ocean_seeds` gives each ocean an interior witness and its imported source area.
Map building verifies that the witness is strictly inside the selected polygon.
Ocean polygons are not automatically selected as nearest-continent named basins;
that selection is recorded separately in `decision_basins`.

## Run and test

Use the [project environment](../../../../environment.yml), `NEON_DATABASE_URL`
and the R2 credential profile supplied outside the code:

```bash
worldatlas-import --recipe CONSTRUCTION_ID \
  --r2-endpoint R2_ENDPOINT --work-dir /absolute/path/to/worldatlas-work/inputs
```

The source catalog supplies the exact R2 file, size and checksum. Verified cached
files are reused. Geometry and construction references are saved atomically;
failed imports preserve existing records and relationships.

`test_areas.py` covers complete collections and geographic geometry.
`test_s130.py` covers line identity, source vertices and interpolation settings.
`test_build_routes.py` covers cached imports, repeat runs and atomic rollback.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

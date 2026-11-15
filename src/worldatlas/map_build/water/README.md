# Water assignment

`build.py` reads a saved geographic selection and verified physical/final-land
grids. It calls Python functions directly in this order:

1. Build one complete physical shoreline index, labeled by the current land entities.
2. Assign the coastal band by WGS84 distance to coastal land-cell centers.
3. Discover each selected basin's participants from its adjacent physical shores,
   then assign its remaining water by nearest participating shore.
4. Fill the ocean partitions and remaining enclosed water, then compose the grid.

The coastal distance, tie priority, basin selection, ocean barriers and seeds come
from the saved selection. Provider-specific source extraction belongs in source
imports. Basin participants and shoreline counts are calculated for each build.

Explicit ocean dividers use the same `atlas.geographic_partitions` table as land
dividers, with `method: ocean_barrier` and two ocean entity IDs. Their complete
lines are imported into `atlas.source_features`; map building only turns those
lines into blocked grid edges. `atlas.ocean_seeds` supplies each ocean's imported
area and an interior witness. Coast-to-ocean ownership is calculated from the
coastal band and named basins, so it needs no additional stored boundary line.

```bash
python3 -m worldatlas.map_build.water.build \
  --selection /absolute/path/to/input-selection.json \
  --physical /absolute/path/to/physical-grid \
  --land /absolute/path/to/final-land-grid \
  --output /absolute/path/to/new-water-output
```

Each input grid contains `rows.u32le` and `runs.u32le`. The physical report supplies
the grid dimensions and alignment. Output includes individual assignment layers,
basin participants, the complete final grid, counts and processing times. Download
time is zero because this calculation uses imported geometry and local grids.
The output directory must be new; the main pipeline manages checkpoint reuse.

`coastal.py`, `basins.py` and `remaining.py` implement the stages;
`composition.py` enforces precedence, physical-mask preservation and full final
coverage. The nearest-shore modules provide conservative distance bounds and
exact WGS84 refinement. A bound certifies an assignment only when omitted shores
cannot change the result. The complete shared index removes crop omissions.

Tests use independent exhaustive distances, arbitrary category codes, changed
land labels, wrapping, holes, conflicts and a complete small water build.
Independent shoreline and enclosed-water references live under `tests/`; they
are not runtime alternatives. Run with:

```bash
python .github/scripts/run_tests.py --suite map_build
```

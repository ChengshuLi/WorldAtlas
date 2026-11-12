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

```bash
PYTHONPATH=scripts/map-build python -m map_build.water.build \
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
land labels, wrapping, holes, conflicts and a complete small water build. Run with:

```bash
PYTHONPATH=scripts/map-build python -m unittest discover \
  -s scripts/map-build/map_build -t scripts/map-build
```

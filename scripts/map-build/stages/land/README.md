# V8 mainland stages

The [V8 runner](../../pipeline/README.md) connects the mainland stages using
the physical grid it just built.

- `fresh-components-20261104/` labels connected land cells.
- `stage2-geodesic-20261104/` resolves mainland witnesses, builds the selected
  regions, and assigns land cells using WGS84 geodesic distance.
- `mainland-source-verification-20261104/` contains the water closure checks
  used when joining boundary lines into regions.
- `neon-mainland-regions-20261104/rasterizer/` rasterizes the selected mainland
  regions onto the physical grid.

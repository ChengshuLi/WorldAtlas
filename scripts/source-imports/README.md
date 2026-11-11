# Source imports

These tools read raw geographic sources and save the selected geometry and
construction decisions in Neon. Raw source files stay in R2; Neon's source
catalog identifies their versions and checksums.

- [`osm/`](osm/README.md): join archived OpenStreetMap ways into a boundary.
- [`iho/`](iho/README.md): import selected IHO S-130 ocean boundary routes.
- [`traces/`](traces/README.md): construct final boundaries from reviewed points
  traced from source figures.
- [`watersheds/`](watersheds/README.md): construct boundaries from elevation,
  natural waterways and source basin geometry.
- [`source_io.py`](source_io.py): shared Neon recipe/catalog reads and verified
  R2 downloads.

Geographic selections belong in Neon construction records. Reusable parsing and
construction code belongs here. The [map builder](../map-build/pipeline/README.md)
uses the selected structured records, together with large raw raster/vector
inputs, to produce map cells.

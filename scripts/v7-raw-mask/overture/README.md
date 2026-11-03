# Candidate Overture water rasterizer

This experimental tool rasterizes one pinned Overture GeoParquet water shard into a sparse one-bit GeoTIFF. It is a research candidate, not a recovered historical builder, a complete water mask, or a V2 release.

It requires Python 3, NumPy, PyArrow with Parquet support, and GDAL/OGR Python bindings with GEOS, a GeoTIFF driver, and a memory vector driver. The trial used Python 3.13.5, PyArrow 26.0.1, GDAL 3.10.3, and GEOS 3.13.1. Parquet pre-buffering is disabled and GDAL's cache is limited to 64 MiB. The tool processes features in batches and rasterizes tiles, but unusually complex input may require additional memory. The example grid is large; provision disk and memory accordingly.

Copy `config.example.json` and explicitly review the grid and policy. The example's Overture subtype and provenance predicate is provisional: it has not been established as the historical source predicate. It uses selected polygon/multipolygon OSM-derived features and excludes ocean/physical subtypes and ocean/sea classes. It performs no other tag exclusions. Invalid polygons are not repaired; IDs are recorded and the result is marked incomplete. A missing subtype also marks it incomplete. GDAL default polygon rasterization is used with `ALL_TOUCHED` off; exact historic boundary behavior is unproven.

Run `python rasterize_water_shard.py SOURCE.parquet SOURCE_SHA256 CONFIG.json NEW_OUTPUT_DIRECTORY`. The output directory must not exist, contain an input, or be located within either input's directory. The tool hashes the source before and after, detects changes to configuration, and creates outputs exclusively. Interruptions may leave partial files, without a completion report. Keep those outputs until their disposal is authorized. A successful result is still only a candidate; independent geographic and reference comparisons are required before use.

Run the synthetic tests with `python -m unittest -v test_rasterize_water_shard.py`. They cover policy selection, batching and tile boundaries, input integrity, output separation and collision, and invalid-geometry reporting. Synthetic tests do not prove equivalence on a global dataset.

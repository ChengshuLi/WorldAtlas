# Research terrain screening

This generic research tool samples a line and terrain cross-sections from locally supplied DSM and mask rasters. It does not change a boundary, establish downstream flow, or certify a watershed. The user supplies the geographic data; none is stored in this directory. Only mask-0 pixels with non-NoData elevation enter summaries. Confirm mask semantics against the actual source and use a suitable local projected CRS.

Requirements: Python 3 with GDAL/OSR and NumPy. Run tests with `/usr/bin/python3 -m unittest discover -s scripts/caucasus-audit`.

Input `--samples` is GeoJSON Point features with `section`, `source_edge_index` (zero-based index into line coordinates), and `distance_along_section_m`; input `--line` is a GeoJSON LineString geometry. Repeat `--tile` using `NddEddd:/path/to/DSM.tiff:/path/to/MSK.tiff`. Specify `--section`, `--epsg` (a locally suitable metric CRS), and `--output` in a separate local research directory. Output contains input-derived geographic coordinates and should be handled as research data, not committed to the source repository.

The nearest-neighbor, 1-arcsecond DSM samples are indicators only. The source can contain vegetation, buildings, clouds, ancillary data and negative-elevation conversion artifacts. Check source quality, compare resolutions, consider watershed routing and uncertainty, and obtain review before accepting any change.

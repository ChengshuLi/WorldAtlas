# Direct-region mainland seed builder

Research only. This classifies all cells in explicitly selected physical components using caller-supplied closed continent regions and produces a zero/17–22 seed. It does not infer cuts, close lines, select geography, resolve islands, read a historical assignment map, prove provenance or represent approval. A separate stage is needed for all other land and water.

Run `/usr/bin/python3 build_seed.py CONFIG NEW_OUTPUT_DIR`. Requires Python GDAL/OGR, g++, NumPy for tests, and GDAL/GEOS supporting valid polygons. All paths are explicit. Output is exclusive and its directory tree must be separate from all input and program directories; it must not already exist; failed runs may leave partial output but do not produce a success report.

The JSON object has exact keys:

- `schema`: `direct-region-seed-research-v1`.
- `grid`: `width`, `height`, `west`, `north`, `step`, and `crs: "EPSG:4326"`, with cell sizes `step` and `-step`; every polygon layer must declare WGS84. No reprojection is performed. The intended geographic grid uses longitude/latitude degrees. Width/height must be positive integers, step positive, and all affine values finite.
- `component_rows`, `component_runs`: `{path,sha256}` pins to little-endian uint32 row offsets and `(start,exclusive_end,component_id)` triples, respectively. Each row's intervals must be sorted, non-overlapping and in bounds.
- `regions`: zero to eight unique `{id,geometry,witnesses}` items. `geometry` is a `{path,sha256}` pin to a vector file with exactly one layer, one valid polygon or multipolygon feature. Its geometry must include all chosen closures; this program does not create them. `witnesses` is a list of `{lon,lat,inside}` point tests in the same CRS. Points on the boundary fail.
- `rules`: nonempty, unique `{component_id,region_id,inside_code,outside_code}` items, with codes 17–22. A `null` region means a whole-component rule and requires equal codes. For a named region, each selected component cell gets `inside_code` if its center rasterizes in that region, otherwise `outside_code`. Each selected ID must occur in the component stream.
- `evidence`: list of `{path,sha256}` pins for optional source lines or connector files, for provenance records. Pinning these does not verify that they generated or match a supplied polygon. Never include historical label grids as build inputs.
- `strip_rows`: integer 1–1024.
- `reserve_bytes`: optional nonnegative integer, default 2 GiB. Free space on the output filesystem is checked before creating the output and before each strip; test fixtures may set zero. A reserve is not a forecast of total output size.

The builder requires a little-endian host and checks all pins before and after, verifies the config and program files did not change, and creates a research report only on success. Output `rows.u32le` contains uint32 row offsets into `runs.u32le`, whose `(exclusive_end,code)` pairs cover each whole row; code zero is not part of the mainland seed. Region masks use GDAL's center-rasterization behavior, including its exact-boundary tie convention, which is not established as V2's. Overlapping polygons are encoded as independent bits, so region order does not determine membership. Output hash, input pins and GDAL version are recorded. This tool does not authenticate sources, test geographic appropriateness or prove the water-side closure is correct.

Run `/usr/bin/python3 -m unittest -v test_build_seed`. Synthetic tests cover direct region splits, overlapping masks, zero gaps, input pin rejection, duplicate or missing components, witness failure and existing output. A separate real-data cross-check matched 128 full-width seed rows from the earlier independent direct implementation; the generalized builder has not yet been run worldwide due to the disk reserve.

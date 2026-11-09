# Candidate Overture water rasterizer

The rasterizer converts one pinned Overture GeoParquet water shard into a sparse one-bit GeoTIFF. The union stage combines all selected shards.

It requires Python 3, NumPy, PyArrow with Parquet support, and GDAL/OGR Python bindings with GEOS, a GeoTIFF driver, and a memory vector driver. The trial used Python 3.13.5, PyArrow 26.0.1, GDAL 3.10.3, and GEOS 3.13.1. Parquet pre-buffering is disabled; GDAL uses its default cache behavior, with no application-imposed memory cap. The tool processes features in batches and rasterizes tiles, but unusually complex input may require additional memory. The example grid is large; provision disk and memory accordingly.

The default `gdal` rasterizer uses NumPy, Arrow and the supported GDAL/OGR Python
bindings. It needs no ctypes bridge, custom C++ helper, compiler, executable or
subprocess. It performs the same OGR parsing, geometry-type and GEOS-validity checks. Only exact
finite standard 2D Point WKB is classified without OGR as a non-polygon.

The default `batch_method: "hybrid"` groups features into tile burns, prunes only original vertex
runs strictly outside each tile-row strip, and skips empty multipart envelope
gaps. NumPy indexes ring coordinates once per batch. Retained edges keep their
original double coordinates; outside-strip bridges cannot intersect a visible
scanline. Every GDAL burn retains the reference tile-local transform, including
center ties. `Layer.WriteArrow` populates each tile layer in a batch rather than
building a Python Feature per polygon. `gdal_array.OpenArray` shares the live
NumPy tile, avoiding initialization and result copies. The `tiled` method retains the unpruned reference raster path;
global vector mode is rejected because it changes rare pixel-center ties.

Reports pin the Python binding and GDAL identity; physical checkpoints verify
those pins. Old `rasterizer: "native"` configurations fail explicitly rather than
compile or silently change engines. Set `rasterizer: "python"`, or use
`--engine python`, for the retained feature-layer reference implementation.

Copy `config.example.json` and explicitly review the grid and policy. The `water-shard-candidate-v2` configuration uses Overture's inland-water classification: all nonempty subtypes except `ocean` and `physical` are eligible. It burns only polygon/multipolygon geometry and applies no source-provenance, class, or OSM-tag filter. This follows the [Overture water schema](https://docs.overturemaps.org/schema/reference/base/water/). Invalid polygons are not repaired; IDs are recorded and the result is marked incomplete. A missing subtype also marks it incomplete. GDAL default polygon rasterization is used with `ALL_TOUCHED` off; exact historic boundary behavior is unproven.

Run `python rasterize_water_shard.py SOURCE.parquet SOURCE_SHA256 CONFIG.json NEW_OUTPUT_DIRECTORY`. The output directory must not exist, contain an input, or be located within either input's directory. The tool hashes the source before and after, detects changes to configuration, and creates outputs exclusively. Interruptions may leave partial files, without a completion report. Keep those outputs until their disposal is authorized. A successful result is still only a candidate; independent geographic and reference comparisons are required before use.

## Union and comparison

`aggregate_compare.py CONFIG.json NEW_OUTPUT_DIRECTORY` unions a complete, explicitly listed set of hash-pinned candidate masks and can optionally compare every grid cell with a separate hash-pinned binary reference. Copy `aggregate-config.example.json`, replace all placeholders, pin the complete raw-source manifest, and list every shard with its output and report digests and `candidate-only` status. The declared shard count must match the list; incomplete masks are rejected. The config itself and every input mask are verified before and after processing. Inputs and output must be separated as above, and the output directory must be new. The configured minimum free-space reserve is checked before each block; `rows_per_block` defaults to 128, while the current full-source profile uses 512 rows aligned to the GeoTIFF tiles. Interrupted or failed runs may leave partial files without a report.

The union skips unallocated GeoTIFF byte blocks only when GDAL reports them empty and their implicit value is zero; other inputs are read normally, and allocated blocks are checked for nonbinary values. On one 32-shard full-grid trial, this union took 20.6 seconds compared with 522.9 seconds in an earlier profile, with every union pixel equal. Timing and cache conditions were not controlled, and the two TIFF byte hashes differed. This is not an end-to-end timing guarantee.

The report records the union hash and, when a reference is supplied, both water cell counts and all mismatch spans. Exact grid agreement is not proof of historic source selection, code identity, or geographic correctness. The aggregation tests run with `python -m unittest -v test_aggregate_compare.py` and cover full-cell differences, input changes, incomplete inputs, output isolation, and nonbinary masks.

# Candidate Overture water rasterizer

This experimental tool rasterizes one pinned Overture GeoParquet water shard into a sparse one-bit GeoTIFF. It is a research candidate, not a recovered historical builder, a complete water mask, or a V2 release.

It requires Python 3, NumPy, PyArrow with Parquet support, and GDAL/OGR Python bindings with GEOS, a GeoTIFF driver, and a memory vector driver. The trial used Python 3.13.5, PyArrow 26.0.1, GDAL 3.10.3, and GEOS 3.13.1. Parquet pre-buffering is disabled; GDAL uses its default cache behavior, with no application-imposed memory cap. The tool processes features in batches and rasterizes tiles, but unusually complex input may require additional memory. The example grid is large; provision disk and memory accordingly.

The default `native` rasterizer additionally requires a C++17 compiler and a
Linux GDAL shared library. It builds the checked-in `water_native.cpp` into the
new shard output, using that output for compiler temporary files. GDAL development
headers are not required. The helper reads Arrow's existing WKB buffers, performs
the same OGR parsing, geometry-type and GEOS-validity checks using independent
geometries across the process's available CPUs. The default `native_method:
"hybrid"` groups small features into shared tile burns, uses GDAL's native vector
path for broad single-part polygons, and skips empty multipart bounding-box gaps.
It retains complete original geometries, coordinates and GDAL fill rules. The
`tiled` and `vector` methods remain available for controlled comparisons. This
avoids repeated broad-polygon vertex traversal as well as Python dictionaries,
WKB copies and per-tile OGR feature clones. The report records method, validation
threads, helper/binding, binary, compiler and GDAL identity. Union, checkpoint and physical-lineage checks
verify those pins. Set `rasterizer: "python"` in the pinned config, or use
`--engine python` for a direct run, to use the retained reference implementation.

Copy `config.example.json` and explicitly review the grid and policy. The `water-shard-candidate-v2` configuration uses Overture's inland-water classification: all nonempty subtypes except `ocean` and `physical` are eligible. It burns only polygon/multipolygon geometry and applies no source-provenance, class, or OSM-tag filter. This follows the [Overture water schema](https://docs.overturemaps.org/schema/reference/base/water/), but the historical V2 predicate is not known. Invalid polygons are not repaired; IDs are recorded and the result is marked incomplete. A missing subtype also marks it incomplete. GDAL default polygon rasterization is used with `ALL_TOUCHED` off; exact historic boundary behavior is unproven.

Run `python rasterize_water_shard.py SOURCE.parquet SOURCE_SHA256 CONFIG.json NEW_OUTPUT_DIRECTORY`. The output directory must not exist, contain an input, or be located within either input's directory. The tool hashes the source before and after, detects changes to configuration, and creates outputs exclusively. Interruptions may leave partial files, without a completion report. Keep those outputs until their disposal is authorized. A successful result is still only a candidate; independent geographic and reference comparisons are required before use.

Run the synthetic tests with `python -m unittest -v test_rasterize_water_shard.py`. They cover policy selection, batching and tile boundaries, input integrity, output separation and collision, and invalid-geometry reporting. Synthetic tests do not prove equivalence on a global dataset.

`benchmark_water_shard.py SOURCE SHA256 CONFIG NEW_OUTPUT --repeats 2` times
complete reference/native shard runs in alternating order and checks feature
counts and every mask pixel. `--reference PRIOR_SHARD_OUTPUT` additionally checks
the prior producer's mask. Source hashing and native compilation are included;
source acquisition is outside this benchmark. Retain the source and benchmark
report. A selected-shard result is not a complete 32-shard throughput result.
Use `--discard-matching-outputs` to remove only new byte-identical mask copies
after verification. `--discard-owned-source` additionally removes a regenerable
raw copy downloaded specifically for this benchmark, after every check succeeds.
Do not use that option for an existing input shared with another task. Reports,
hashes, native binaries and cleanup receipts remain available.

### Complete-shard timing, 2026-11-07

Two serial, alternating-order trials processed the entire official shard 6
(1,196,853,535 bytes, 2,093,933 rows), the slowest shard in the preceding sealed
32-shard run. Python reference versus native hybrid times were 115.44 → 48.76
seconds and 126.72 → 37.79 seconds: 2.37–3.35× faster. Every feature count,
every mask pixel and the TIFF byte hash matched both the fresh reference and
the sealed producer. The native raster plan removes broad-polygon retraversal
and empty multipart tiles; it also validates independent geometries across the
nine available CPUs.

Timings include source hashing, native compilation and processing, but exclude
download and post-run comparison. Host/cache effects remain possible despite
exclusive internal benchmark windows and reversed order. This measures one
complete source shard, not a new full 32-shard or end-to-end physical run. See the
[pinned receipt](../../../docs/benchmarks/physical-native-20261107.json) for source,
code, runtime, timings and verification details. The owned download and matching
generated TIFF copies were removed after verification; their digests and reports
remain in the receipt.

## Union and comparison

`aggregate_compare.py CONFIG.json NEW_OUTPUT_DIRECTORY` unions a complete, explicitly listed set of hash-pinned candidate masks and can optionally compare every grid cell with a separate hash-pinned binary reference. Copy `aggregate-config.example.json`, replace all placeholders, pin the complete raw-source manifest, and list every shard with its output and report digests and `candidate-only` status. The declared shard count must match the list; incomplete masks are rejected. The config itself and every input mask are verified before and after processing. Inputs and output must be separated as above, and the output directory must be new. The configured minimum free-space reserve is checked before each block; `rows_per_block` defaults to 128, while the current full-source profile uses 512 rows aligned to the GeoTIFF tiles. Interrupted or failed runs may leave partial files without a report.

The union skips unallocated GeoTIFF byte blocks only when GDAL reports them empty and their implicit value is zero; other inputs are read normally, and allocated blocks are checked for nonbinary values. On one 32-shard full-grid trial, this union took 20.6 seconds compared with 522.9 seconds in an earlier profile, with every union pixel equal. Timing and cache conditions were not controlled, and the two TIFF byte hashes differed. This is not an end-to-end timing guarantee.

The report records the union hash and, when a reference is supplied, both water cell counts and all mismatch spans. Exact grid agreement is not proof of historic source selection, code identity, or geographic correctness. The aggregation tests run with `python -m unittest -v test_aggregate_compare.py` and cover full-cell differences, input changes, incomplete inputs, output isolation, and nonbinary masks.

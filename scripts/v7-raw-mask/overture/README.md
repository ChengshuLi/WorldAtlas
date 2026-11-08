# Candidate Overture water rasterizer

This experimental tool rasterizes one pinned Overture GeoParquet water shard into a sparse one-bit GeoTIFF. It is a research candidate, not a recovered historical builder, a complete water mask, or a V2 release.

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

Copy `config.example.json` and explicitly review the grid and policy. The `water-shard-candidate-v2` configuration uses Overture's inland-water classification: all nonempty subtypes except `ocean` and `physical` are eligible. It burns only polygon/multipolygon geometry and applies no source-provenance, class, or OSM-tag filter. This follows the [Overture water schema](https://docs.overturemaps.org/schema/reference/base/water/), but the historical V2 predicate is not known. Invalid polygons are not repaired; IDs are recorded and the result is marked incomplete. A missing subtype also marks it incomplete. GDAL default polygon rasterization is used with `ALL_TOUCHED` off; exact historic boundary behavior is unproven.

Run `python rasterize_water_shard.py SOURCE.parquet SOURCE_SHA256 CONFIG.json NEW_OUTPUT_DIRECTORY`. The output directory must not exist, contain an input, or be located within either input's directory. The tool hashes the source before and after, detects changes to configuration, and creates outputs exclusively. Interruptions may leave partial files, without a completion report. Keep those outputs until their disposal is authorized. A successful result is still only a candidate; independent geographic and reference comparisons are required before use.

`benchmark_selected_water.py SELECTED_PIPELINE_CONFIG NEW_OUTPUT` reads the
inline water configuration and complete raw manifest from the supported pipeline
selection, then compares every raw shard through both Python implementations in
one process. It verifies every pixel and diagnostic count. Missing raw inputs
use the selected serial R2 S3 staging; downloads are timed separately. Completed
owned downloads are removed after verification, while original local inputs and
failed downloads remain untouched. Use `--shard 6` for a clearly labeled single
complete-shard trial, `--repeats 2` for alternating repeat order, or
`--keep-downloaded-sources` to retain newly acquired raw copies. These controls
do not weaken source pins or imply geographic acceptance.
If interrupted, use the identical command with `--resume`. Completed paired
reports and masks are reverified before reuse; incomplete outputs and partial
downloads are preserved under `interrupted`. Producer UTC intervals and attempt
records distinguish separate measurement windows. Summed production durations
are not an uninterrupted end-to-end pipeline timing.

Run the synthetic tests with `python -m unittest -v test_rasterize_water_shard.py`. They cover policy selection, batching and tile boundaries, input integrity, output separation and collision, and invalid-geometry reporting. Synthetic tests do not prove equivalence on a global dataset.

`benchmark_water_shard.py SOURCE SHA256 CONFIG NEW_OUTPUT --repeats 2` times
complete reference/GDAL Python API shard runs in alternating order and checks feature
counts and every mask pixel. `--reference PRIOR_SHARD_OUTPUT` additionally checks
the prior producer's mask. Source hashing is included; source acquisition is
outside this benchmark. Retain the source and benchmark
report. A selected-shard result is not a complete 32-shard throughput result.
Use `--discard-matching-outputs` to remove only new byte-identical mask copies
after verification. `--discard-owned-source` additionally removes a regenerable
raw copy downloaded specifically for this benchmark, after every check succeeds.
Do not use that option for an existing input shared with another task. Reports,
hashes and cleanup receipts remain available.

`profile_water_shard.py SOURCE SHA256 CONFIG PINNED_REFERENCE NEW_OUTPUT` uses
standard Python cProfile on one complete GDAL-API run, then checks every count
and mask pixel against the pinned reference. It retains per-function calls,
self/cumulative time, producer logs and raw pstats data. Instrumentation adds
overhead; this attributes repeated work, not a speed comparison. Run it outside
the exclusive uninstrumented timing window. Cumulative times overlap and must
not be summed. See the [baseline audit](../../../docs/benchmarks/physical-baseline-audit-20261108.json)
before comparing retained receipts from different implementations or scopes.

### Historical development timing, superseded by the center-tie correction

The global-vector implementation below was subsequently found to change two
physical cells in a complete 32-shard run. It is no longer used. Its selected
shard measurements remain historical evidence, not a correctness claim or timing
for the corrected implementation. The [correction receipt](../../../docs/benchmarks/physical-center-ties-20261107.json)
records the exact incident, extracted-feature reproductions and complete fixed
shard comparisons. Both offending full shards now match every original pixel;
their corrected native producer times were 21.55 and 45.37 seconds. Those are
native-only checks, not fresh paired or end-to-end timings.

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

`reproduce_water_cell.py SOURCE SHA CONFIG ROW COLUMN NEW_OUTPUT` verifies a raw
source, extracts nearby features using its bbox column with one-cell padding,
and replays the Python feature-layer reference, GDAL hybrid and GDAL tiled paths. It retains source-row
indices, feature IDs, extracted data, pinned reports and each cell value. This is
a diagnostic subset, not a complete source or geographic verification.

## Union and comparison

`aggregate_compare.py CONFIG.json NEW_OUTPUT_DIRECTORY` unions a complete, explicitly listed set of hash-pinned candidate masks and can optionally compare every grid cell with a separate hash-pinned binary reference. Copy `aggregate-config.example.json`, replace all placeholders, pin the complete raw-source manifest, and list every shard with its output and report digests and `candidate-only` status. The declared shard count must match the list; incomplete masks are rejected. The config itself and every input mask are verified before and after processing. Inputs and output must be separated as above, and the output directory must be new. The configured minimum free-space reserve is checked before each block; `rows_per_block` defaults to 128, while the current full-source profile uses 512 rows aligned to the GeoTIFF tiles. Interrupted or failed runs may leave partial files without a report.

The union skips unallocated GeoTIFF byte blocks only when GDAL reports them empty and their implicit value is zero; other inputs are read normally, and allocated blocks are checked for nonbinary values. On one 32-shard full-grid trial, this union took 20.6 seconds compared with 522.9 seconds in an earlier profile, with every union pixel equal. Timing and cache conditions were not controlled, and the two TIFF byte hashes differed. This is not an end-to-end timing guarantee.

The report records the union hash and, when a reference is supplied, both water cell counts and all mismatch spans. Exact grid agreement is not proof of historic source selection, code identity, or geographic correctness. The aggregation tests run with `python -m unittest -v test_aggregate_compare.py` and cover full-cell differences, input changes, incomplete inputs, output isolation, and nonbinary masks.

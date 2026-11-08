# Fresh complete pipeline measurement, 2026-11-07

The supported raw-source-to-final-grid pipeline completed in one uninterrupted
invocation using producer commit `88483e3021a6c12d148bbd7f673b4ff553c045f6`.
It rebuilt every processing stage from the pinned input selection. No earlier
physical, component, land, basin, coast, ocean or final-grid outputs were reused.
The separately selected reference grid was used only for regression verification.

**All 7,158,366,208 cells match published V8.** The final row and run streams
are byte-identical. The result remains provisional and non-publishable; equality
is a reproduction check, not independent geographic approval.

## Stage inputs, outputs and observed processing wall time

Both columns exclude measured source downloads and gaps between interrupted
attempts. The new run has exactly one attempt and no interrupted intervals.
The previous completed run includes active recovery and repeated validation.
These are actual run observations, not a controlled causal speedup experiment;
unchanged physical and mainland stages were slower in this invocation.

| Stage | Work and inputs | Output | Previous observed run, seconds | Fresh optimized run, seconds |
| --- | --- | --- | ---: | ---: |
| Setup | Validate pinned selected source files, configurations and runtime | Source/runtime/code identity | 245.913 | 8.843 |
| Physical | Rasterize full raw OSM land polygons and all 32 official Overture water shards; subtract water | Global dry-land/water TIFF and compressed row/run streams | 1720.061 | 2120.099 |
| Mainland/islands | Build connected components; apply mainland seeds, exact WGS84 assignments and selected regional/island rules | Continent labels for all dry-land cells and lineage reports | 1958.458 | 2261.217 |
| Water/final assembly | Use fresh physical/land streams, SeaVoX archive and basin/coastal/ocean policies; build all basins/coast, prefill, oceans, enclosed water and final grid including selected Iceland revision | Complete continent-labeled grid and producer reports | 9843.559 | 3416.312 |
| Verification | Recheck source/code/output pins and compare generated final streams with V8 | Full-grid comparison and sealed final report | 13.283 | 12.772 |
| Total | Sequential parent-stage processing intervals | Complete measured run | 13781.274 | 7819.242 |

The fresh total is **2h 10m 19.2s** of processing. A further **828.295s** of
measured raw-source download time is excluded. The physical producer processed
all 32 official Overture `2026-10-21.0` water shards, totaling 28,818,195,515
source bytes. Sources were downloaded one shard at a time, size/hash verified,
processed completely, then removed by the supported staging flow. Download and
other shard processing did not overlap.

Water runs two basin jobs alongside one coastal batch. Parent-stage interval
unions count their overlap once. Do not add individual command durations to
obtain water or end-to-end wall time.

## Selected current substeps

| Command | Fresh processing wall seconds |
| --- | ---: |
| Physical producer, excluding downloads | 2119.297 |
| Component construction | 32.764 |
| Stage 2 preparation and assignment | 1702.803 |
| Regional/island assignment | 514.801 |
| Complete 546-tile coastal batch | 952.623 |
| Bering Sea assignment | 97.693 |
| Prefill assembly | 223.468 |
| Baseline ocean assignment | 46.601 |
| Enclosed-water assignment | 192.582 |
| Baseline final composition | 37.460 |
| Updated ocean assignment | 34.798 |
| Split final composition | 19.593 |

All 92 basin coverage verifications and all 546 coastal tiles completed.
After the assignment improvements, repeated individual SeaVoX extraction calls
became the basin-pool critical path. The coast finished while that pool was
still running. This is a target for subsequent optimization, not work included
in this producer commit.

The controlled isolated optimization evidence is separate: Bering processing
5141.516s to 105.837s, and complete coast 1142.289s to 791.148s. The current
97.693s/952.623s values above are actual commands under pipeline concurrency.
See the existing [Bering benchmark](bering-rectangles-20261107.json)
and [coastal benchmark](coastal-shore-index-20261107.json).

## Reproduction and provenance

Use the checked-in entrypoint with the pinned selection and a new persistent
run directory, following `scripts/v7-pipeline/README.md`:

    /usr/bin/python3 scripts/v7-pipeline/run_pipeline.py \
      /workspace/selection/config.json /workspace/runs/fresh-run

The actual selection SHA-256 was
`9563b98fa163278f35c6b7c09538d2bedbb386561763d7d7d4c52ec3c41476d6`.
The run used Python 3.13.5, NumPy 2.2.4, SciPy 1.15.3, PyProj 3.7.1/PROJ 9.6.0,
GDAL 3.10.3 and PyArrow 26.0.1, with local projection networking disabled.
The clean checkout matched remote PR4 at launch and after completion. All 973
recorded script hashes matched that checkout; no untracked script or one-off
local coordinator was used. Run directories contain generated data, requests,
checkpoints and compiler outputs, not copied Python/C++ source executables.
Temporary artifacts stayed in the persistent run workspace. No application
memory limit or guardian was introduced. No publication or deployment occurred.

- [Machine-readable stage, 294-command and physical-unit times](optimized-full-pipeline-20261107.json)
- [Unmodified producer run report](optimized-full-pipeline-20261107-report.json)
- [Unmodified full-grid comparison](optimized-full-pipeline-20261107-comparison.json)

The copied report SHA-256 is
`1510eedfe81f034d55c3d9baba89034adddefabf9ed73c9709481487b311fb89`;
the copied comparison SHA-256 is
`f2a7319247cb05bb059e10b1bd5142a8210809bd239625531b4c43c7d14859ee`.
Their original run paths and hashes are preserved as provenance, not portable
input locations. The full timing ledger is pinned by the report's timing anchor.

# Direct research pipeline

The existing stage CLIs consume pinned raw sources and freshly produced physical,
land and water artifacts. They do not need a local coordinator or an old labeled
map. All outputs remain provisional, non-publishable research. Draft decisions,
unverified snapshots, and selected research policies require the corresponding
explicit CLI opt-ins. A hash proves byte identity, not geographic correctness or
approval.

## Stages and contracts

1. `../v7-raw-mask/build_physical.py` produces the physical mask, rows, runs and
   report from the official raw source manifest. Pin its output report and stream
   hashes. Input acquisition is separate from processing time.
2. The WGS84 Stage 2 entry is
   `../v7-recovery/land/stage2-geodesic-20261104/orchestrate_stage2.py`.
   The selected mixed/regional producer is
   `../v7-land/research-mixed-runtime/stage3-mixed-leeward-full-20261105/apply_selected_mixed.py`.
   Its report embeds `input_lineage`, binding its request, decision snapshot,
   physical inputs, baseline and code. Consumers validate those pins directly;
   no sidecar lineage repair or path relocation is supported. Rebuild requests
   and code pins after changing a producer. Diagnostic baselines remain explicitly
   provisional and must pass their normal freeze gate. The existing
   `prepare_fresh_handoff.py` accepts a hash-pinned template and validates the
   fresh Stage 2 report, derived manifest, outer request and code closure directly.
   It emits current input/code pins, without a recovery-evidence sidecar or
   an exact historical-template allowlist. Code dependencies use a fixed module
   inventory with each policy hash checked at its canonical repository path; no
   by-hash clone search or source-prefix relocation is performed. Regional and Stage 2 WGS84 modules
   keep distinct, pinned identities without replacing each other in memory.
3. `extract_seavox_feature.py` and `build_seavox_basin.py` produce each selected
   named basin. Shared basins also consume the fresh land streams. Use
   `--research-shore-method wgs84-coastal-4neighbor-center-v2` for WGS84
   ellipsoidal center-to-center assignment. `--research-interval` is an optional
   execution engine with the same exact fallback, not the default. Point,
   wrapped-point, interval and wrapped-interval manifests carry distinct methods,
   complete cell accounting and source-code pins. `verify_basin_coverage.py`
   checks emitted spans against the source raster and physical water.
4. `batch_coastal_tiles.py` uses the same canonical physical/land lineage checks
   as the other consumers and seals the grid generation for each batch. A plan
   accepts either uniform `pad_degrees` and core boxes or entries of the form
   `{core: [x0,x1,y0,y1], latitude_pad_degrees: ..., longitude_pad_degrees: ...}`.
   Independent halos avoid inflating latitude coverage near the poles. The
   current builder uses RLE shore extraction and 2-D rectangle certificates.
   `assemble_coastal_tiles.py` verifies the complete non-overlapping tessellation.
   Each batch publishes `batch-start.json` and a durable `tile-complete.json`
   after each closed tile. To continue after interruption, keep the previous
   batch and run the same command with a new `--out` and `--resume-from OLD_OUT`.
   Repeat `--resume-from` for earlier preserved attempts if a restart itself was
   interrupted. Input, snapshot, plan, driver and supporting code hashes must
   match; every copied manifest and assignment file is rehashed. Partial tiles
   without completion records are regenerated, and corrupt records fail closed.
   Historical batches without these producer-owned records are not adopted.
   Checkpoints use relative paths and survive preservation-directory renames.
   Timing carries recorded active intervals forward without restart downtime.
   After a hard interruption, the work since the last checkpoint is unknown:
   `timing_complete` is false, `processing_elapsed_seconds` is null, and
   `recorded_processing_elapsed_seconds` is the measured lower bound.
5. `build_prefill_plan.py` consumes a configuration with `rle_inputs.physical`,
   `rle_inputs.land`, `coastal_band` and the selected `basins`. Each stream and
   report has its path and SHA-256. It binds source selection, decision policy,
   explicit layer precedence and land lineage.
   `build_prefill.py` then produces the prefill streams and audit. Physical-water
   encoding comes from the validated producer contract: mixed land preserves
   unassigned water as 0; direct land uses 1. No report-hash allowlist is used.
6. `../v7-recovery/ocean/make_candidate_build.py` pins the physical build and
   selected ocean policy. `ocean_fill_runner.py` fills eligible residual water
   and reports its unseeded partition. `build_closed_water.py` consumes that
   partition and the prefill to assign enclosed water; unresolved components
   fail closed. `prepare_final_plan.py` binds completed ordinary ocean/closed
   outputs, validates their conservation and prepares the final plan.
   `compose_direct.py` checks disjoint full coverage and rejects overwrites,
   gaps and changed inputs before producing the final grid.
7. `compare_grids.py` validates every row and compares all cells against explicit
   reference rows/runs SHA-256 pins and dimensions. It reports exact changed-cell
   pair counts, byte identity and both stream/combined hashes. A semantic mismatch
   writes its comparison report and exits nonzero. Different valid RLE
   segmentations can still have identical cells. No reference hashes are compiled
   into the comparison code.

All plan paths are relative to their document or absolute inside `--input-root`.
Old workspace and `/tmp` prefixes are not remapped. Outputs must be new and must
not replace or contain inputs. Fresh output directories may be inside the run's
input root, so one run can keep its artifacts together without copying them.

## Separately pinned policy revisions

The pipeline binds the selected named-water and ocean exports to the
same run's mainland snapshot. The effective water snapshot records all
three source pins and validates the shared registry. The water stages
build named basins, coastal water, prefill, ocean and enclosed water
from that bound selection.

## Wall-clock timings

Stage reports expose `processing_elapsed_seconds`, measured with a monotonic
clock over the successful local processing invocation, including CLI preflight
and integrity checks. Prepare/download inputs
before these intervals; acquisition time is not processing time. A killed or
interrupted attempt does not create a completed timing report. Stage 2 explicitly
marks resumed checkpoints with prior work unmeasured; its successful invocation
is not the complete stage total. A fresh uninterrupted run is required for a
complete baseline when earlier intervals were not recorded.

A batch timing includes its sequential tiles and input sealing. Per-tile timings
are nested detail, not additional elapsed time. Never sum concurrent jobs as a
stage's wall-clock duration: use the union of their processing intervals, excluding
periods where no processing runs. Microbenchmarks and historical log gaps are not
full-run timings. Exact final-grid equality must be checked separately from speed.

## Focused checks

With NumPy, SciPy, PyProj and the GDAL system Python available, set `TMPDIR`, `TMP`
and `TEMP` to a persistent workspace directory, then run:

    PYTHONPATH=scripts:scripts/v7-replay:scripts/v7-recovery/ocean \
      /usr/bin/python3 -m unittest discover -q -s scripts/v7-replay -p 'test_*.py'

The retired `scripts/research-diagnostic-water` fork has been consolidated into
these normal stage contracts. Historical gzip comparison adapters, per-run report
allowlists and lineage sidecars are not part of the supported pipeline.

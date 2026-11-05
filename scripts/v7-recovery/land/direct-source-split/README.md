# Direct mainland cut research

This package is an unselected research candidate. It derives one selected source line, physical component and two land categories from a pinned decision snapshot and independently resolved component witness. The graph partitions only that component; it does not consume a prior label grid, construct the remaining seed, or run the downstream stage-two land assignment. It does not authenticate the exported snapshot or approve any geography.

The request is supplied at runtime, not stored in this repository. It includes a grid; SHA-256 pins and paths for the Neon-export snapshot, witness report, component rows and component runs; selected rule and boundary IDs; and resource limits. Those inputs must be staged from their authorized stores. The boundary source references must match original-asset R2 metadata in the snapshot; the report retains whether the recorded lineage is complete or incomplete. Metadata consistency alone does not verify R2 availability or prove complete source custody. The rule must reference exactly one complete selected source boundary. Region witnesses establish the two graph seeds and side orientation. Conflicting witnesses, line-through-center cases, endpoints too close to selected land, non-simple or wrapped lines, incomplete coverage, resource limits and ambiguous residual fragments fail closed. The nearest-segment residual rule is experimental and is not a generally proven partition.

Run the process-group monitor with a fresh output directory outside every input and code directory:

`/usr/bin/python3 watch_direct.py REQUEST OUTPUT MAXIMUM_PROCESS_GROUP_RSS_KIB`

The request's `max_rss_kib` must match the monitor argument. It also specifies `minimum_memory_kib`, `minimum_free_bytes`, `max_nodes`, `max_raster_work`, `max_residual_cells`, and `max_residual_segment_tests`. The program enforces a host-memory floor of at least 1,887,437 KiB and disk reserve of at least 2 GiB. The process-group cap cannot exceed 870,400 KiB; graph, rasterization and residual work also have hard upper bounds. The monitor checks the process group and writes a marker only after successful driver completion. Sampling can miss short-lived peaks; escaped children and simultaneous monitor/guardian failure are not contained. An incomplete output must be inspected, not reused.

The report is research-only. Before replacing any current pipeline step, independently verify exact coverage and equality, rebuild the entire downstream output, and benchmark the complete old and new paths under comparable resources. No result from this package alone authorizes a switch.

Run synthetic tests with `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 -m unittest -q test_direct_core test_watch_direct`.

`watch_compare.py REQUEST OUTPUT MAXIMUM_PROCESS_GROUP_RSS_KIB` runs an independent comparison of two complete, pinned full-width RLE grids. It checks every cell, tolerates different run segmentation, and reports equality or bounded mismatch examples without using either grid as an assignment input. The comparison request specifies the grid dimensions, four row/run input pins, and the same memory, disk and process-group limits. Equality is numerical only; it does not establish source provenance or approve a switch. Run its synthetic tests with `/usr/bin/python3 -m unittest -q test_compare_full`.

`compose.py` provides a row-level primitive for combining a direct split with a separately produced partial seed that already excludes the selected component. It takes the allowed category codes as input and rejects missing component coverage, invalid codes and overlap. It does not generate that partial seed or establish equivalence. Its synthetic tests use `/usr/bin/python3 -m unittest -q test_compose`.

# Pinned diagnostic water composition

This is a self-contained, research-only reproduction of the local provisional water prefill and final-composition path. It does not publish a map, alter Neon, upload raw sources, or establish geographic correctness or decision authority. Obtain raw source files from their preserved custody and decisions from their structured source; the caller must supply the pinned files and an explicitly labeled local diagnostic overlay.

The diagnostic land producer referenced here writes physical-water cells as code 0. The prefill accepts that encoding only for the specifically pinned, validated run7 report and its diagnostic lineage. Other direct-land inputs retain their existing contract. The Bering wrapped-shore result is accepted only with the pinned original comparison and independent raster-coverage evidence. Other wrapped basins need a separately reviewed evidence contract before this package can compose them.

Scripts require fresh outputs and explicit draft, unverified-snapshot, and research-shore opt-ins. Paths in an input plan must be relative to its directory or absolute under the supplied input root. No workspace-specific filesystem paths or input data are embedded. The source selection, water precedence, complete tile coverage, input hashes, physical/land agreement, and absence of unassigned final cells are checked by the scripts. Final output remains provisional and non-publishable until its decisions, geography, connectivity, and V7 differences have been independently reviewed.

Run focused tests with system Python and the required NumPy/SciPy/PyProj dependencies:

    cd scripts/research-diagnostic-water/v7-replay
    python3 -m unittest -q test_prefill test_prefill_plan test_compose_direct test_wrapped_shore_evidence test_finish_prefill_config test_prepare_final_plan test_portable_paths test_selected_mixed_lineage

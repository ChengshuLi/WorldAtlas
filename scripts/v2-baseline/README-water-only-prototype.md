# Exact water-only crop shortcut (research prototype, not integrated)

This candidate does not modify the active, pinned run. `water_only.py` proves that the crop including the extractor's extra neighbor rows is entirely physical water. It validates the RLE structure for physical and land on every scanned row. The caller may only skip shoreline extraction if the proof returns true; it must retain all existing core-cell validation, spherical boundary certification, input pinning, disk checks and report logic. All other crops use the unchanged extractor. The input pins must be verified before use and reverified after the run.

To integrate into a separately versioned copy of `coastal_band_adaptive.py`, import `water_only_crop`, include the module path and hash in the tile code identity, and replace the one call with:

    if water_only_crop(physical, land, crop, w, h):
        raise ValueError('no participant shorelines in crop')
    edges = core.shore.edges_for_crop(physical, land, crop, w, h, step, [x[1] for x in PAIRS], max_segments=limit)

The existing surrounding try/except handles the same no-shore result, and the existing `classify` continues to reject uncertified crop boundaries. Update the resumable runner's identity and per-tile code-hash checks to include the new module. Never claim unchanged code identity or silently mix legacy tiles with new tiles. Preserve prior partial artifacts. Any migration must verify provenance and be separately designed; a fresh output with new hashes is simpler.

Validation after copying into `scripts/v2-baseline` adjacent to `scripts/v7-replay`: `OPENBLAS_NUM_THREADS=1 python3 test_water_only.py -v` passed 300 randomized checks, wrapped x and neighbor rows, plus malformed physical and land RLE checks. Isolated real tiles with the shortcut matched baseline decompressed spans and all reported counts: polar, hit, 0.295 s vs 2.79 s; England nonempty-shore, fallback, 4.62 s and 152,191 assignments/4,416 spans. Timings were low-priority shared-host runs, not a global completion estimate. `occupancy_water_only.py` conservatively estimates 2,827 / 6,912 crops (41%) are physical-water-only, using coarse bins and neighbor rows; it is a planning diagnostic, not an input-validation or production proof. Run as `python3 occupancy_water_only.py PATH_TO_RESUMABLE_CONFIG.json` after copying next to `coastal_band_adaptive.py`, or pass `--adaptive-dir PATH` when running the prototype elsewhere. Additional tests and a representative end-to-end benchmark should precede using this candidate.

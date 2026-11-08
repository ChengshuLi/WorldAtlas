# Complete land kernel replay, 2026-11-08

The complete 131,072 × 54,614 preserved-source land replay passed. It freshly
regenerated the seed index, checked every representative against actual seed
cells, reran source-bound WGS84 decisions, and wrote every global land row.
Expected land labels supplied no hint, upper bound, certificate, stopping rule
or assignment. All resulting rows and runs matched the pinned completed
producer byte for byte. Six WGS84 ties and all Ural counts also matched.

## Measured phases

- Complete physical/component/seed preflight: 24.084 seconds.
- Fresh Python seed tiles, exact pinned manifest: 9.963 seconds.
- Actual-seed representative verification: 0.799 seconds.
- Spatial index construction: 2.733 seconds.
- Complete source-bound WGS84 search: 37.010 seconds.
- Complete Python land writer: 30.390 seconds.
- Sum of these phases: 104.980 seconds.

These are one-host phase timings, not a controlled before/after speed ratio or
a full raw-source pipeline measurement. Staging and before/after hash passes
are outside the phase sum. Nine CPUs were available to the process; other heavy
workers held their runs during this replay. UTC phase anchors were not recorded.
The date in the JSON is when the evidence was recorded, not an inferred start.

## Coverage and identity

- Physical land: 1,984,469,039 cells.
- Four seed roots and all six seed-category populations matched.
- All 457,889 nonseed component assignments were reproduced.
- 456,669 roots certified; 1,220 exactly searched; 14,280 exact queries.
- 26,693,670 output runs.
- Rows SHA-256: 8922efb4b90021e36e5491ddf65ab1eaa7f6961dfc0f81fadfbfecc45f510674.
- Runs SHA-256: dc19c358ce976b201c9861685948ca1ddae61635b10d4136c4ff19b9cb50310b.
- Ural: 43,575 land centers, 52 Europe-to-Asia and 5 Asia-to-Europe changes;
  zero other-category land labels.

The exact source, reference, code and output hashes and individual ties are in
[the evidence JSON](land-kernel-replay-20261108.json). Original archived source
configurations and reports were not rewritten. The missing historical assignment
checkpoint was replaced by a fresh source-bound search, not by copied labels.

## Reproduction

Use `scripts/v7-pipeline/stage_land_sweep_inputs.py` with the approved exact
catalog/core-config and a read-only R2 profile. Stage the complete streams and
search inputs. Then call `scripts/v7-pipeline/replay_land_sweep.py` with the
staged directory, a new output directory and `--search`. Both are ordinary
in-process Python tools; they do not launch the whole pipeline, compile code,
start subprocesses or change cloud data.

This validates preserved-input kernel equivalence. It does not reconstruct raw
sources, authenticate geographic decisions or establish acceptance. The
user-owned full end-to-end pipeline remains separate work.

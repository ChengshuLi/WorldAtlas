# General batched land coverage

The complete candidate-first pair measured 8.319192 s for 128-row numeric
batches versus 22.672494 s for the current Python row checker, an observed
2.725324× ratio. All coverage/root/category/population report fields match,
including 1,984,469,039 physical land cells, 457,889 nonseed roots and the four
selected mainland roots. The [verbatim receipt](land-batched-preflight-pair-20261108.json)
records the exact source hashes and UTC intervals (07:09:37–07:10:08 UTC).
This is one isolated preflight-only pair, not a whole-stage speed ratio.

The change removes repeated NumPy and I/O call setup across ordinary batches.
Each source's offsets and every original row/interval remain validated. uint64
positions pack row and column exactly; the algorithm does not expand pixels,
inspect available RAM, impose a cache ceiling, or choose a path by map/root/
category name. Sparse UINT32-width and arbitrary batch-size/dense oracles pass.
The previous one-row numeric prototype measured 16.329 s in a separate pair;
that is historical context, not a controlled row-versus-batch ratio.

The actual Stage2 builder now calls the numeric checker with the shared
128-row default, and its normal source identity includes both numeric modules.
The independent legacy row checker remains available for comparison. A complete
paired source-bound replay (fresh seed index, all WGS84 decisions and ties,
full writer and Ural counts) is the next integration proof. No raw-source/full
user-owned pipeline, provider authentication or geography acceptance is claimed.

# Complete numeric-writer integration

The current 128-row numeric coverage check was held constant on both sides.
Each isolated trial independently regenerated seed tiles, verified representatives,
rebuilt indexes, reran every WGS84 decision/tie and wrote every output byte.

- Current coverage + legacy writer: 90.237814 s.
- Current coverage + numeric writer: 73.051019 s.
- Observed full-kernel ratio: 1.235271×, about 19.05% less elapsed time.
- Writer phase: 30.247544 s versus 12.545130 s.

Every result matched: 456,669 certified components, 1,220 exact components,
14,280 exact queries, all six ties, 1,984,469,039 land cells, 457,889 assigned
roots, 26,693,670 complete runs and all 43,575 Ural land-center/57 relabel counts.
The source-bound checkpoint supplied no old expected assignments; expected
land labels were used only after fresh search and writing.

- Rows SHA-256:
  8922efb4b90021e36e5491ddf65ab1eaa7f6961dfc0f81fadfbfecc45f510674.
- Runs SHA-256:
  dc19c358ce976b201c9861685948ca1ddae61635b10d4136c4ff19b9cb50310b.

The [verbatim receipt](land-writer-integration-pair-20261108.json) records all
source/code hashes, the actual candidate Stage2 builder fingerprint, full phase
UTC intervals and both complete reports. The numeric writer becomes the Stage2
default only after this successful integration proof. The legacy Python writer
remains available as an independent oracle; no native helper is restored.

The last pre-rebase checks passed 414 stage2 and 118 pipeline test executions.
Independent dense oracles, varied batches, extreme identities/widths,
malformed/failure cases and exact scalar Ural arithmetic are covered. No
pixel-sized ROI array, memory-based admission rule or cache ceiling is used.

This is one reference-first complete preserved-source kernel pair, not balanced
cache order or the whole raw/provider/regional pipeline. Geographic acceptance
is separate. No user-owned full pipeline was launched or changed, and no
intermediate output was uploaded to R2. The separate writer-only pair is
[recorded here](land-numeric-writer-20261108.md).

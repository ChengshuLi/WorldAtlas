# Complete paired Python land sweep comparison, 2026-11-08

The complete original and current preflight/writer sweeps produced identical
coverage reports, land output bytes and Ural counts. The combined measured time
fell from 106.007 seconds to 52.854 seconds: an observed 2.006× throughput ratio
and 50.14% less time for these two sweeps.

- Preflight: 44.933 seconds original, 22.688 seconds current, 1.980×.
- Writer: 61.075 seconds original, 30.166 seconds current, 2.025×.

This was one reference-first pair on the same host and Python interpreter,
with other heavy workers holding their runs. It is not a balanced cache-order
study, a whole-mainland-stage ratio or a raw-source end-to-end ratio. Input and
post-run hash checks were outside the measured intervals.

## Complete input and result checks

- Grid: 131,072 × 54,614, every row consumed and written.
- Physical land: 1,984,469,039 cells.
- Nonseed assignments: 457,889, with four designated seed roots.
- All seed-category populations and physical/component coverage matched.
- All 26,693,670 output land pairs matched the pinned completed producer.
- Ural counts matched: 43,575 land centers, 52 Europe-to-Asia changes,
  5 Asia-to-Europe changes and no other-category land labels.
- Rows SHA-256: 8922efb4b90021e36e5491ddf65ab1eaa7f6961dfc0f81fadfbfecc45f510674.
- Runs SHA-256: dc19c358ce976b201c9861685948ca1ddae61635b10d4136c4ff19b9cb50310b.

The reference source files were verified against original PR4 commit b09ecb545.
Both sweep implementations were loaded from the exact fingerprinted Python
source, not an existing cached module. The same checksum-verified, identity-bound
checkpoint supplied both trials' assignments. That checkpoint came from the
[fresh source-bound replay](land-kernel-replay-20261108.md), not expected labels.
Expected land output supplied only the final comparison.

## Timing intervals and reproduction

- Original: 05:15:05.954981–05:16:51.962405 UTC.
- Current: 05:16:51.962631–05:17:44.816302 UTC.

The [exact comparison JSON](land-sweep-ab-20261108.json) records phase times,
UTC intervals, source/code/checkpoint pins and complete reports. Reproduce with
`scripts/v7-pipeline/compare_land_sweeps.py`, the preserved staged evidence,
the completed source replay, the original Stage 2 source directory and a new
output directory. The tool starts no processes and modifies no source reports.

The changes reduce Python read/unpack, write/hash and lookup overhead through
complete row batching and an input-sized assignment index. They do not sample
cells, crop input, change numerical rules, add a bounded cache or impose an
application memory limit. Geographic acceptance and the user-owned full
end-to-end pipeline remain separate work.

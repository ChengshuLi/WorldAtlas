# Land cost map and next measurement

The complete preserved-source replay covered every input/output row. Its
104.980-second measured phase sum is divided as follows:

- Physical/component/seed preflight: 24.084 seconds, 22.94%.
- Global land writer: 30.390 seconds, 28.95%.
- Source-bound WGS84 search: 37.010 seconds, 35.25%.
- Fresh seed index, representative checks and spatial index: 13.496 seconds,
  12.86% combined.

These fractions describe only this kernel replay, not the raw-source pipeline.
Source construction, witness/closure proofs, selected regional application,
source staging and final composition remain outside it. The archived component
report has its own 32.143-second historical measurement; it is not a current
controlled baseline.

## The paired test covers the largest measured share

Preflight plus writing account for 51.89% of this measured replay. Their exact
input sizes explain why the Python call overhead matters:

- Physical pairs: 26,682,201 records.
- Component triples: 13,315,490 records.
- Seed pairs: 20,319,323 records.
- Written land pairs: 26,693,670 records.
- Grid rows: 54,614.

The original reader made a Python read/unpack call for each of the 60,317,014
input records. The current reader decodes one complete row per read, about
163,842 such calls across the three streams. The writer similarly batches
writing and hashing by row instead of per output pair. These are call counts,
not predicted wall-time ratios. All records are still validated and consumed.
The complete assignment dictionary replaces repeated binary searches without
sampling or a bounded cache.

`compare_land_sweeps.py` has now paired the original PR4 b09ecb545 and current
sweeps over the same complete inputs and freshly source-derived checkpoint.
The [paired result](land-sweep-ab-20261108.md) records the observed timings. The preserved baseline files were checked byte for byte against
that Git revision. The comparator loads the exact fingerprinted Python source,
not a possibly unrelated cached module. It checks every output byte, population
and Ural count and records UTC trial intervals. The paired run completed before
the physical final proof took the released slot.

One pair gives an observed ratio in a declared order, not a balanced cache-order
study. A reverse-order repeat is the appropriate next check if the conclusion
is small or ambiguous.

## Search needs phase evidence before more algorithm changes

The current certificate proves 456,669 of 457,889 roots, or 99.7336%, before
exact search. The remaining 1,220 roots produce 14,280 exact queries. The
37.010-second search measurement includes physical witness construction,
certificate work, exact work and checkpoint writes. It does not isolate which
of those dominates.

The exact index already returns counters for candidate tiles, seed runs scanned
and WGS84 run pairs tested. The runner currently discards them. A targeted
profiling run should preserve those counts and separate witness, certificate
and exact phases before proposing tighter bounds or more batching. Changing
pruning, tie policy or numerical guards without that evidence would add risk
without an established target. No such algorithm change has been made.

## Fresh seed construction is a separate major cost

The subsequently inspected, exact catalog-pinned rasterizer report records
102.705 seconds for the complete 131,072 × 54,614 grid. This historical
measurement is excluded from the current 104.980-second kernel replay. It
includes its recorded builder/kernel path and is not a current controlled
comparison. The exact report, program and polygon hashes are in
[the seed-raster cost audit](land-seed-raster-cost-audit-20261108.json).

The current frozen builder burns serial full-width strips. A future parallel
GDAL design must keep the identical original affine transform for each strip,
use independent OGR datasets/layers per worker, preserve strip order and burn
semantics, and compare complete resulting seed streams and populations. Threads
are a possible Python/GDAL implementation route; executable subprocesses must
not be restored. This is a design direction, not a measured improvement.

The archived rasterizer references two exact assembled polygon GeoJSONs that
are not present in the recovered catalog. That is not proof of cloud absence.
Their normal producer requires fresh water/terminal closure proofs, so no
substitute rings were assembled by skipping those proofs or patching a report.
A faithful fresh-seed raster comparison needs those exact staged polygons or
normal current-producer outputs. The prepared complete kernel A/B does not
have this dependency and remains ready.

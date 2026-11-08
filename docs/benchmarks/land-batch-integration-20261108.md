# Complete land-kernel integration pair

The actual Stage2 builder now uses source-bound 128-row numeric coverage.
A separately coordinated reference-first pair independently regenerated every
seed tile, verified representatives, rebuilt spatial indexes, reran WGS84
search and wrote the complete land RLE for both coverage implementations.
No checkpoint supplied assignments, and expected labels were used only after
fresh decisions and writing. Sources and reports were never patched.

- Current Python coverage kernel: 104.133374 s total.
- Integrated batched coverage kernel: 89.159940 s total.
- Observed total ratio: 1.167939×, about 14.38% less elapsed time.
- Coverage phase: 22.733005 s versus 8.439951 s.
- Other phases were unchanged: seed-index generation about 10 s, source-bound
  search about 36 s, full writer about 29.5 s, plus index/verification work.

Every report/data result matches: 456,669 certified components, 1,220 exact
components, 14,280 exact queries, all six ties, 1,984,469,039 land cells,
457,889 assigned roots and 26,693,670 complete output runs. All 43,575 Ural land
centers and the 52 Europe-to-Asia/five Asia-to-Europe changes match exactly.

- Rows SHA-256:
  8922efb4b90021e36e5491ddf65ab1eaa7f6961dfc0f81fadfbfecc45f510674.
- Runs SHA-256:
  dc19c358ce976b201c9861685948ca1ddae61635b10d4136c4ff19b9cb50310b.

The [verbatim complete receipt](land-batch-integration-pair-20261108.json)
contains all phase durations/UTC intervals, complete code/source fingerprints,
both outputs and the actual Stage2 builder fingerprint. The actual builder
selects the same numeric API/default as the candidate replay, and its normal
code identity includes both numeric modules. The independent legacy checker
remains available for comparison, not the Stage2 production coverage path.
The final pre-rebase source passed 383 stage2 and 112 pipeline test executions.

This is a complete preserved-source land-kernel pair, not the whole raw-source
pipeline. Seed raster production, source/provider/regional admission and
geographic acceptance are separate proofs. The earlier proper-GDAL seed pair
is [recorded separately](land-python-api-pairs-20261108.md). One ordered pair is
not a balanced cache-order trial; minor variation in other phases is included
in the observed total. The user-owned pipeline was not launched or changed.

The remaining measured largest kernel costs are WGS84 search (36.4 s) and the
writer (29.6 s). A general numeric writer is a credible next investigation;
no speed or correctness claim for that unimplemented path is made here.

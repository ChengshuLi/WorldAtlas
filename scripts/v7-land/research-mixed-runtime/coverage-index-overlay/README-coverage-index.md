# Reuse whole-component coverage within one build

The mixed resolver builds a transient all-root cell-count index at the first
all-center containment decision. It validates every physical/component row
once, then reuses counts for later decisions in that same resolver call. The
intended semantics preserve source geometry, selected decisions, boundary rules,
component IDs and output format. The existing non-indexed selector remains
available.

This is a research overlay, not a standalone runtime. Assemble it only with
matching reviewed dependencies; publishing this code does not deploy a map.

The index is trusted in-process caching, not an adversarially immutable
snapshot. Each use checks the resolved stream identities and file metadata;
the outer resolver must authenticate input hashes before and after resolution.
The caller must use an external process-group RSS guard, because index memory
scales with the number of distinct roots. If those conditions cannot be met,
use the existing non-indexed path. The index is not persisted across runs.

Synthetic tests check output and error parity and reject a changed generation.
A bounded benchmark compared 12 representative queries over four sampled
1,024-row windows of the pinned physical/component streams. It is not a full
map replay or a scientific validation. Full-map equivalence and performance
must be measured when a future map rebuild is authorized.

## Combined runtime verification

The 1,540.609-second draft163 run used the unindexed archive/territorial
resolver and the unbatched GeoNames reader. An isolated copy of that same
assembled runtime was tested with this coverage overlay and the adjacent
`shared-geonames-zip-overlay` applied together. The polygon suite passed 924
tests and the point/resolver suite passed 1,016 tests, including two-point
old-versus-batched claim parity. These are tests, not a full map replay.

The two coverage files replace the matching files in
`group-label-multipolygon-prototype`; the two GeoNames files replace the
matching files in `geonames-point-integration-20261105/point-component-prototype` (the historical runtime aliases this to `point-integration`). Do not apply
those replacements to a different assembled resolver without checking for
intervening geographic or interface changes. This tested combination requires
`polygon_intersection.py` SHA-256
`391c7dee1b91dfa9c78ad087a46a9c9e9c8df778183ebc706b481e0286d110d5`.

The combined runtime's changed code SHA-256 values are:

- `polygon_resolution.py`: `4bb8639e2748c78d4317bf89ae18b87c88c36afccd13258757a9d69116bc6639`
- `full_coverage_policy.py`: `a0b71d2508e65f2cd96958620f0c42df39fdd70392a0063db6a54dbd64a1ffaf`
- point `resolve.py`: `616ce4350f2b85fa311e05a43e045cfa858384853a289b1b6708f3e69d63eb5f`
- `geonames_extract.py`: `56ddd15280866c7916520c7db6bc441af298d61d082e61ed497aa54ce50f78e3`

Refresh the parent configuration's code pins, the point request's resolver
and extractor pins, and the point request's own parent hash. Continue to pin
all other inputs and code, hash streams before and after resolution, and use a
process-group RSS guard. A prior sampled benchmark showed equivalent output
for 12 coverage queries over 4,096 rows in 6.76 seconds unindexed versus
0.905 seconds with index creation and queries. Host load, full-grid root
counts and real decisions differ; do not treat this as a full-build speedup.

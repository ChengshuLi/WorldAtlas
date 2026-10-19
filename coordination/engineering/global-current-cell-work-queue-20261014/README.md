# Current native-cell work queue

This is a work plan for future workers, frozen at accepted selection
`a61b6f9e7f88b1da380e3a834f89d7509132ed71`. It starts with the complete selected
owner-zero raster, not earlier gap polygons or their component/batch inventory.
It does not change geography or approve any particular repair.

## In plain terms

There are 660 work packages. They are questions or repair candidates, not 660
confirmed errors:

- 200 packages can start checking source-backed repair candidates
- 444 packages need mapping, shared-source or physical interpretation work
- 14 packages investigate land absent from the retained territorial sources
- 2 packages handle the Antarctic policy and one malformed physical source

Give related packages using the same source to one worker. The package tells
them exactly which cells to examine, which evidence to reuse, what to decide
and how to finish. Start with `global-work-queue.json`; the detailed source and
physical queues sit underneath it.

## Start a worker

1. Read the combined queue and select a source-family session. Keep its related
   cause packages on one worker so the original source is decoded/indexed once.
2. For a source/cause package, run the committed package-bound ownership command
   below once. It derives the complete original interval table and checks current
   selected owners from immutable Git inputs; no separate extraction or adjacent
   data-file checkout is needed. The separate physical-only queue retains its
   existing Python selector; see `PHYSICAL-PACKAGES-README.md`.
3. Read the exact intended owner IDs, source feature IDs, locality scopes,
   competitor source families, native blocks, measured cost, question and
   completion condition. Reuse the original repository source products named by
   their catalogue; this directory does not copy the original source corpus.
4. Use that same report's `original_intervals` and per-key owners to account for
   already-owned intervals before an additive repair. Preserve the full original
   table and denominator; do not rerun extraction to reconstruct its source/class
   columns. Recheck current ownership when the accepted data revision changes,
   without rebuilding this queue or repeating unaffected source research.
5. For the remaining cells, check the current selected owner-zero state,
   source-to-location authority, explicit territorial exclusions and all relevant
   competitors. Then use the existing source-target native operator, verify
   conservation and coordinate normal reviewed integration.

From an owned checkout, with an exact accepted data commit and fresh output file:

```sh
GIT_NO_LAZY_FETCH=1 GIT_NO_REPLACE_OBJECTS=1 \
  node scripts/observe-selected-owners.mjs --repo . --commit EXACT_DATA_COMMIT \
  --package gb-GRL-ADM1--repair-evaluation --out /path/to/new-observation.json
```

Use `original_package` and `original_intervals` from this one report. Interval rows
are `[y,start,end,candidate_owner_indices,source_feature_indices,physical_class]`;
ends are exclusive. Owner/source indices and mask classes retain their original
queue meaning, not current scientific qualification. The report also binds both
code/data revisions, original interval/key hashes and actual consumed input pins.
See [the bounded ownership contract](../../../docs/COVERAGE_CLASSIFICATION.md#observe-selected-ownership-without-source-geometry)
for runtime, input acquisition and output requirements. Missing pinned Git bodies
still refuse; they are not silently fetched or replaced with checkout files.

The current standalone `source-batch-intervals.mjs` command is removed. Its pure
extractor is shared by the ownership command, with no checkout-file fallback.
Frozen package `execution.command` fields record historical execution; exact old
code/input pins remain available for historical audit, not current package work.
Physical source qualification and native repair acceptance remain separate operations.

## Use source/cause packages, not connected components

`source-package-queue.json` contains 644 territorial packages grouped into 368
source-family sessions. Its disjoint categories cover 40,589,285 owner-zero cells:

- 200 repair-evaluation packages: 6,911,949 cells with one lineage candidate and
  retained land or inland-water support
- 28 shared-lineage packages: 6,956,846 cells where source ancestry is shared by
  current locations; resolve the reusable source/subregion crosswalk together
- 89 source-conflict packages: 3,496 cells with incompatible overlapping mapped
  source features; these are mapping conflicts, not automatically disputed borders
- 172 location-mapping packages: 23,828,471 source-covered cells without a present
  location join
- 155 physical-interpretation packages: 2,888,523 unique lineage candidates outside
  the retained physical land/water masks

Related categories belong in the same source session, not separate worker or PR
assignments by default. Small conflict packages are part of that family's work.
The 2,869 source/province locality groups and 523,918 planar four-neighbor connected
cell groups are diagnostic scales, not execution tasks. The component diagnostic
has no wraparound union between columns zero and `size-1`.

The separate physical queue covers the disjoint 100,304,914 retained land-support
cells outside all retained territorial source footprints. Together these scopes
contain 140,894,199 distinct owner-zero cells. These are source-relative discovery
and investigation counts, not a count of wrong or repairable cells. Antarctic
policy and malformed-source investigations are separate and add no repair-cell
claims to that denominator.

## Efficient scheduling and completion

The first source-backed evaluation sessions include Russia ADM2, Norway ADM2,
Greenland ADM1 and Canada ADM3. Package costs record actual original-source decoded
bytes, complete competitor inputs, measured full-source raster seconds and sparse
interval counts. For example, the full Russia ADM2 source pass took 12.279 seconds;
it did not require one operation per candidate cell.

Process native row blocks sequentially using the existing 4,096-row operator
boundary. Split delivery only at real source, locality, resource or integration
boundaries. Do not create one task per component or set arbitrary cell quotas.
Read-only research is parallel. Repair authoring claims must have disjoint owner
IDs and interval selectors; shared crosswalk changes coordinate all dependent
packages. Final selected-bank changes still use the normal serialized merge path.
Revalidate against current ownership when work is resumed; newer repairs can make
parts of this frozen inventory stale without invalidating the retained evidence.

The largest shared-lineage concentration is Canada ADM3: a few original
unorganized administrative regions were divided among named physical atlas
regions. Its millions of affected cells require a small number of source-crosswalk
questions, not millions of manual ownership decisions. Broad unmapped-source
families also include Ukraine ADM1, Canada ADM1, China ADM1, Tanzania ADM1 and
Brazil ADM1. Their source dates and roles differ; a coarse administrative footprint
is not automatically an applicable current-location boundary.

## Evidence and limits

- All 368 retained territorial products and 73,567 original source features were
  read and hash-checked. 66,431 features have present-location lineage. The selected
  49,625-location roster was joined through all 36 selected source parts plus
  explicit source-member and historical semantic aggregation records.
- Land/water support is from the complete available retained GSHHG hierarchy.
  Its vintage is not perfect contemporary ground truth. Missing physical support
  does not establish ocean, and river water never vetoes a sourced location.
  Explicitly reviewed territorial holes can constrain an actual repair.
- The unique candidates contain 6,736,231 retained land-support cells and 175,718
  retained inland-water cells. All other source-backed candidates are still
  retained in their corresponding interpretation or mapping packages.
- Three Fiji antimeridian features required the existing periodic source
  canonicalization recipe. Original and transformed geometries are retained in
  `normalized-source-seams.json`. Independent full-source native-span comparison
  found the same native cells before/after periodic interpretation. They were not
  silently treated as unchanged raw coordinate arrays.
- `raw-native-supported` means compatible with the numerical raster operation.
  It is not a validity, topology, physical truth or territorial approval claim.
- Complete independent retained-source checks at four large Arctic physical-only
  witnesses confirmed that they lie outside the actual retained Greenland/Canada
  territorial polygons. See `arctic-territorial-source-sanity.json`; this supports
  a source-coverage disagreement, not automatic assignment to a nearest location.
- Antarctica is excluded by current repository policy. The territorial corpus has
  no Antarctica product. One malformed GSHHG level-one source remains an explicit
  conservative-envelope investigation, not invented repaired geometry.

## Compact custody and reproduction

`ownership-binding.json`, the retained source catalogue, current lineage and the
source/physical summary files bind the exact operands and all sparse blocks.
The source and physical selectors validate both encoded and decoded hashes.
Large metadata is gzip transport of the same canonical bytes. One source block
has two complete row-array transports to satisfy the existing trusted evidence
validator's 32 MiB per-file decoded limit. Its original logical hash and counts
are preserved. No checker bound is changed.

The full raw-source pass took 184.297 seconds and 583,905,280 peak RSS bytes; global
source aggregation took 25.802 seconds and 884,973,568 peak RSS bytes. Source and
physical inputs were streamed. Future packages reuse these interval products;
they do not need to repeat a worldwide rasterization. Actual extraction controls
covered relocation, compressed-only metadata, altered source roster, corrupt
interval bytes and pre-existing output directories. Independent review remains
required for the exact PR head and later geographic changes.

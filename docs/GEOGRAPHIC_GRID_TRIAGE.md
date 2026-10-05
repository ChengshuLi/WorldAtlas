# Geographic coverage triage against the actual grid

`scripts/triage-geographic-grid.py` reads an immutable registry and compares every
retained connected gap component with the actual canonical ownership product.
This is investigation evidence for #946. It does not change boundaries or assign land.

The native reader preserves the manifest's exact size and coordinate bits. It verifies
whole original encoded and decoded hashes for every row/run partition, complete row
accounting, run ordering and nonoverlap across partition boundaries, and every owner
against the exact integer-to-location inventory. A bounded decoded-part cache keeps
reads small. The current release, hierarchy, manifest, selected containing geography
files, original component partitions and frozen water report are independently pinned.

Each valid unchanged component gets one deterministic representative point. The
containing canonical cell, actual owner and inverse-projected cell centre are recorded
separately. The centre may lie outside a thin component. If floating-point rounding
cannot produce a strictly interior representative point, the component stays in the
output with unknown sampling status. There is no minimum area filter, snapping,
simplification, buffer, MakeValid or nearest-location assignment.

This is not exhaustive raster coverage: all other cells remain unchecked, and grid-only
gaps outside retained continuous components can remain undiscovered. All original
fragment IDs appear exactly once; blocked tiles, unmeasured fragments, domain and
reference-shore flags remain intact. Inherited measured areas retain their original
context; they are not new measurements. Multiple nearby IDs are inherited diagnostic
context, not certified adjacency. Priority counts describe investigation buckets,
not counts of confirmed geographical defects.

For sampled owned cells whose centres are strictly inside a continuous gap, a selected
unchanged current owner shape is tested both in native longitude/latitude and after
projecting its original vertices to the app's Mercator grid. Straight edges between
projected vertices differ from straight longitude/latitude edges. This can explain
an apparent discrepancy without a broken grid. Edge/tie and unexplained cases stay
flags. Missing selected owner geometry stays unknown; it is never inferred from names.

The two existing pilot anchors are read from the actual grid. Exact current footprint
contacts are extracted for the declared pilot subjects. Positive boundary length,
point-only contact and every positive-area numerical intersection are distinguished.
Current atlas footprints remain derived data, requiring native-provider verification.
Source metadata and original full-feature hashes are retained. Research links come
from exact machine-readable member inventories in retained original GitHub API
responses, rather than regional issue titles. Snapshot links describe retrieval-time
scope; future coordination must recheck live claims and preserve other workers' work.

`coordinated-followups.json` stages bounded joint source investigations for both sides
of the Iran–Pakistan and Portugal–Spain components. It records exact contacts and
existing regional packets. It authorizes no territorial assignment or deployment.
A source-backed repair requires mutually consistent neighbor evidence, stable identity
and release/crosswalk checks, independent review, geographic regression controls,
and subsequent certificate/content revalidation. The frozen water pilots retain their
source encoding, date, limited AOI, unobserved-month and registration uncertainty.

With the committed Python preparation dependencies installed:

```sh
python -I -B test/geographic-grid.py
```

Reproduction passes an immutable commit containing the registry and protocol snapshots,
its exact whole-file bytes/hash, and an unused destination. The evidence manifest records
the frozen input commit and exact command. Geography inputs come from the registry's
separate immutable reference commit. Working-tree substitutions do not change reads.
Output overwrites and symlink destinations are rejected. Report and sample partition
bytes must match in two separate full runs without normalization. The complete original
partition pins and native integrity checks do not imply complete pixel classification.

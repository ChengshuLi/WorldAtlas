# Refining geographic coverage candidates

Issue #946 refines the immutable audit from #909. It does not change map
footprints, assign an administrative owner, authorize water exceptions, or
publish anything. Rendering (#907) and prevention of newly introduced coverage
loss (#920) are separate parts of the global coverage work.

The original audit partitions a declared physical-reference domain into
five-degree tiles. A single candidate can therefore appear as multiple fragments.
`scripts/refine-geographic-components.py` reads a whole-file pinned report and
its original candidate bundles through ordinary Git blobs. It checks the report's
original evaluation inputs at their original commit and separately compares those
bytes with the specified input commit. That comparison does not change the
original evaluation date or certify new geographic inputs.

`scripts/geographic_components.py` joins valid positive Polygon fragments on
positive-length shared contacts. It uses exact retained coordinates without a
buffer, rounding, snapping, simplification, area cutoff or geometry repair.
Positive-area intersections are retained as input-overlap defects and flag the
entire component. They cannot establish a unique measured union area.
Point-only contacts do not themselves join components and retain an explicit
ambiguity record. Other shared edges can still connect the same fragments.
The spatial index filters candidate pairs; it does not determine connectivity.

At longitude +/-180, translated copies are used only to test exact cylinder
contacts. Component output unions retain original longitudes; a component crossing
the date line may be a planar MultiPolygon. No polygon is drawn across the entire
world to connect its ends. Holes and separate islands remain in the geometry.

Component identity hashes the sorted original fragment IDs and canonical
whole-feature hashes. Membership binds each fragment to its unchanged original
bundle and whole-file SHA-256. Component shapes, contacts and source bindings are
deterministic gzip partitions, each bounded to 32 MiB after decompression.
Destinations must be new nonsymlink vintages; prior results and original sources
are never replaced.

Measured area totals are sums of the existing measured fragment values. They are
not new physical-water measurements or a certification of missing land. Every
original null measurement and blocked tile remains explicit. Domain-edge and
blocked-tile contact flags, including wrapped date-line contacts, identify additional limits, without inventing coverage
inside a blocked area. Nearby location/source metadata remains an inherited
diagnostic; its original halo search does not certify true neighbor adjacency.

Reproduce the retained component product from the repository root, with the pinned
Python dependencies installed and an unused output directory:

```sh
python -I -B scripts/refine-geographic-components.py \
  --commit c881d662da6cbba6f6bc7f988af57ab7dc98c0a4 \
  --report coordination/engineering/coverage-gaps-907-20261005-local01/global-v3/report.json \
  --report-bytes 12965 \
  --report-sha256 3a52c875e5bb4d39a56faa5ad04785e6be5d0e0f8c9eac97500a7a23ca399ae0 \
  --out .cache/your-unused-components-run
```

Two runs compare each output's encoded and decoded SHA-256, in filename order.
Report comparison normalizes only output destination paths; membership, geometry,
source/input pins, unknowns, software and all counts must agree. Controls cover
tile edges, point contacts, tiny genuine separations, holes/islands, date-line
edges/points, overlapping inputs, blocked areas, unknown measurements, input
permutation, immutable reads, whole-report pins and overwrite/decompression limits.

Detailed numeric water pilots, actual canonical integer-grid discrepancy checks
and coordinated source-backed repair followups remain subsequent work in #946.
Existing regional research retains its scope. A physical-water observation does
not determine which province owns a gap; ownership repairs require compatible
administrative sources and joint release/certificate/content revalidation.

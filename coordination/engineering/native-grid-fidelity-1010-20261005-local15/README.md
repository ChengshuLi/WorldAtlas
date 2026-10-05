# Native-grid fidelity work in progress

Issue #1010; offline engineering only. Initial data/code baseline:
`d55795e4c0ad01527029db0bd1d774124a12a61a`, the merged #973 diagnostic.
Original grid pin: `73899e8581d74634d6304a9e52aa32849dd174730aba2c6cc48db512a985d1f6`.
Original hierarchy pin: `568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b`.

`src/native-grid.js` defines a separately versioned membership rule. It evaluates
original binary lon/lat coordinates at a supplied inverse-projected latitude
table and exact rational canonical longitudes. Exact integer orientation and
intersection thresholds determine spans; there is no tolerance, snapping,
minimum-area discard, or nearest-owner fill. Latitude uses minimum-exclusive,
maximum-inclusive edges; longitude spans include their left threshold and
exclude their right threshold. Boundary incidences, including duplicates, are
retained separately. First original owner wins; native holes stay empty.

Eight initial controls pass, including the actual application's demonstrated
collinear-vertex projection gap, an independent integer orientation oracle over
every cell of a small grid, holes/islands/overlaps, partition equality, shared
edge/horizontal endpoint ties, split dateline pieces, polar clipping, tiny
features and malformed inputs. These are controls, not a worldwide result.

Remaining: immutable full-source loader and whole-domain comparison, original
source validity accounting, pinned latitude-table bytes, two deterministic world
runs and resources, all changed/ambiguous cell inventories, separately pinned
candidate grid, original grid/rule/history preservation, coverage classification
and release/content bindings, CPU/GPU/Canvas parity, exact-head independent
review, applicable CI and normal queue. No candidate is installed or published.
Original source authority, native topology, physical water and factual territorial
approval are not established by this numerical rule. Source gaps and physical
classification remain separate from projection discrepancies and #1005.

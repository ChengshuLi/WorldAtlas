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
features and malformed inputs. These are numerical controls; geographic source authority remains unapproved.

The first two complete world runs at immutable execution head
`78a756cb8f616663e96d2cc8e2355bd73afbe4b9` agree in every scientific byte.
They retain every discrepancy interval. Those scratch vintages remain preserved;
a later execution head removes only a redundant derived roster export to fit the
existing evidence budget. The complete roster remains recoverable from unchanged
original bounds and all world-part files, with its canonical JSON digest recorded.
No original source, finding, ownership span or normative latitude byte is dropped.

The focused first PR contributes the full native comparison, versioned offline
membership implementation and separate original native planar validity accounting.
It changes no application caller or prepared production asset. Generated reports
are frozen evidence at their recorded execution/baseline commits, not measurements
of a later PR tree. The exact execution bootstrap must be used for reproduction.

Remaining in this issue: a separately pinned candidate grid with an explicit
method version; preservation of original grid/rule/releases; coverage-classification
and release/content bindings; CPU/GPU/Canvas parity; full candidate/native comparison;
exact-head independent review, applicable CI and normal queue. No candidate is
installed or published. Physical-water classification, source authority and factual
territorial approval are not established by this numerical rule. True source gaps
remain separate from projection discrepancies and the global follow-up #1005.

## Reproduction

Allocate a managed sparse review slot at execution bootstrap
`71f9e596204cee5a754bf8bd77eb53131fb22c85`, preserving all baseline
blobs in the shared Git store. Include this owned packet, scripts, src, tests and
requirements. Run the storage admission check before generation. The original
102 input files are read as pinned Git blobs, not copied into the checkout.

```sh
node --test test/native-grid.test.mjs
node scripts/audit-native-grid.mjs --repo . --commit d55795e4c0ad01527029db0bd1d774124a12a61a --out .cache/native-run-a --row-start 0 --row-end 262166 --partition-rows 4096
node scripts/audit-native-grid.mjs --repo . --commit d55795e4c0ad01527029db0bd1d774124a12a61a --out .cache/native-run-b --row-start 0 --row-end 262166 --partition-rows 4096
python scripts/audit-native-topology.py --repo . --inputs .cache/native-run-a/inputs.json --out .cache/native-topology.json
```

Use Node 24 and the committed Shapely/NumPy preparation versions. Compare every
scientific product in the two fresh output directories, excluding `progress.json`
whose measured timing/RSS observations differ. Compare the result inventory with
the retained `reproducibility.json`. The pinned Float64 little-endian latitude table
is normative for these numerical results; inverse Math cross-platform identity
has not been established. Validity output includes Python/GEOS versions, so its
byte reproduction additionally requires that recorded environment.

Every discrepancy records row, half-open column span, stored index and complete
native owner set. Resolve indices against the unchanged original bounds, then
original IDs against all pinned world-index parts for names/source paths/parents.
The loader validates the entire crosswalk, not only discrepant locations.
The native source atlas excludes Antarctica. A checked grid cell outside source
coverage is accounted for but is not certified as water or complete geography.

## Frozen worldwide results

At the recorded original data baseline, both retained full-domain vintages cover
all 262,166 rows and 68,731,011,556 cells. The 68 scientific products match byte for
byte. There are 21,485 projection-empty cells, 34,441 projection-overpaint cells,
658,971 projection-foreign-owner cells, and 714,897 first-owner differences overall,
retained as 198,608 discrepancy intervals. Native multiple-owner cell count is zero
at sampled centres; this does not prove absence of continuous sub-cell overlaps.
Both-model-empty cells remain unclassified. No exact boundary centre incidences
occur in this source vintage; the positive synthetic tie controls remain required.

Separate original native planar accounting checked every one of the 49,625
features, with no invalid or empty geometries. It references the complete original
input inventory and includes positive hole / negative self-crossing and overlapping
multipart controls. The row-comparison reports deliberately do not claim this
separate check themselves: their `native_topology_verified` flags remain false.
Read the separate `native-topology-v1.json` proof for native planar validity only.

The old roster-export vintages and metadata correction preserve identical
mathematical findings, domains, counters and boundary diagnostics in every part.
They are not relabeled as the later execution. Timing and peak RSS observations
are retained separately and do not enter deterministic scientific hashes.

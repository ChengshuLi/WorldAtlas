# Exhaustive pinned canonical-grid representation audit

Issue #973. This is an offline diagnostic; it changes no footprints, source bytes,
location owners, grid assets, release history, certificates, facts or live website.
Geographic truth, water classification and source-backed gap repairs remain open.

## Verified scope

Both complete runs cover all 262,166 rows / 68,731,011,556 cells, with zero
unchecked cells. All 49,625 original locations, 56 encoded/decoded partitions,
28,809,329 native runs, identity/parent roster and release/hierarchy/grid pins are
verified. The original stored grid agrees with the application's projected
footprint membership and first-owner convention: zero raster-only gaps, owned
cells outside projected coverage, foreign owners or first-owner differences.
This does not mean source geography is complete. A hole in the footprints remains
uncovered in both representations; water and continuous source gaps are separate.

The complete inventory retains 1,801 cells under multiple location memberships,
in 1,732 row intervals / 192 owner sets. These are representation findings, not
confirmed territorial defects. Boundary/source/projected geometry interpretation
needs separate review. All 715 bitwise stored/executed projection-bound differences
remain visible without a tolerance cutoff. Every row partition records these
bounds and its declared checked/unchecked domain.

The 65 gzip row products from two independent whole-world runs are byte-identical.
Ten actual rasterizer/compiler and synthetic controls cover holes/islands,
overlaps/priority, grid-only gaps away from a sample, centre/endpoint ties,
dateline splits, wrong projection, row partitions and malformed inputs. Three CLI
negative controls reject invalid commit, oversized domain and output overwrite.
Whole-file and independent review requirements remain pending until accepted.

## Method and limits

`scripts/audit-grid-intervals.mjs` generates sparse intervals over at most 4,096
rows, using the actual projected vertex/edge and deterministic first-owner rule.
It counts distinct overlapping owners, including duplicate same-owner polygons,
without a world-sized per-cell matrix. Original compact native assets occupy
bounded memory. Invalid original projection geometry is neither repaired nor
approved by its even-odd application interpretation.

`scripts/audit-canonical-rows.mjs` reads only immutable ordinary Git inputs,
checks source/decoded hashes and all native runs, and validates complete world
identity/parent context. Every source file is in `inputs.json`. Its execution
sources must match its actual Git HEAD. This prevents silently reproducing with
modified code; results record both baseline and execution commit separately.
`scripts/audit-canonical-world.mjs` runs row partitions sequentially with exact
complete/incomplete accounting and fresh output directories.

Frozen scientific bootstrap: `51937ce` (full SHA in inputs/report). Original data:
`5b72dc3adf48b089c3319b18c3a447468196176a`. Results are archived to this exact
framework and execution bootstrap. The added world driver wraps the same CLI;
the actual recorded runs used retained local controller commands, not a claim
that this new wrapper generated those archived observations. Timing/memory are
raw local observations in `local-resource-observations-v1.json`; they are not a
cross-machine performance promise.

## Reproduce

Use the managed allocator, distinct reviewer ID, storage admission and one sparse
detached review slot at the **execution bootstrap** in `inputs.json`; include
`data/canonical-grid`, `data/hierarchy.json`, `data/world-index.json` and release
pointers. Original geography parts are consumed as immutable Git blobs, not full
checkout copies. Executable source bytes in the final PR must match bootstrap
versions for the row/interval algorithms. Review added tests/driver at the exact
PR head separately. Do not substitute current source geography or change HEAD
mid-run. Preserve recorded outputs and use fresh owned scratch directories.

Run the bootstrap row CLI with the pinned data commit, iterating half-open row
ranges `[0,4096)` through `[262144,262166)`, fresh gzip output per partition.
Repeat all ranges independently and compare all 65 whole-file hashes to
`reproducibility.json`. The world driver may run from an independently inspected
file using `--repo BOOTSTRAP_SLOT --commit BASELINE --out FRESH_OWNED_DIRECTORY`.
Run current-head `node --test test/audit-grid-intervals.test.mjs` for ten controls.
No npm install or Python dependency is needed.

Full-world/source-gap context (#946), incomplete physical references, regional
source repair #991 and Portugal-Spain #972 are not cleared by this audit. No
publisher chat, browser, provider writes or deployment occurred.

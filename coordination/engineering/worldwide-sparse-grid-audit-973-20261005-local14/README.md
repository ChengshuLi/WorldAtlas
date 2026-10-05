# Exhaustive pinned canonical-grid representation audit

Issue #973. This is an offline diagnostic; it changes no footprints, source bytes,
location owners, grid assets, release history, certificates, facts or live website.
Geographic truth, water classification and source-backed worldwide repairs remain open.

## Verified scope

Both corrected complete runs cover all 262,166 rows / 68,731,011,556 cells, with zero
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
bounds and its declared checked/unchecked domain. `overlap-location-context.json`
resolves every overlapping owner index to its original stable location ID, name,
parent and prepared source metadata with whole-file source receipts. These are
unclassified references, not independently approved current/native geography or
political affiliation.

The 65 gzip row products from two independent corrected whole-world runs are
byte-identical. Twelve actual rasterizer/compiler and synthetic controls cover
holes/islands, overlaps/priority, grid-only gaps away from a sample,
horizontal/endpoint/upper-vertex ties, dateline splits, wrong projection,
row partitions and malformed inputs. Three CLI negative controls reject invalid
commit, oversized domain and output overwrite. Forty-two merge-integration
controls include exact-once shard coverage and actual per-shard browser needs.
Whole-file and independent review requirements remain pending until accepted.

## Method and limits

`scripts/audit-grid-intervals.mjs` generates sparse intervals over at most 4,096
rows, using the actual projected vertex/edge and deterministic first-owner rule.
It counts distinct overlapping owners, including duplicate same-owner polygons,
without a world-sized per-cell matrix. Original compact native assets occupy
bounded memory. Invalid original projection geometry is neither repaired nor
approved by its even-odd application interpretation.

Boundary diagnostics preserve every emitted original-edge incidence: horizontal
centres are integer column spans `{y,start,end,owner,kind}` for `[start,end)`,
including segment endpoints when they coincide with cell centres. Nonhorizontal
active intersections and excluded upper vertices use `{y,x,owner,kind}` records.
Duplicate vertices/edges/owners remain explicit. Diagnostic record counts count
sparse records; centre incidences sum span lengths and point incidences, including
duplicates. Neither is a count of unique ambiguous cells or confirmed defects.
The unchanged actual raster fill uses its original half-open convention.
This checks the current projected straight-edge model; it does not prove that
model is faithful to native lon/lat polygon membership at inverse-projected cell
centres. A source-equivalent collinear-vertex control demonstrates that separate
projection blind spot. General audit/correction is tracked in #1010 without
changing native geography. It is not attributed to any real-world gap by this
synthetic control.

`scripts/audit-canonical-rows.mjs` reads only immutable ordinary Git inputs,
checks source/decoded hashes and all native runs, and validates complete world
identity/parent context. Every source file is in `inputs.json`. Its execution
sources must match its actual Git HEAD. This prevents silently reproducing with
modified code; results record both baseline and execution commit separately.
`scripts/audit-canonical-world.mjs` runs row partitions sequentially with exact
complete/incomplete accounting and fresh output directories. The two corrected
recorded runs used this committed world driver.

Corrected frozen scientific bootstrap:
`060c51d04caca6bf38d8d11dbb4fdc3cc3c3a411`. Original data:
`5b72dc3adf48b089c3319b18c3a447468196176a`. Earlier results and ten-control
receipts remain preserved in pushed ancestor PR head
`8fa7c5ab9f93ca298371f7db75bab732a83f877d` (original execution `51937ce`).
That head was not accepted: independent review found incomplete horizontal and
excluded-upper-vertex tie diagnostics. This new vintage regenerates all row
products after fixing both cases, rather than relabeling the earlier result.
Timing/memory in `local-resource-observations-v1.json` are raw observations from
the first corrected run, not a cross-machine performance promise. The filenames
retain this packet's original version labels; execution pins distinguish vintages.

## Reproduce

Use the managed allocator, distinct reviewer ID, storage admission and one sparse
detached review slot at the execution bootstrap in `inputs.json`; include
`data/canonical-grid`, `data/hierarchy.json`, `data/world-index.json` and release
pointers. Original geography parts are consumed as immutable Git blobs, not full
checkout copies. Executable row/interval/world sources in the final PR must match
bootstrap versions. Review current tests/metadata at the exact PR head separately.
Do not substitute current source geography or change HEAD mid-run. Preserve
recorded outputs and use fresh owned scratch directories.

Run the committed world driver using `--repo BOOTSTRAP_SLOT --commit BASELINE
--out FRESH_OWNED_DIRECTORY`; it iterates `[0,4096)` through `[262144,262166)`.
Repeat independently and compare all 65 whole-file hashes to
`reproducibility.json`. Aggregate only complete progress records; retain source
rosters, all finding records/owner sets, bounds differences and tie incidences
without filtering. Reproduce the context registry by resolving every owner index
in the complete overlap ledger through the pinned original bounds roster and
world-part features; verify all raw part hashes and exact parent equality before
extracting the declared prepared metadata fields. Never infer source dates or
missing metadata. Run current-head `node --test test/audit-grid-intervals.test.mjs
test/merge-integration.test.mjs` for 54 controls. No npm install or Python
dependency is needed for the row generator or these controls.

Full-world/source-gap context (#946), incomplete physical references, regional
source repair #991 and Portugal-Spain #972 are not cleared by this audit.
General source-preserving projection correction follows #1010. Worldwide follow-up #1005 discovers candidates before coarse water masking and
retains all old/new relationships and previously blocked domains; it does not
limit investigation to the two examples. No publisher chat, browser, provider
writes or deployment occurred.

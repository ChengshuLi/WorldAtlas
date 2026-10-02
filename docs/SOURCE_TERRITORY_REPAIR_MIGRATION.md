# Staged source-territory identity and footprint repairs

`python scripts/apply-source-territory-repairs.py` prepares **a fresh, separate stage** under `.cache/source-territory-repair-stage`. It never writes live geography, the SQLite database, hosted entities, published ownership or environmental products. The output directory must not exist and cannot be inside `data`. All 49,614 source input geometries, original inspected source files, exact area helpers and proposal files are pinned and checked. Inputs changing during preparation fail the stage.

The stage implements the complete 25 inspected duplicate-source unions in `data/source-territory-splits.json.gz`, independently of political ownership. Source IDs remain stable; the retained source identity keeps its geographically reviewed current parent. It does not choose geography parents based on the winning modern polity. The separate licensed full Vatican source replaces the placeholder, retaining both Vatican and Roma identities and subtracting the occupied footprint from Roma. All proposals and original source vintages remain archived.

The two previously blocked Morocco/Mauritania seams measure 0.913054 and 0.929302 m². Each is reconciled by exact polygon difference against its pinned unchanged named neighbor. The receipt includes both hashes, neighbor identity, and WGS84 removed area. Removed coverage still belongs to that neighbor. This is a narrowly validated numerical topology operation, without buffering, area targets, new world land, or pixel reassignment. A candidate seam of one square metre or more, or one differing from its inspected measurement, fails. Floating-operation comparison tolerance is explicitly 0.001 m²; it is never permission for source-driven territorial growth.

## Executed global validation

The exhaustive stage checked all before and after polygons with an STRtree and calculated every positive-area intersection using the existing WGS84 surface integral, including antimeridian-aware geometry handling. The result was:

| Check | Result |
| --- | --- |
| Before / after active locations | 49,614 / 49,589 |
| Existing IDs with changed footprints | 27 |
| Removed / newly created location IDs | 25 / 0 |
| Fully unchanged location records and geometries | 49,562, compared exactly |
| Empty geographic groups archived and pruned | 7 |
| Introduced positive-area overlap pairs | 0 |
| After invalid or empty geometries | 0 |
| World land added or left uncovered | None beyond the explicit floating-operation tolerance |
| Remaining baseline overlap pairs | 1,121 numerical slivers |
| Largest remaining / total measured overlap | 1.226332 m² / 389.604880 m² worldwide |

Remaining numerical slivers are reported exhaustively and are **not** described as an overlap-free source atlas. The canonical grid separately provides exactly one location identity per land cell. The stage does not close source-vintage, coastline, granularity, or semantic review gaps. Existing source footprints can contain marine territory; historic assignment must still respect approved applicable land-footprint evidence.

Every retained location has exactly one complete adjacent-tier chain. Empty ancestor groups are retired, archived with original names/parents/metadata, and pruned rather than retained as active geography. Parent footprints should continue to derive from member locations rather than independent parent polygons.

## Stage schema and identity/history preservation

- `before/world-index.json` and `before/geography/part-*.json`: complete exact original coordinate snapshots.
- `after/world-index.json` and `after/geography/part-*.json`: complete staged corrected snapshots.
- `before/hierarchy.json` and `after/hierarchy.json`: original and pruned geographic membership sets.
- `before-boundaries.json` and `after-boundaries.json`: supported non-example dated footprints from the current database, preserved unchanged. A removed identity with a dated footprint fails until an explicit evidence-scope decision is made.
- `migration-receipt.json`: exact Node-compatible published footprint hashes, changed/removed/added/reused IDs, one explicit lineage relationship per proposal, all original affected features and chains, retired groups, source evidence, exact per-proposal coverage and seam measurements, exhaustive global overlap lists, and local-record preservation counts/hash.
- `original-source-geometry.json.gz`: all 36 exact original full source features, their source-file and canonical-geometry hashes, plus the original complete OSM relation payload and licensed source receipt.
- `archive.json.gz`: affected original features and chains, retired geographic groups, and complete copies of original local states, attribute records, entity-history rows and boundaries.

Original claims stay on their original IDs and footprint contexts. `history_transfer` is always false. A union does not copy retired-ID population, names, religious distributions, ownership intervals, direct evidence or hosted claims onto the successor. Original historical ownership intervals must be archived by the incremental preparation wrapper; changed-footprint spatial summaries must be rederived, not relabeled. Imported hosted claims require an independent scope check at publication, even when current local direct-record counts are zero.

The original prepared footprint hash is `1c8c1584520d7360375c8ac79f12fe840dd8a47efb10f3d05c8517689667dd58`. The corrected staged hash is `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`. These use the existing native `JSON.stringify`/`localeCompare` contract, not a substituted Python number-formatting contract.

## Incremental preparation and publication

Run the frozen ownership wrapper against these explicit snapshots, retaining the original corpus:

```sh
python scripts/prepare-ownership-incremental.py \
  --before .cache/source-territory-repair-stage/before/world-index.json \
  --after .cache/source-territory-repair-stage/after/world-index.json \
  --before-boundaries .cache/source-territory-repair-stage/before-boundaries.json \
  --after-boundaries .cache/source-territory-repair-stage/after-boundaries.json \
  --receipt .cache/source-territory-repair-stage/migration-receipt.json \
  --ownership data/ownership-history \
  --source data/cliopatria \
  --output .cache/source-territory-repair-stage/ownership-history
```

The source directory above contains the pinned Cliopatria index and source parts; the ownership directory contains its archived executed algorithm receipts. Both paths match the current repository preparation layout. The stage has `geometry_stage_validated: true` after exhaustive checks, but **`publication_ready: false`**: source ownership, environmental summaries, canonical-grid representation, hosted imported claim scope, immutable geographic release staging, static/server consistency and browser gates must still pass before installation or publication.

`--skip-global-audit` is available only for explicitly unvalidated exploratory staging; it never marks the geometry stage validated. It cannot serve as a publication gate.

Run `python test/source-territory-repairs.py`. Twelve focused tests exercise stable identity/archives, no owner-based reparenting, stale original/source rejection, strict existing-footprint unions, exact neighbor-seam conservation, refusal to treat material overlaps as numerical seams, complete parent chains, and global containment/crossing overlap detection.

## Durable Git evidence and cache-free resumption

`data/geographic-repair-evidence/` preserves the lossless compressed migration receipt, the affected original features/claims, all full original source features and OSM payload, dated-footprint inputs and before/after hierarchy snapshots. Its top-level `index.json` pins every archive hash and the decompressed receipt hashes. The original evidence bundle is 1.78 MB, rather than duplicating 404 MB of full raw snapshots.

After the corrected geography is installed in `data`, a fresh checkout can reconstruct both exact footprint snapshots without the old cache:

```sh
python scripts/restore-geographic-repair-stage.py \
  --after data/world-index.json \
  --evidence data/geographic-repair-evidence \
  --output .cache/restored-source-territory-stage
```

The restoration first requires the exact pinned after footprint hash and 49,589 IDs. It then restores all 52 original affected features, including retired IDs, and checks the complete reconstructed 49,614-ID before footprint hash. Every archive hash and original plain receipt hash must match. This full real-dataset reconstruction was executed successfully. An unrelated later geometry revision cannot silently masquerade as this migration; use the matching Git geographic revision before resuming it.

`data/geographic-repair-evidence/ownership-archive/` additionally preserves all **2,268 original intervals** of the 52 changed/retired identities, the original complete ownership index/dictionary, and the exact incremental preparation receipt. Unchanged intervals are not duplicated there: **6,832,396 original intervals** across all 49,562 reused IDs were exhaustively byte-compared and remain in the new ownership corpus. Together the live reused rows and archival rows account for all **6,834,664 original intervals**. The correction derives only **1,441 intervals** for 27 changed footprints, resulting in **6,833,837 current intervals**, without copying any original direct history onto new geography. All 13,378 political source geometries were checked; original evidence dictionary indices are unchanged, with 1,040 evidence tuples appended.

The 51 century transport files were regenerated from the staged ownership index. Independent validation decoded and compared **every one of their 7,411,391 transported interval/evidence tuples** against the 6,833,837 source intervals, including exact original interval endpoints and local evidence-index remapping. All 51 buckets matched. Its durable receipt is `ownership-archive/runtime-validation.json`.

```sh
python scripts/prepare-ownership-runtime.py \
  --source .cache/source-territory-repair-stage/ownership-history \
  --output .cache/source-territory-repair-stage/ownership-runtime
python scripts/validate-ownership-runtime.py \
  --source .cache/source-territory-repair-stage/ownership-history \
  --runtime .cache/source-territory-repair-stage/ownership-runtime \
  --receipt data/geographic-repair-evidence/ownership-archive/runtime-validation.json
python test/ownership-runtime-validation.py
```

Five independent validator tests check complete cross-bucket intervals and reject changed evidence, shortened intervals, missing rows and altered dictionaries even when transport asset checksums are refreshed. Validation receipts prove transport consistency; they do not close geographic semantics, environmental rederivation, grid representation or publication gates.

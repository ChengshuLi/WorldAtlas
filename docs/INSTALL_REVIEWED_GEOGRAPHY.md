# Installing a reviewed geographic generation

`scripts/install-reviewed-geography.mjs` validates a complete geographic/prepared/grid generation. It defaults to a read-only dry run. Supplying `--apply` also requires the exact `--expected-validation` SHA-256 returned by the reviewed dry run. Changed files, scripts or candidate assets invalidate that hash.

```sh
node scripts/install-reviewed-geography.mjs
node scripts/install-reviewed-geography.mjs --apply --expected-validation=REVIEWED_DRY_RUN_SHA256
```

Explicit `--name=path` options are available for `data`, `geography`, `ownership`, `runtime`, `references`, `grid`, `source-receipt`, `macro-receipt`, `grid-audit` and `grid-source-areas`. Defaults select the validated source-territory and macro-boundary stages, their incrementally prepared attributes/ownership, and the approved zoom-10 canonical grid. Source directories must be outside the active data directory. Symlinks, path traversal and staged database files are rejected.

## Validation

The validator checks every active location/group ID, six complete adjacent-tier parents, six continents, nonempty groups and the exact location-footprint/hierarchy hashes. Source and macro migration receipts must match the current baseline and candidate. No historical claim transfer is permitted. The unapproved Namibia replacement is explicitly excluded: all 111 current source identities and their geometry must remain unchanged, with the outstanding source-review reason recorded.

Ownership assets, evidence, archived prior tuples, executed algorithm snapshots and migration identity maps are hash-checked. Every current location has exactly one ownership interval sequence; duplicate identities, overlapping intervals and year zero fail. Reference tuples are validated against immutable category/type indices and unique resolved attribute intervals. The reference migration's original baseline, archive and supported-period receipt are checked. Every bounded runtime bucket must match the exact current ownership index and footprint hash.

Each grid part is hash-checked both before and after byte-shuffle decoding. Decoded row/run sequences must be contiguous, ordered, nonoverlapping and refer to valid current location IDs. Their exact per-location cell counts must equal the exhaustive grid assessment. Every location must have a cell. Grid bounds and province membership must agree with the current parent chain and hierarchy hash. WGS84 grid distortion uses the independently prepared whole-footprint surface areas; zero missing locations does not certify that a source originally included every island.

## Controlled local activation and rollback

Pause local atlas writers, development servers and builds for the short commit. The transaction provides atomic individual filesystem renames with rollback across the complete bounded replacement set. It does **not** provide a single atomic filesystem view to an unrelated concurrent reader. Published Site generations have their own atomic deployment boundary; publish only after the complete local generation and audits pass.

The installer copies validated assets into a temporary generation and verifies copied bytes before moving live paths. It replaces only `geography`, `hierarchy.json`, `world-index.json`, `ownership-history`, `ownership-runtime`, `reference-attributes`, `canonical-grid`, `pixel-audit.json` and `publication-geography-receipt.json`.

The 13 GiB data directory is never copied wholesale. SQLite files, the original hosted source catalog, all independent source archives and other data products stay outside the replacement set. No database connection or historical-record migration is performed. Originals from replaced paths are retained under `.cache/geography-install-backups/<transaction ID>`. A durable journal records each rename; a caught failure restores every original path. Retain this backup until the validated generation is published and its historical/source evidence is durably archived.

An exclusive `data/.geography-install.lock` blocks simultaneous installs. An interrupted process can leave the lock and journal: inspect that journal and the recorded backup before recovering; do not blindly delete the lock or original assets. Successful or automatically rolled-back transactions remove their lock. `data/publication-geography-receipt.json` records old/new counts, complete source hashes, grid representation, Namibia's pending status, the backup and transaction journal.

## Required follow-up gates

After authorized activation, regenerate current reports in this order:

```sh
python scripts/review-framework.py --report-only
python scripts/audit-granularity.py
python scripts/review-world.py
python scripts/review-global-semantic-closure.py
```

The installer generates the current pixel report directly from verified precompiled assets and existing source-area evidence. It does not compile ownership again. The root integration changes the canonical renderer resolution and makes the static builder reuse `data/canonical-grid`; builds and navigation must not recompile this ownership grid.

The six frozen continent source inspections and older regional/source diagnostics retain their original snapshot scopes. Their hashes/counts must never be silently rewritten to suggest they audited later polygons. Updated current reports distinguish structural coverage from independently completed semantics. New or changed footprints remain semantically open until new evidence resolves their questions.

Run `node --test test/install-reviewed-geography.test.mjs`. Tests cover read-only dry runs, exact approval hashes, database/catalog/archive preservation, commit rollback, stale/corrupt products, incorrect grid membership/counts, unsafe paths/symlinks and empty geographic groups.

# Reproducible development and research checkpoint

The primary repository is `https://github.com/ChengshuLi/WorldAtlas`, development branch `work`. A new Codex thread should clone that branch and read `AGENTS.md`, `docs/IMPLEMENTATION_PROGRESS.md`, and `docs/LUNA_DATA_HANDOFF.md` before changing content. The separate Site source repository is a deployment mirror; it is not the research handoff repository.

## Start from Git

```sh
git clone --branch work https://github.com/ChengshuLi/WorldAtlas.git
cd WorldAtlas
npm ci
npm run dev
```

Node 24 or later is required. Prepared geography, sparse dated ownership intervals, environmental references, source manifests, migration archives, and completed dated-name/religion products are tracked. SQLite databases, build output, downloaded caches, local credentials, and dependency directories are intentionally excluded. A fresh local database is created from tracked inputs; existing local imports remain preserved when reopening it.

For geographic preparation, use Python 3.12 and install `requirements.txt` in a virtual environment. Source URLs, source byte hashes, executed algorithms, and restoration commands are retained with each producer. Some source downloads are large; running the website does not require downloading them again. Do not replace a checksum-pinned source with a newer release under the same identity.

## Preserve existing research

`data/ownership-history` and `data/ownership-runtime` contain completed historical political assignments and exact runtime transport. `data/reference-attributes` retains completed environmental references. `data/dated-reference-names` and `data/demographic-evidence` retain completed dated-name and religion evidence. `data/prepared-evidence` supplies validated bounded imports and browser caches for the completed content checkpoint. The original geographic archive and immutable hosted identity catalog must never be regenerated from newer names or parent chains.

The paused GHSL output is retained in `data/interrupted-preparation/ghsl-2020`, with a byte-hash retention manifest. It is explicitly **unvalidated**, excluded from imports and public coverage, and must not be treated as completed population evidence. Its source URLs/hashes and continuation instructions are in `data/population-ghsl/sources.json` and `docs/GHSL_POPULATION_IMPORT.md`.

The reviewed source and macro migrations are installed in Git and published in owner-private Site version 13: **49,589 locations → 5,133 provinces → 471 areas → 66 regions → 29 subcontinents → six continents**, with fixed canonical grid zoom 10. `data/publication-geography-receipt.json` records installation; `data/validation/published-milestone-2026-10-02.json` and production verification record the matching native publication/provisioning. Footprint SHA-256 is `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8`; hierarchy SHA-256 is `bb083958f4ccee3ca1aa4b9d0392433a79c4ebbf023c873168c0900ca4a36d58`. Namibia's replacement remains blocked, so its 111 existing identities/footprints remain in the installed dataset with source-quality annotations.

The complete lossless reversal uses tracked final geography plus tracked receipts, not an old thread's cache:

```sh
python scripts/restore-reviewed-geography.py \
  --final data/world-index.json \
  --evidence data/geographic-repair-evidence \
  --manifest data/geographic-restoration-manifest.json \
  --output .cache/restored-reviewed-geography
```

This creates `baseline/`, `source-stage/before/`, `source-stage/after/`, `macro-stage/before/`, and `macro-stage/after/` with complete hierarchies and immutable record/source archives. It reverses macro properties and groups first, then restores the 52 original source features and original ordered part layout. All 36 original baseline raw file hashes and all 36 source-after raw hashes were checked in the full-data proof. `data/reviewed-geography-restoration-proof.json` and `docs/REVIEWED_GEOGRAPHY_RESTORATION.md` retain the result and newline conventions. The older `restore-geographic-repair-stage.py` is a footprint-oriented source helper; use the reviewed wrapper for a complete reversal across both migrations.

A `.cache` path in a producer document is an output/source-download location, not the durable handoff. Reconstruct reviewed geography with the command above before using an incremental producer's before/after arguments. Native public rasters can be downloaded from their immutable URLs and checked against retained hashes when rederivation is needed; current prepared content runs without them. Namibia's blocked candidate products and original source bytes are retained in `data/retained-geographic-sources/namibia`; do not apply that candidate merely because its local stage has disappeared. All Git evidence manifests, source-quality part hashes, and public evidence paths must match before replaying. Consult the migration documents for unresolved source, semantic, device and publication gates.

The application consumes evidence through stable IDs, sparse supported intervals, and provenance. Add factual content through the existing import contract; do not materialize one row per location per year, fabricate gap-filling records, or modify map geometry as a side effect of content research.

The checkpoint scan found no tracked or eligible untracked implementation file above the Site Git limit of 16 MiB, and none above GitHub's 100 MB file limit. The largest current file is `data/geographic-migration-review.json` at 16,694,976 bytes, only 82,240 bytes below 16 MiB; rerun the size gate after adding research content. Completed product/release manifests and all four public Namibia evidence links were checked for existing matching byte hashes. Local databases, caches, build output and credentials remain excluded from Git.

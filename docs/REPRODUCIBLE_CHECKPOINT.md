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

Staged geographic repairs are separate from the active dataset until their geometry, ownership, environmental summaries, grid, migration preservation, and publication checks all agree. `data/geographic-repair-evidence` contains compact original geometry, affected ownership rows, dated footprint snapshots, hashes, and a restoration manifest. `scripts/restore-geographic-repair-stage.py` reconstructs the source-repair stage from tracked inputs, without relying on a previous thread's workspace. Macro-geographic decisions and the Namibia source review retain their own source bytes and crosswalks. Consult their migration documents for current gate status.

The application consumes evidence through stable IDs, sparse supported intervals, and provenance. Add factual content through the existing import contract; do not materialize one row per location per year, fabricate gap-filling records, or modify map geometry as a side effect of content research.

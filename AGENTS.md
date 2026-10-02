# Agent guidance

## Project context

WorldAtlas is a world-history atlas with stable territorial locations, a six-tier hierarchy, whole-location map modes, sparse dated evidence, and a persistent hosted content API. Read `README.md`, `docs/IMPLEMENTATION_PROGRESS.md`, and `docs/LUNA_DATA_HANDOFF.md` before changing its geography or historical content.

Application code and database content are independent. A factual content import must not require rewriting the UI, rebuilding the canonical grid, or extending an unsupported interval. Preserve completed evidence, original source bytes/hashes, predecessor identities, geometry and immutable records. Do not materialize one record per location per year; represent supported half-open intervals, with no year zero.

Separate continuation queues: `docs/ENGINEERING_TODO.md` belongs to technical maintainers; `docs/HISTORICAL_RESEARCH_TODO.md` belongs to Luna content-research threads. Read and update the queue matching your scope, plus `docs/HANDOFF_STATUS.md`. Content research must not silently undertake engineering or geographic release installation.

Geographic structure lives in `data/world-index.json`, its parts and `data/hierarchy.json`; completed sparse products have independent manifests. `src/attributes.js` and `src/temporal.js` are shared resolvers; `hosted/` implements the content service; `drizzle/` contains immutable deployed schema migrations. Never regenerate `data/hosted-catalog` from current names/parents: it is the original identity registry. Geographic revisions use explicit release/crosswalk evidence. Antarctica is excluded and EU5 counts are scale references, not quotas.

The primary handoff branch is `work` in `ChengshuLi/WorldAtlas`. The Site source repository is a separate deployment mirror. Do not assume a new thread can access `.cache`, SQLite databases or another thread's workspace. Durable research/checkpoints and resume instructions must be committed to the primary repository; credentials and local dependency/cache directories must not be committed.

## Working in this repository

- Keep changes focused on the requested work.
- Keep each pull request below 1,000 changed lines, excluding test changes.
- Follow conventions established by the code and documentation as they appear.
- Update relevant documentation when a change affects how the project is used or developed.
- Avoid introducing dependencies or tooling unless the task calls for them.

## Verification

- Use the validation commands defined by the project when they exist.
- If no relevant validation command exists, say what you checked and what remains unverified.
- Do not report checks as passing unless you ran them.
- `npm ci` and `npm run dev` run the committed prepared atlas on Node 24. Python preparation dependencies are pinned in `requirements.txt`.
- `docs/STRUCTURAL_VALIDATION.md` and `scripts/validate-structure.mjs` define contract, scientific, publication, browser and content-only verification phases. Match prepared products, grid, release and build before publication tests; source checks do not establish semantic or historical completion.

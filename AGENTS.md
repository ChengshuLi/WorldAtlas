# Agent guidance

## Project context

`docs/THREE_THREAD_START.md` links the three role handovers/prompts. M engineering and N history workers use `docs/WORKER_COORDINATION.md`: claim one ready 1–3-PR work item with a unique worker ID before implementation; umbrellas cannot be claimed. Use the serialized worker merge queue and one designated Site publisher. New location-attribute imports require globally approved continent/subcontinent/region boundaries and the target region's complete published branch certificate, exact subjects and release pins; none are approved yet. Follow `docs/TOP_DOWN_GEOGRAPHY_WORKFLOW.md`; current research is source-only. Issue creation updates GitHub Issues only; engineering and history-research workers use their isolated lane branches and continue through their queues.

WorldAtlas is a world-history atlas with stable territorial locations, a six-tier hierarchy, whole-location map modes, sparse dated evidence, and a persistent hosted content API. Read `README.md`, `docs/IMPLEMENTATION_PROGRESS.md`, and `docs/LUNA_DATA_HANDOFF.md` before changing its geography or historical content.

Application code and database content are independent. A factual content import must not require rewriting the UI, rebuilding the canonical grid, or extending an unsupported interval. Preserve completed evidence, original source bytes/hashes, predecessor identities, geometry and immutable records. Do not materialize one record per location per year; represent supported half-open intervals, with no year zero.

GitHub Issues is the single source of truth for TODOs, status and dated work history. Use exactly one `type:engineering` or `type:history-research` label for current lanes; future types may add labels and ownership rules. Keep closed issues, original raised/recorded/completed dates and evidence; human dates use America/Los_Angeles. Unknown earlier dates remain unknown. `docs/ENGINEERING_HANDOFF.md` and `docs/HISTORY_HANDOFF.md` remain instruction entry points, with copy-ready prompts under `docs/prompts/`. The `_TODO.md` files retain acceptance guidance, not live task lists. Original trackers are immutable archives.

Concurrent work uses isolated checkouts and unique `engineering/<job-id>` or `research/<campaign-id>` branches from fresh `origin/main` for each PR. Research owns only its campaign directory; engineering preserves research directories and other jobs' execution artifacts. Read `docs/PARALLEL_WORK_PROTOCOL.md` and run `scripts/check-handoff-scope.mjs` with the PR body before submitting. Each focused PR addresses one GitHub issue or a part of it. Large issues may have multiple PRs or linked child issues. Use exactly one `Refs #N` line for partial work or `Closes #N` only when all acceptance criteria are satisfied. Update progress/blockers/evidence on the issue, not shared TODO documents. Integrate verified PRs serially with squash merges, explicitly using the PR title as squash commit title. After every merge, branch afresh from updated main. Keep the already merged initial foundation PR's original history. Normal merges do not deploy or invoke provider-management migrations.
Geographic structure lives in `data/world-index.json`, its parts and `data/hierarchy.json`; completed sparse products have independent manifests. `src/attributes.js` and `src/temporal.js` are shared resolvers; `hosted/` implements the content service; `drizzle/` contains immutable deployed schema migrations. Never regenerate `data/hosted-catalog` from current names/parents: it is the original identity registry. Geographic revisions use explicit release/crosswalk evidence. Antarctica is excluded and EU5 counts are scale references, not quotas.

The primary handoff branch is `main` in `ChengshuLi/WorldAtlas`; `work` retains the initial development history. The Site source repository is a separate deployment mirror. Do not assume a new thread can access `.cache`, SQLite databases or another thread's workspace. Durable research/checkpoints and resume instructions must reach the primary repository through their issue PRs; credentials and local dependency/cache directories must not be committed.

## Working in this repository

- Keep changes focused on the requested work.
- Keep each future pull request below 1,000 changed lines, excluding test changes. The user explicitly permits the initial work-to-main foundation PR to exceed this limit. One GitHub issue or part of it per PR; retain dated progress, evidence and closed issues.
- Follow conventions established by the code and documentation as they appear.
- Update relevant documentation when a change affects how the project is used or developed.
- Avoid introducing dependencies or tooling unless the task calls for them.

## Verification

- Use the validation commands defined by the project when they exist.
- If no relevant validation command exists, say what you checked and what remains unverified.
- Do not report checks as passing unless you ran them.
- `npm ci` and `npm run dev` run the committed prepared atlas on Node 24. Python preparation dependencies are pinned in `requirements.txt`.
- `docs/STRUCTURAL_VALIDATION.md` and `scripts/validate-structure.mjs` define contract, scientific, publication, browser and content-only verification phases. Match prepared products, grid, release and build before publication tests; source checks do not establish semantic or historical completion.

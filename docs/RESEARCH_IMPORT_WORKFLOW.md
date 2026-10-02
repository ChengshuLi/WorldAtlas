# Research and content imports without application changes

**Current research policy (2026-10-02 America/Los_Angeles):** source-only until complete worldwide hierarchy review and matching engineering approval. New location-attribute imports are blocked; local staging and dry runs may proceed. Use [WORKER_COORDINATION.md](WORKER_COORDINATION.md) for reservations and [GEOGRAPHY_RESEARCH_READINESS.md](GEOGRAPHY_RESEARCH_READINESS.md) for the global gate. Older descriptions of enabled live transport below describe capabilities, not permission to bypass this policy.

This workflow is for Luna researching evidence and adding content to existing locations. It requires structured data files and existing commands, not changes to application code, schema, grid or website deployment. Root remains responsible for engineering, geographic footprint migrations and capacity upgrades. Sparse supported intervals represent evidence; do not generate a row for every year or fill unsupported gaps.

Start from branch `main` of `ChengshuLi/WorldAtlas`, create an isolated `research/<campaign-id>` branch under [the parallel protocol](PARALLEL_WORK_PROTOCOL.md), run `npm ci` with Node 24, and read `docs/LUNA_DATA_HANDOFF.md`, `docs/ATTRIBUTE_CONTRACT.md` and `docs/ENVIRONMENT_CLASSIFICATIONS.md`. Obtain the current published release using `GET /api/geography/release` through the existing private Site access and save its JSON response as `geographic-release.json`. Preserve stable location/category/entity IDs; names are labels. Current geographic membership is reference context unless separately dated evidence establishes otherwise.

## Prepare a research collection

Create `research.json` containing arrays named `sources`, `entity_types`, `entities`, `categories`, `records`, `names`, `retirements`, `relationships` or `media_links`. Only include collections needed for this research. Sources/categories/identities already present in the service can be referenced by ID. This workflow cannot add geographic locations, change footprints or redefine geographic tiers. People, events, armies, routes and other nongeographic graph subjects can use existing types or sourced new type definitions. Media links reference already uploaded immutable objects; media uploads remain a separate bounded API operation.

Each claim needs a stable ID, source ID, valid supported interval and disclosed method/uncertainty. Read the handoff contract for the exact fields. Negative years are BC, year zero is forbidden, and intervals are `[valid_from, valid_to)`; `2027` is only an exclusive endpoint. Examples stay explicitly opt-in. Unknown values use `null`. Fixed environmental classification IDs are listed in the classification guide and `/api/classifications`.

Compile with one command:

```sh
node scripts/prepare-research-bundle.mjs research.json geographic-release.json research-bundles/campaign-001
```

The compiler preserves the exact original input, pins release/footprint/hierarchy hashes, checks input source bounds and classifications, orders dependencies and emits content-addressed batches of at most 200 rows and 1 MiB. A retirement and its submitted replacement remain in one transaction; original evidence is retained. Multiple retirements sharing one replacement stay together, and chained corrections commit in dependency order. An atomic correction group larger than the batch budget is rejected for review rather than split unsafely.

Local preflight validates syntax, controlled classifications, input-source interval/method consistency and immutable bytes. It does **not** establish historical truth, source licensing, identity matches, existing service conflicts or source completeness. The hosted service remains authoritative for identities, constraints, conflicts and transactional acceptance. Missing externally referenced identities/sources fail at import; do not invent identities to suppress the error. Do not widen original evidence periods to fill gaps.

Optionally supply a fourth argument pointing to a JSON list of licensed source files:

```json
[
  {"path":"sources/census.csv","source_id":"source:existing-stable-id","license":"CC BY 4.0","redistribution_permitted":true}
]
```

Paths resolve relative to `research.json`. Copies are preserved by SHA-256 in `source-files/`, with original basename, bytes, source ID and license. `redistribution_permitted:true` is an explicit researcher assertion, not automated license verification. Restricted materials must not be included; preserve their lawful URL/version/hash and research notes instead. This option does not upload source archives or bypass the media endpoint's 20 MiB limit. Large archives need suitable licensed object storage and a restorable Git manifest; do not exceed repository/hosting file limits.

## Validate, import and resume

Perform a network-free dry run:

```sh
node scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001 --dry-run
```

Import with one command:

```sh
node --use-env-proxy scripts/import-research-bundle.mjs https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ research-bundles/campaign-001
```

Supply the private service credential JSON through the hidden terminal prompt. Never put credentials in command arguments, environment dumps, files, notes, receipts or Git. Keep the existing owner-private audience. The importer verifies current published geography before any write, checks all input/batch/archive hashes, and retries transient/network failures up to four attempts using the same stable ingestion identity. A conflicting claim or changed geography stops the campaign for review.

`import-receipts.json` is atomically saved after every committed batch, including before an eventual failure. Rerun the identical command to resume; completed receipt entries are skipped. A lost response can be safely retried because server ingestion IDs are idempotent. Never edit a completed bundle or reuse its IDs for different evidence. Corrections require a new sourced immutable claim and a sourced retirement, preserving the original. Choose a new output directory for revised research.

Receipts establish accepted transactions, not independent factual or exhaustive read-back verification. Check new claim IDs through `/api/evidence/records/{claim_id}` or `/api/evidence/names/{claim_id}` and inspect the corresponding year/location on the Site. Verify map fills and inspector agree, gaps remain unknown, aliases do not create new identities, and original evidence is accessible. The existing published-checkpoint verifier covers its prepared checkpoint; it is not a verifier for every arbitrary future campaign.

## Preserve progress for the next research thread

Keep input, generated manifests/batches, licenses/hashes, lawful source bytes/restoration manifests, receipts and findings inside `research/campaigns/<campaign-id>/`. Post dated milestones, coverage, blockers and evidence on the linked GitHub issue. Keep closed issues as history; do not edit shared handovers. Push `research/<campaign-id>` and open a PR targeting **main**. Maintainers integrate serially and update global summaries. Do not commit credentials or dependency/cache/SQLite directories. A fresh thread must be able to recover the research from Git and licensed source locations without access to this workspace.

This workflow has bounded batches; it does not promise that one managed database supports billions of claims. The current compiler reads a campaign into memory; divide large research campaigns into manageable input collections. Sparse evidence intervals and stable APIs avoid materializing the conceptual location × year × attribute grid. Root owns measured query/storage capacity, compact map delivery and future partitioning. Stop on explicit service capacity errors and preserve the partial ledger; do not redesign infrastructure in a research-only thread.

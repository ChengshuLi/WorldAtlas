# Start a content-only Luna research thread

**Current research policy (2026-10-02 America/Los_Angeles):** source-only until complete worldwide hierarchy review and matching engineering approval. New location-attribute imports are blocked; local staging and dry runs may proceed. Use [WORKER_COORDINATION.md](WORKER_COORDINATION.md) for reservations and [GEOGRAPHY_RESEARCH_READINESS.md](GEOGRAPHY_RESEARCH_READINESS.md) for the global gate. Older descriptions of enabled live transport below describe capabilities, not permission to bypass this policy.

For the current one-document/one-prompt workflow, use [HISTORY_HANDOFF.md](HISTORY_HANDOFF.md) and [LUNA_HISTORY.txt](prompts/LUNA_HISTORY.txt). These provide research instructions and concurrent branch rules; GitHub Issues holds the authoritative TODOs and dated work history. Engineering uses its separate [handover](ENGINEERING_HANDOFF.md).

Clone `https://github.com/ChengshuLi/WorldAtlas`, branch **main**. This is the durable handover; no prior workspace or `.cache` is required. The website is https://worldatlas-explorer.chengshu-li-2013.chatgpt.site/ and retains its owner-private audience.

Read, in order:

1. `AGENTS.md`.
2. `docs/HANDOFF_STATUS.md` and `data/validation/neon-final-publication.json` for the actual deployed state and open work.
3. `docs/LUNA_DATA_HANDOFF.md` and `docs/RESEARCH_IMPORT_WORKFLOW.md` for content campaigns.
4. `docs/ATTRIBUTE_CONTRACT.md` and `docs/ENVIRONMENT_CLASSIFICATIONS.md` before preparing attributes.
5. `docs/RESEARCH_MEDIA_WORKFLOW.md` when retaining licensed archives or linked media.

## Scope

Research sources and prepare/import historical names, aliases, ownership evidence, population, primary culture/religion, habitation, rank, topography, vegetation and climate. Events, people, places, armies, routes, artifacts, relationships and linked media use the existing generic entity contracts. Detailed new domain interfaces remain future engineering work.

Do not edit application code, schema, UI, infrastructure, source policies, geographic releases or the canonical grid. Keep stable identities and preserve original evidence. The platform accepts sourced dated parent membership/existence; that does not authorize changing reference geography or publishing new footprints. The browser currently advertises `datedFootprints:0`.

Use sparse supported intervals, not annual location snapshots. A supported 500-year fact is one interval claim. Unsupported years stay unknown. Modern references and settlement estimates must not silently become historical location facts. Primary culture/religion require the source's warranted interpretation; no fabricated population shares. Rank `unsettled` requires supported absence of inhabitants.

**Environmental timeline TODO:** research supported intervals and actual changes for the three fixed classifications. Current raw evidence gaps in 2025 do not establish a sudden physical change; the UI already supplies separately labeled present-day physical reference context. Do not widen source dates just to remove Unknown.

## First campaign

- Inspect current `/api/geography/release`, capabilities, `/api/storage/capacity` and existing source/entity catalogs. Save the exact geographic release and reuse stable IDs.
- Choose a bounded, well-sourced geography/time/attribute campaign. Retained completed evidence is listed in `docs/LUNA_DATA_HANDOFF.md`; do not restart or discard it.
- Prepare ordinary factual JSON and lawful source bytes or documented restoration manifests. Compile and validate with the existing scripts; use their documented network-free dry run before importing.
- Authenticate through the documented private Site mechanism with hidden input. Credentials belong in server secrets, never chat or Git. GitHub's `NEON_API_KEY` is an Actions management credential, not a research-import token.
- Import bounded content-addressed batches. Verify returned claim IDs, source intervals, selected-year values and receipts. Save progress even if a campaign is interrupted; retain complete original input and hashes.
- Commit and push source notes, inputs, bundles, receipts, coverage and open questions on your own `research/<campaign-id>` branch before ending; open a PR to **main** and post dated progress and evidence on the GitHub issue. Do not commit credentials, local databases or caches.

The production platform is writable and has preserved its existing 3,984 historical claims and 28 archives. All 22 retained prepared batches replayed without changing revision 1321 or its snapshot fingerprint. Future successful imports will advance that revision; it is not a fixed requirement for new research.

## Separate maintainer queue

Research can continue independently of the documented open engineering/geographic work: dated-footprint browser/cache integration, installation of three validated hierarchy candidates, blocked source repairs and complete geographic semantic approval, physical mobile validation and measured scaling beyond the current capacity envelope. Do not silently assume these are complete or undertake them as historical-content expansion. Report a campaign blocker with its pinned inputs and receipt so a technical maintainer can resolve it.

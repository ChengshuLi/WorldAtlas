# Historical research TODO — Luna content threads

This is the source-research and dataset-content queue. Follow [LUNA_START_HERE.md](LUNA_START_HERE.md), [LUNA_DATA_HANDOFF.md](LUNA_DATA_HANDOFF.md) and [RESEARCH_IMPORT_WORKFLOW.md](RESEARCH_IMPORT_WORKFLOW.md). Engineering has a separate owner and queue in [ENGINEERING_TODO.md](ENGINEERING_TODO.md). Do not edit code, schema, UI, infrastructure, reference geography or grid assets to complete a research campaign.

The platform is writable. Existing ownership/environmental products, 3,588 dated names, 396 religion records, 9,301 separate-settlement estimates and original archives are retained. Preserve and extend them. Interrupted GHSL output is unvalidated; it is not a completed import. Existing dated evidence covers particular supported intervals, not every year.

Choose bounded source/geography/time/attribute campaigns. Research all six inhabited continents systematically; maintain explicit coverage and open questions rather than repeatedly selecting only earlier regression examples. Store sparse supported intervals with stable IDs, per-attribute provenance, original hashes, license and uncertainty. Do not generate annual rows, invent missing facts or widen modern observations to ancient dates.

## RES-01 — source inventory and campaign coverage

- [ ] Discover reusable public sources by geography, attribute and supported interval; assess license, vintage, precision, spatial unit and uncertainty before importing.
- [ ] Inspect current sources/entities, release pins, capabilities and capacity. Reuse identities; verify fresh-thread private API access through documented hidden authentication.
- [ ] Select and document the next bounded campaign, including its uncovered territory/time/attributes and justified limitations. Continue incomplete campaigns using their retained inputs and receipts.

## RES-02 — historical names and aliases

- [ ] Research dated preferred names and aliases at every geographic tier, preserving language, source and supported intervals.
- [ ] Keep stable entity IDs through renames. Never rename reference geography or create a new location solely because its label changed. Unsupported historical names remain unknown; the existing UI handles present-day reference context.

## RES-03 — ownership evidence

- [ ] Extend or improve historical ownership using direct sourced location evidence and explicit uncertainty, without discarding the existing prepared reconstruction.
- [ ] Preserve stable polity/category IDs and precedence over derived evidence. Retain dated boundary collections as source evidence for maintainer preparation when spatial assignment is needed; do not write new geographic algorithms or paint independent polygons.

## RES-04 — population, habitation and rank

- [ ] Research censuses, demographic reconstructions and settlement histories. Mark modeled values as estimates, preserving supported precision, method and territorial scope.
- [ ] Keep settlement estimates separate from location totals. Do not infer population or rank solely from a modern administrative label.
- [ ] Research habitation and rank separately. Use `unsettled` only with evidence of no inhabitants; unknown habitation must not become rural settlement.
- [ ] Inspect retained GHSL sources/intermediate results before resuming; import only validated, correctly scoped products. If producer/code changes are required, record the blocker for a maintainer.

## RES-05 — primary culture

- [ ] Research supported population distributions or warranted primary-culture attestations with dated culture identities and source qualifications.
- [ ] Determine primary culture from supported population shares where available. Do not substitute geographic area shares unless the source warrants that interpretation, or fabricate shares from broad cultural labels.

## RES-06 — primary religion

- [ ] Extend the retained observation-year census evidence using supported historical/census sources and stable religion identities.
- [ ] Preserve source denominators, mixed/uncertain cases and observation dates. Primary religion requires the source's warranted interpretation; settlement religion is not automatically location-wide religion.

## RES-07 — environmental timeline coverage

- [ ] Research documented terrain, river and coastal changes for topography; historical land use/cover for vegetation; and dated observations/reconstructions for climate.
- [ ] Use the existing fixed classifications; preserve original source wording and uncertainty in metadata. Report an unsupported category to a maintainer instead of changing the registry.
- [ ] Investigate evidence gaps such as 2025 without widening original records just to remove Unknown. The UI already separates labeled physical reference context from historical assertions; potential natural vegetation is not historical land cover.

## RES-08 — sourced memberships and existence

- [ ] Research dated parent membership and identity existence when sources support them, using the published `temporal_geography` contract and documented atomic campaign phases.
- [ ] Keep reference labels distinct from dated administrative claims. A membership record does not establish changed historical land geometry. Flag required splits/merges/new footprints for the maintainer; browser footprint support remains `datedFootprints:0`.

## RES-09 — interconnected historical subjects and media

- [ ] As later campaigns require, research people, events, places, armies, routes, artifacts and sourced relationships using existing generic identities and import collections.
- [ ] Retain lawful images/audio/source archives with hashes, licenses, attribution and supported links/intervals through the existing media workflow (currently 20 MiB per object). New domain interfaces, geometry infrastructure or larger-file transport belong to engineering.

## Completion and continuity for every campaign

A campaign is complete only for its explicitly documented scope: validated source input, accepted bounded imports, preserved receipts, claim/source/interval read-back, selected-year checks and recorded remaining uncertainty. A successful import is not proof of historical truth or global coverage.

Commit and push **work** with research notes, lawful source bytes or restoration manifests, immutable input/bundles, partial and final import/read-back receipts, coverage achieved and next action. Update this queue and `docs/HANDOFF_STATUS.md`; record campaign IDs/paths rather than checking off an entire worldwide attribute after one batch. On capacity, identity, release-pin or unsupported-contract errors, retain progress and report the blocker to the maintainer. Do not redesign the platform.

# Geography readiness for concurrent historical research

The atlas has a published, versioned six-tier reference foundation. Luna can use its existing IDs, footprints and parent chains for source research without designing geography. **The user requires complete worldwide hierarchy review before any new location-attribute imports.** Worldwide geographic semantic review is still unfinished, so new location-attribute imports are blocked everywhere. Source research, evidence preservation and local staging can proceed concurrently with engineering.

This document is a readiness contract, not a live task queue or new automated validator. GitHub Issues holds scope decisions, dependencies, claims and progress. Start with [HISTORY_HANDOFF.md](HISTORY_HANDOFF.md), [RESEARCH_IMPORT_WORKFLOW.md](RESEARCH_IMPORT_WORKFLOW.md) and [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md).

## Recorded reference foundation

The committed live verification receipt [neon-final-api-writable.json](../data/validation/neon-final-api-writable.json), checked at `2026-10-02T07:05:44.864Z` (2 October UTC; 1 October in America/Los_Angeles), records Site 18 using this published reference:

| Item | Recorded value |
| --- | --- |
| Release ID | `geography:review:44acd708dd8aae06e3643b252faf91c04c49b54bb93b705a8c4662ec8568755a` |
| Version | `2` |
| Reference calendar label | `2026-10-01` |
| Footprints SHA-256 | `5d7236fe7e9d2f83c07c0b5cc1d5e703bf685f860fd49c850edd18eea27c61a8` |
| Hierarchy SHA-256 | `bb083958f4ccee3ca1aa4b9d0392433a79c4ebbf023c873168c0900ca4a36d58` |
| Active chain counts | 49,589 locations → 5,133 provinces → 471 areas → 66 regions → 29 subcontinents → 6 continents |
| Content capabilities | `mapSnapshots: 1`, `datedGeography: 1`, `datedFootprints: 0`, `storageExport: 2` |

The prepared definition is [release-2.json](../data/geographic-releases/release-2.json); the installed generation is evidenced by [publication-geography-receipt.json](../data/publication-geography-receipt.json). The reference is undated geographic context, not a claim that these administrations, names or borders existed in every historical year. Antarctica is excluded.

These receipts record past verification. After the worldwide approval gate below is satisfied, every new import campaign must read the actual current `/api/geography/release` and capabilities through its authorized private Site access, save the exact response, and verify the matching released IDs and assets. Private credentials and a writable service do not authorize bypassing the worldwide approval gate. A fresh chat cannot inherit another workspace's private credentials. Public research can begin without those credentials.

## What remains unfinished

[global-semantic-closure.json.gz](../data/global-semantic-closure.json.gz) explicitly reports `audit_complete: true`, `structural_complete: true`, and `semantic_complete: false`. Its complete-unique-chain, valid-footprint and nonoverlapping-interior checks support all 49,589 current locations. Its independent local-purpose and source-island-completeness checks remain open for all 49,589 locations. All 5,705 parent-group overall outcomes remain open. This means the inventory is exhaustive; it does not mean every existing territory is unusable or that every geographic question has been approved.

The separate [geographic-semantic-followup.json](../data/validation/geographic-semantic-followup.json) verifies inventory/provenance consistency across six continental reports, with `semantic_complete: false`, `approvals_created: 0`, and `corrections_installed: 0`. Its readable findings are under [semantic-followup/](semantic-followup/). [GLOBAL_SEMANTIC_CLOSURE.md](GLOBAL_SEMANTIC_CLOSURE.md) explains measured triggers and individual source-backed closure requirements.

Concrete engineering dependencies include:

- Prepared Monaco/Luxembourg grouping and West Virginia duplicate-province corrections are validated candidates, awaiting coherent installation/publication. See [REFERENCE_HIERARCHY_CORRECTIONS.md](REFERENCE_HIERARCHY_CORRECTIONS.md) and [ENGINEERING_TODO.md](ENGINEERING_TODO.md).
- Namibia's 111 existing locations retain an open source-quality guard. The candidate 107-constituency replacement has unresolved neighbor/source-land differences; it must not be imported as approved geography. See [NAMIBIA_REPAIR_MIGRATION.md](NAMIBIA_REPAIR_MIGRATION.md).
- Local/urban purpose, mixed source roles, weak parent correspondence, repeated tiers, island/source-land completeness and geographic boundary conventions remain individually open worldwide.
- Historical footprint browser/version/cache integration is not published (`datedFootprints: 0`). Published dated membership/existence support uses existing released location footprints; it cannot manufacture an historical footprint.

The documented platform handover supplies tools for supported content work. It does not establish final worldwide geography or lift the user's import pause. Geographic review/correction work belongs to engineering; Luna may retain source findings and link the affected engineering issue.

## Mandatory worldwide approval before location-attribute imports

Every location-attribute import issue must depend on [worldwide semantic review issue #7](https://github.com/ChengshuLi/WorldAtlas/issues/7). No new owner, population, culture, religion, rank, topography, vegetation or climate claim may be imported for any location until all of these conditions hold:

1. Issue #7 is completed with retained evidence of complete worldwide hierarchy/semantic review, including every current location and parent branch.
2. The closure evidence reports `semantic_complete: true` and matches the actual published reference release, hierarchy and footprint pins. A true result for an older or staged generation is insufficient.
3. Engineering has accepted and published the reviewed generation, retained its approval/publication evidence, and verified matching served assets, memberships and hashes.

An individual approved location, continent, source profile or compatible source claim cannot lift this global pause. Structural success, a writable Site, an accepted schema or a local compiler pass cannot lift it either. Preserve existing live facts and completed evidence; the pause concerns new location-attribute imports.

While the gate is closed, Luna can collect sources, preserve lawful original bytes and notes, identify subjects, prepare factual JSON and run local preparation/dry runs. Mark these campaigns source-only or staged, preserve their provisional release pins, and leave their imports blocked on #7. Before later importing, recheck the approved current release and let engineering revalidate any earlier staged evidence whose geographic context changed.

## Gate each bounded content campaign

After worldwide approval, the following per-campaign conditions still apply before marking an issue ready for imports. Source-only workers may record this evidence provisionally while #7 remains open:

1. **Released subjects:** exact release ID, hierarchy/footprint pins, stable entity IDs, their active memberships and reference footprint/source-member meaning. Use IDs to resolve ambiguity; equal place names do not establish equal entities.
2. **Bounded evidence scope:** geography/subjects, half-open time interval, attributes, source collection/version/license, and existing claim/import receipts checked for overlap. Identify whether the source describes a whole territory, a settlement, a historical jurisdiction, a subgroup or a sampled population.
3. **Territorial compatibility:** cite evidence that the source's spatial denominator and subject match the intended claim. A direct location population total requires the location's territory; a settlement estimate remains settlement evidence. Culture/religion claims require supported population denominators or the source's warranted primary interpretation. Broad labels, current names, nearest centroids and area shares do not establish these matches.
4. **Geography dependencies:** retain the mandatory #7 dependency and engineering approval evidence. If a source additionally needs an unresolved historical split, merge, replacement, boundary or identity decision, link a bounded engineering issue and leave that claim unimported until resolved.
5. **Supported transport:** after worldwide and campaign gates pass, compile with the existing tools, retain original bytes/pins, run the dry run, import only with authorized private access, retain partial receipts, and verify claim/source/interval and selected-year read-back. Existing compiler/API checks enforce structure and release consistency; they cannot automatically prove territorial compatibility or historical truth.

Use these outcomes when selecting the next issue:

| Outcome | Worker action |
| --- | --- |
| Ready for source research/staging | Research, preserve sources/notes and prepare local evidence now; every new location-attribute import remains blocked on #7. |
| Blocked on additional geography | Preserve evidence and link #7 plus the specific engineering dependency; continue other source-only research. |
| Ready for location-attribute imports | Available only after complete worldwide approval, matching published pins, engineering acceptance, campaign territorial compatibility and private access are verified. |

Campaigns may have complete source evidence while still being blocked for imports. Local readiness does not override worldwide approval. After that approval, import only individually verified compatible claims and preserve remaining questions explicitly; worldwide geography approval does not establish whole-world historical content coverage.

## Example: London in 1567

The current location `atlas:city:GBR-Greater London` is a modern metropolitan-territory reference formed from 33 source members. The committed closure record describes about 1,580.897252 km² and this adjacent-tier chain:

`London → Greater London province → London and South East England area → Britain region → Northern Europe subcontinent → Europe continent`.

Luna takes that released identity and chain as reference context. It does not choose a different province or redraw the boundary. This location's semantic outcome remains open, including local purpose, urban-role and source-vintage questions; its modern aggregation is not itself evidence for 1567.

A source saying “London population in 1567” may describe a historical settlement or jurisdiction within the modern footprint. Its number cannot automatically become the whole modern reference-location population, and its religion/culture cannot automatically become a whole-location scalar. Retain the source's exact subject, denominator and uncertainty, including any existing independently identified settlement subject. Historical boundary creation/rendering requires engineering. Even an explicitly compatible whole-territory claim remains staged until complete worldwide approval; after approval it may supply that field without redesigning the hierarchy.

Thus “fill London's 1567 fields” is a valid research goal, but unknown fields may remain when sources cover different territory or dates. A fixed reference hierarchy removes geography design from Luna's duties; it cannot remove the need to interpret a source's historical subject.

## Coordinate engineering changes with active research

Routine code/UI work and disjoint source-only research/staging can proceed together while location-attribute imports wait for worldwide approval. A geography engineer must identify affected IDs, ancestor/descendant groups, old/new footprint/hierarchy pins, proposed crosswalk and maintenance window on the engineering issue. Record links to affected active research issues before publication. Preparing a candidate does not change the research foundation.

Release publication and imports use the existing serialized database contract. When a new current release changes the pinned campaign context, the importer stops obsolete new batches. Preserve the old input, bundle and committed receipts; continue independent public research. Engineering supplies explicit before/after revalidation or a supported new subject/release decision. Researchers must not edit completed bundle bytes, silently repin, or transfer claims onto a replacement identity. Higher-tier name evidence additionally requires unchanged descendant IDs and geometries for reuse. See [LUNA_DATA_HANDOFF.md](LUNA_DATA_HANDOFF.md), [GEOGRAPHIC_RELEASES.md](GEOGRAPHIC_RELEASES.md) and [GEOGRAPHIC_RELEASE_VALIDATION.md](GEOGRAPHIC_RELEASE_VALIDATION.md).

M engineering chats and N source-only history-research chats can start concurrently with isolated branches and bounded disjoint scope. They share integration and source/identity contracts. Every location-attribute import depends on completed worldwide review #7, matching published semantic approval and engineering acceptance. Their number is not a guarantee of available ready issues, private access, service capacity, or complete independence. Researchers prepare evidence while engineering finishes the hierarchy; importing location attributes starts only after the global gate passes.

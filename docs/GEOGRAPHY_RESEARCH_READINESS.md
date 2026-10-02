# Geography readiness for concurrent historical research

**Current policy supersedes the earlier worldwide full-hierarchy pause:** approve continent, subcontinent and region boundaries globally, then release each complete regional branch independently for location-attribute research/imports. Luna never designs boundaries or hierarchy. See [TOP_DOWN_GEOGRAPHY_WORKFLOW.md](TOP_DOWN_GEOGRAPHY_WORKFLOW.md) for the dependency order and bounded worker scopes.

**No macro partition or regional branch is currently approved for this policy.** New location-attribute imports remain closed. Source collection, lawful evidence preservation and provisional staging can continue, but source-only work does not establish a location's territorial meaning. This document is a contract; GitHub Issues holds current claims, progress, dependencies and completion evidence.

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

These receipts record past verification. After the macro and regional approval gates below are satisfied, every new import campaign must read the actual current `/api/geography/release` and capabilities through its authorized private Site access, save the exact response, and verify the matching released IDs and assets. Private credentials and a writable service do not authorize bypassing those approval gates. A fresh chat cannot inherit another workspace's private credentials. Public research can begin without those credentials.

## What remains unfinished

[global-semantic-closure.json.gz](../data/global-semantic-closure.json.gz) reports `audit_complete: true`, `structural_complete: true`, and `semantic_complete: false`. All 49,589 locations have complete unique chains and checked footprints; local-purpose and source-island-completeness checks remain open for all of them. All 5,705 parent-group overall outcomes remain open. Inventory/structural completion does not mean semantic approval.

[geographic-semantic-followup.json](../data/validation/geographic-semantic-followup.json) records zero follow-up approvals/corrections and unfinished semantics. Earlier macro corrections are retained separately; this is not a claim that no geographic work occurred. The older [MACRO_BOUNDARY_CONVENTION.md](MACRO_BOUNDARY_CONVENTION.md) records 20 supported reporting conventions and 15 open own-boundary reviews, 78 unresolved crossing locations and four open physical/island segments. Its 49,614-location generation must be reconciled with the current release before approval.

Prepared Monaco/Luxembourg and West Virginia corrections await coherent installation. Namibia's candidate replacement remains blocked by neighboring-source conflicts. Worldwide local/urban purpose, mixed source roles, repeated tiers, missing land/islands and boundary conventions remain open. Published `datedFootprints: 0` means dated membership support cannot manufacture historical footprints. See [GLOBAL_SEMANTIC_CLOSURE.md](GLOBAL_SEMANTIC_CLOSURE.md), [REFERENCE_HIERARCHY_CORRECTIONS.md](REFERENCE_HIERARCHY_CORRECTIONS.md) and [NAMIBIA_REPAIR_MIGRATION.md](NAMIBIA_REPAIR_MIGRATION.md).

## Required approval before location-attribute imports

Engineering records approval in [research-geography-gate.json](../data/research-geography-gate.json) only through a reviewed PR with independently retained evidence. Version 2 retains `macro_boundaries` and `regions` certificates; both currently have no approvals. Content work items declare `region_ids` and a scope manifest; regional certificates list `approved_location_ids` and `approved_subject_ids` against exact `approved_release` pins. Three layers are required:

1. **Global macro approval:** all six continents, every subcontinent and every region have approved own boundaries/associations and reconciled shared edges, tied to a published release. This does not approve their descendants.
2. **Regional branch approval:** the target region's entire area → province → location branch is reviewed, corrected or justified, validated and published. Its certificate names its stable region ID, exact permitted subject IDs, release/hierarchy/footprint pins, completed approval issue and retained evidence. An approved outer envelope alone cannot authorize London's attributes.
3. **Bounded campaign approval:** the work item names its region, exact subjects, source collection, supported interval and attributes, plus source-territory compatibility evidence. Claims and imports must match the certificate and current release. Completing all worldwide descendants (#7) is no longer a prerequisite for an already approved branch.

The content claim workflow and standard research import CLI enforce the recorded macro/regional gate and explicit subjects. A ready label, an open private API, a successful dry run or a complete structural chain cannot substitute for approval. The private service itself is not newly permission-isolated by this repository policy; workers must honor the reviewed workflow. Preserve existing live facts and completed research: this concerns new imports.

Source-only campaigns can run without approval or production credentials. Retain provisional IDs/pins and the source's actual subject. Never turn a settlement or different administrative territory into a whole-location scalar merely because names match. Before import, engineering must revalidate staged evidence against the approved branch; researchers must not silently repin completed bundles or move claims to replacement identities.

## Example: London in 1567

The current `atlas:city:GBR-Greater London` is a modern metropolitan-territory reference formed from 33 source members, about 1,580.897252 km²:

`London → Greater London province → London and South East England area → Britain region → Northern Europe subcontinent → Europe continent`.

Its territorial purpose remains open. A historical source's “London population” may describe the City of London or surrounding settlement, rather than that entire footprint. Engineering must finalize the target location and complete Britain branch before targeted location-attribute imports. Luna preserves narrower settlement evidence separately; it does not stretch that population to fit Greater London. Even after geographic approval, unsupported location fields remain unknown.

## Changes during concurrent research

One designated engineering publisher integrates geographic releases. Regional engineers own disjoint approved outer envelopes and coordinate shared-edge changes before implementation. Publishing a changed global release does not silently approve unchanged branches or update research pins: the publisher explicitly revalidates certificates and affected campaigns, preserving old receipts and crosswalks. The current import contract uses exact global release pins; an unrelated regional edit may therefore require revalidation of an otherwise unchanged approved branch.

An engineer changing a released branch identifies affected IDs/ancestors, old/new pins, crosswalk, linked research campaigns and maintenance window. A change to a frozen outer boundary reopens the relevant macro/shared-edge approval. Researchers stop obsolete imports and preserve existing evidence; source collection elsewhere may continue. Higher-tier name reuse also requires compatible descendants and geometry. See [GEOGRAPHIC_RELEASES.md](GEOGRAPHIC_RELEASES.md), [GEOGRAPHIC_RELEASE_VALIDATION.md](GEOGRAPHIC_RELEASE_VALIDATION.md) and [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md).

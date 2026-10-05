# West Africa interior batch 7 evidence review

**Issue:** [#473](https://github.com/ChengshuLi/WorldAtlas/issues/473)

**Baseline main:** `ee1b368bcaeb1fb114e3a5d0d9d3a2e06d633fa7`

**Work lane:** geography source evidence and handoffs only.

**Scope:** the issue's exact 229 locations in 31 provinces across a partial Liberia cohort (127/136), all 56 Mali locations, and a partial Mauritania cohort (46/69). The exact member IDs, region v5 pins, and source assignments are preserved in `issue-scope-pinned.json`, `baseline-receipt.json`, and `baseline-members.geojson.gz`.

The renewed serialized reservation receipt is retained at `reservation-renewal.json`; `issue-metadata.json` remains the original retrieval snapshot.

`evidence-review-index.json` is a supplemental whole-file index for independent review. Issue #473 predates the evidence-quality v1 activation, so this index is not represented as a policy-mandated v1 manifest; it provides the exact changed-file hashes and baseline/scope pins for the reviewer.

## Results

The repeatable assessment records all 229 subjects individually: **56 correction-needed** and **173 insufficient-evidence**. No subject is marked geographically justified. This is an honest source-evidence classification, not a region score or approval.

The highest-confidence defect is a source-role mismatch: 17 `atlas:physical` subjects derive from five geoBoundaries administrative predecessor polygons intersected with five retained RESOLVE ecoregion features. The ArcGIS item and layer describe RESOLVE Ecoregions and Biomes, an ecological 2017 source. These physical portions currently carry administrative `source_role` values (`Cercle` or `Mauritania`). The sourced proposal is to correct the role/selection rationale while preserving IDs, source-member IDs, geometry, and parent pending independent extent and parent review.

Other specific follow-ups are a current LISGIS crosswalk for the 127 Liberia subjects; post-2023 boundary and parent crosswalks for all 56 Mali subjects, including Bamako's special role; and a current DCIG/UN SALB moughataa crosswalk for all 46 Mauritania subjects, including the single-child Nouadhibou scale flag. Exact IDs and proposals are in `findings-and-handoffs.json`.

## Sources and territorial meaning

The immutable ADM2 feature files are pinned to geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d`; raw and compressed hashes, byte sizes, attribution licenses, retrieval details, restoration commands, and ADM1 parent-source snapshots are in `sources/register.json`.

- **Liberia:** 2021 geoBoundaries ADM2 “Districts,” 136 features, CC BY 3.0 IGO; this packet assigns 127. The LISGIS catalog lists 2022 district boundaries under CC BY 4.0. Its actual boundary download was not acquired or crosswalked. The catalog response is hash-pinned in `reference-source-checksums.json`, not retained because redistribution terms for the page itself were not verified. See the [LISGIS catalog and license](https://lisgis.gov.lr/open-data-license).
- **Mali:** 2017 geoBoundaries ADM2 “Cercle,” 50 features, CC BY 4.0; the 56 scoped subjects refer to all 50 old ADM2 predecessors, with 47 direct admin units and 9 ecological portions. Official reporting gives a post-2023 national organization of 19 regions and 159 circles. This is evidence that the 2017 source is not current, not a substitute for updated boundary geometry. The national source/crosswalk remains to be restored. See [Mali Government reporting](https://gouvernement.ml/5eme-cohorte-de-a-lecole-de-la-citoyennete-le-general-de-brigade-issa-ousmane-coulibaly-fait-le-point-sur-les-reformes-territoriales-et-de-la-decentralisation-dans-notre-pays/) and the [DNAT Tombouctou regional plan](https://dnat.gouv.ml/wp-content/uploads/2025/03/Plan-Strat%C3%A9gique-de-D%C3%A9veloppement-R%C3%A9gional-de-Tombouctou-vfinale_090532.pdf). The latter is a local official plan, not a national boundary layer.
- **Mauritania:** 2020 geoBoundaries ADM2 has 57 features and a canonical source label “Mauritania,” which is not a subdivision name; 46 subjects and 40 old ADM2 predecessors fall in this packet. UN SALB names DCIG as national authority and publishes validated administrative-polygon temporal coverage through a 2023 update. A 2023 PCGN fact file describes 15 wilayas and 54 moughataa/departments. Neither the feature-count difference nor the role string proves a specific boundary error. An exact current source, code, parent, and license crosswalk remains open. See [UN SALB Mauritania](https://salb.un.org/en/data/mrt) and the [PCGN fact file](https://assets.publishing.service.gov.uk/media/6504627b6771b90014fdab69/Mauritania_Toponymic_Factfile-Sept23.pdf).
- **Ecological portions:** the retained ArcGIS item metadata, layer metadata, queried features, and receipt establish the source identity and selected ECO_ID/ECO_NAME values. The five selected source features report CC BY 4.0; the five administrative predecessor sources retain their own licenses. See [RESOLVE ArcGIS item metadata](https://www.arcgis.com/sharing/rest/content/items/37ea320eebb647c6838c23f72abae5ef?f=json). Do not conflate that ecological source with an administrative boundary source.

`reference-source-checksums.json` records retrieval URLs, UTC dates, response lengths/statuses and SHA-256 for comparator pages/data. Where a response was not retained, the record explains the redistribution uncertainty and gives an explicit restoration URL. A Mali National Pathway URL returned HTTP 503 and is not used as decisive evidence. The official Tombouctou PDF is hash recorded but not retained because redistribution rights were not verified.

## Method and limits

`assessment.json` rebuilds from the retained baseline members and source bytes. It records exact ID/source membership, all ancestors through continent, name and role evidence, per-subject source vintage/license, geometry component/ring/vertex/bbox screens, parent representative-point checks, country-source remainders, and a finding with a concrete recommendation for every subject. `province-assessments.json` groups those same exact IDs without changing or certifying parent aggregates. `coverage-screen.json` makes the additional city-parent, source-name/remainder, disconnected-geometry, oversized-cohort, repeated-tier and neighboring-packet screens explicit, including which source questions remain open.

All 229 recorded representative points fall in exactly one retained pinned ADM1 candidate whose normalized name agrees with the Atlas province name. This is a point screen, not a polygon overlay or proof that the complete parent boundaries agree. For ecological subjects the point also falls in the full RESOLVE source feature and the source administrative predecessor. It does not establish that the Atlas physical fragment is the full or correctly clipped intersection. In `assessment.json`, ecological rows label predecessor geometry measurements as such and separately report the full, unclipped RESOLVE source feature screen; neither area is described as the clipped subject area.

`scale-screens.json` flags Bamako, whose pinned 2017 ADM2 geometry is byte-for-byte equal to the same-name ADM1 geometry, and Nouadhibou, whose spherical area screen is about 90.16% of its same-name ADM1 candidate and has one scoped child. `coverage-screen.json` also identifies Greater Monrovia as a metropolitan name signal and documents the nine named Nouakchott ADM2 units under one same-name ADM1 point-parent candidate. No city footprint comparison was performed for any of these. These are review flags only. They do not authorize deleting, merging, relabeling, or changing any geometry or parent. The calculation is a spherical ring-area approximation, not equal-area measurement or full GIS overlay.

The inspected evidence does **not** establish current completeness of settlements, cities, detached territories, islands, coastal low-water extents, or any country's full terrestrial coverage. It does not establish that every administrative source feature is a suitable Atlas tier. The issue's partial cohorts remain partial; source remainders are explicit in `assessment.json`. No disputed territorial status, geopolitical interpretation, neighboring boundary correction, or inter-region reconciliation is proposed. If a future exact source comparison finds a cross-border mismatch, it must be coordinated with the affected neighbor packet.

The v5 region release, hierarchy, footprints, macro certificate, region membership and all existing project geography remain unchanged. This packet does not approve any region interior, issue a branch certificate, authorize historical imports, deploy, publish, or write production data.

## Reproduction

From repository root with Node 24 (or a compatible modern Node runtime):

```sh
node data/regional-review/regional-review-97ccc950999ad631/verify_packet.cjs
```

The builder and packet verifier are offline and do not mutate project geography. `acquire_sources.py` retrieves the explicitly named immutable geoBoundaries commit plus RESOLVE service artifacts; `hash_reference_sources.py` re-fetches official comparator responses. Both scripts now refuse to overwrite retained source or receipt bytes. If any live response has changed, preserve it as a separately dated source vintage with new names, hashes, rights review and restoration notes; do not replace the archived receipt. Neither network script is needed to reproduce the assessment.

For an original source snapshot, decompress only to a new filename and verify the exact original byte count and SHA-256 in `sources/register.json`; do not overwrite the compressed evidence. Do not redistribute comparator pages or documents whose terms were not verified. The existing original geoBoundaries feature bytes are retained as gzip snapshots with exact original and compressed hashes and explicit restoration instructions.

## Follow-up records

`findings-and-handoffs.json` contains four bounded source/engineering handoffs with exact affected IDs: [ecological source-role correction #801](https://github.com/ChengshuLi/WorldAtlas/issues/801), [Liberia 2022 crosswalk #802](https://github.com/ChengshuLi/WorldAtlas/issues/802), [Mali post-2023 crosswalk #803](https://github.com/ChengshuLi/WorldAtlas/issues/803), and [Mauritania current moughataa crosswalk #804](https://github.com/ChengshuLi/WorldAtlas/issues/804). Each issue is blocked on its parent packet dependencies. The country-specific crosses overlap ecological subjects by design because they answer different source questions. Mauritania findings are split across the disjoint #473 and #474 cohorts, so the two combined children require both packets to finish and the other packet’s active owner to reconcile results before they can be marked ready. No child completion will certify this region or substitute for a complete source/geometry review.

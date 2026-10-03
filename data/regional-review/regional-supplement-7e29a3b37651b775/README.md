# Inaccessible Island source and hierarchy audit

**Issue:** [#525](https://github.com/ChengshuLi/WorldAtlas/issues/525)

**Pinned review:** `geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e` v5

**Scope:** the one assigned location, `atlas:island:geonames:3370905`, and its shared Tristan da Cunha parents.
**Result:** the named main island and its existing five-level parent chain are source identifiable. Whole-family coverage is unresolved: five separately closed coastline rings are outside the retained named-island geometry, and authoritative Tristan material names additional islands absent from the current inventory.

## Assessment

The assigned location represents the named main landmass of Inaccessible Island, not each rock or source ring. GeoNames identifies it as a named island at 37.29946° S, 12.67779° W (feature class `T`, feature code `ISL`, record date 2011-03-17). The Tristan da Cunha government page independently describes Inaccessible as an outer island, an extinct volcanic island with a 449 m summit, cliffs and difficult landings. UNESCO identifies Gough and Inaccessible as uninhabited oceanic islands. These sources support the geographic identity and a single named-island location; they do not establish historical shorelines, political ownership, or a complete treatment of nearby land.

The assigned location's current full chain is:

`atlas:island:geonames:3370905` → province `framework:province:tristan-da-cunha:33a276e2dcef` → area `framework:area:tristan-da-cunha:9cc13f608018` → region `framework:region:south-atlantic-islands:242a7633c849` (“Eastern South Atlantic Islands”) → subcontinent `framework:subcontinent:atlantic-islands:49ea8d869118` → continent `framework:continent:africa:d14fc0b285b2`.

The government source calls Inaccessible an outer island of Tristan da Cunha; the repository macro convention groups Tristan and Bouvet in a remote South Atlantic island reporting subcontinent. The continent association is the atlas's explicit geographic convention, not an inference from an owner code. No sovereign owner or historical attribute is assigned here.

The Tristan da Cunha area currently has one province of the same name; that province has two direct locations: the existing `SHN-4865` (Tristan da Cunha) and the assigned Inaccessible Island. `SHN-4865` is a Natural Earth ADM1 fallback reference with an undated vintage and `reference_owner: Saint Helena`; that political/reference field is not evidence of the physical island group's full membership. The area/province repeated tier is plausible for a sparse island group and is mirrored by the neighboring Bouvet area/province chain, but the shared Tristan parents remain semantically open until the island family is complete. `SHN-4865` was inspected as context, not recertified by this packet.

## Coverage findings and proposed follow-up

The retained OSM XML has a named Inaccessible Island multipolygon (relation 9704046) with 12 outer coastline ways and no inner rings. Its five separately closed coastline ways outside that relation are `29308363`, `29308364`, `478370353`, `682698552` and `888027621`; four carry `place=islet`. Each way's vertex-mean point tests outside the retained main-island land shell; this does not establish polygon overlap, area or integration. The current assigned feature and the #503 candidate land geometry do not include them. Their source names, durable size and role are not established well enough to assert that they belong in this location or deserve independent atlas locations. This is an explicit unresolved land-completeness finding, not an approval of omission.

The Tristan da Cunha government's Gough and Nightingale pages identify those as further members of the island group; the Nightingale page also names Alex/Middle Island and Stoltenhoff Island. The current published location inventory has no Gough, Nightingale, Alex/Middle or Stoltenhoff location. Gough and Nightingale are named islands rather than unlabelled rings. The extant issue scope is Inaccessible Island only, so this audit does not stage their geometry or change the shared parents.

Recommend a bounded follow-up covering the complete Tristan da Cunha island family: independently sourced Gough, Nightingale, Alex/Middle and Stoltenhoff land; the five nearby Inaccessible coastline rings; exact source coverage, granularity and proposed parent membership. Engineering/regional integration should reconcile the shared area and province only after that evidence is available. No inter-region boundary inconsistency was found; no boundary change is proposed.

The issue's source-profile hint also names `data/macro-foundation/new-location-source-profiles-v4.json.gz` with canonical SHA-256 `9b4939f3ae40a17866f2e082dd804b72ae57f778148beab10c7673474fe8a36e`, but that path is absent from current main `411ee3c`. Its expected hash cannot be verified in this checkout. The exact OSM XML and GeoNames archive inputs remain retained elsewhere in the repository; the follow-up should restore or regenerate the profile file from those pinned inputs and preserve the original source bytes.

## Reproduction

Run `python3 data/regional-review/regional-supplement-7e29a3b37651b775/reproduce-audit.py` from the repository root. It checks the pinned member/parent chain, the retained OSM and geometry hashes, ring membership, exact current parent children, and the absence of the named Gough/Nightingale family members from all indexed location parts. It writes only to stdout.

Source references, license and lawful-retention instructions are in `sources.json`. The source archive bytes remain in their original #503/#41 paths and were not copied or modified. `claim-receipt.json` records the serialized reservation required for this issue.

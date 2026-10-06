# East Siberian Russia source and semantic review

**Issue:** [#393](https://github.com/ChengshuLi/WorldAtlas/issues/393)  
**Review baseline:** `origin/main` at `e7cd364e08a713825daa80a3d085d23bd58d5730` (2026-10-06 UTC)  
**Scope:** the issue's exact 207 location IDs and six associated framework province records.  
**Owned packet:** `data/regional-review/regional-review-5cf69eed7fdff0b5/`.

This is source and semantic evidence for a bounded review workload. It is not a geographic subdivision, a certification of East Siberia or Siberia, or permission to publish interior boundaries or import historical attributes. The reproducible table assesses all 207 locations individually and all six province parents: [`subject-assessments.tsv`](reproduction/subject-assessments.tsv). Full per-feature measurements and source checks are in [`geography-assessment.json`](reproduction/geography-assessment.json); source provenance, hashes, licenses, retrieval limits, and restoration directions are in [`source-inventory.json`](source-inventory.json).

## Findings

| Subjects | Classification | Finding |
| --- | --- | --- |
| 185 source-ID matched administrative polygons | `insufficient-evidence` | All names and source IDs match the pinned 2017 GeoBoundaries Russia ADM2 original, but its generic `Raion` role is not enough to establish each unit's current legal/administrative status or completeness. Current name signals flag 30 urban-okrug candidates and 3 closed-territory candidates for official verification; these are leads, not classifications. An authoritative unit-level Rosstat/OKATO crosswalk and source completeness check remain missing. |
| 21 ecological fragments | `correction-needed` | Each is a RESOLVE ecoregion clipped to one of eight underlying ADM2 districts. The 21 observed (district, ecoregion) pairs reproduce against the saved service query, but their current records claim `Raion` and use a province parent. Correct source role and parent semantics need a bounded follow-up. |
| 1 Lake Baikal fragment | `correction-needed` | The subject is a Natural Earth lake polygon fragment within the Severo-Baykalsky district, not an administrative raion. Its public-domain lake source is intersected with an ODbL district source. Role, parent, and the remaining district water/gap relationship need follow-up. |
| Six province parents | `insufficient-evidence` | The Russian Constitution Article 65 supports their role as constituent federal subjects. That does not validate frozen Atlas province boundaries or complete subordinate membership; those reviews remain open. |

No proposed factual correction is silently applied. The current region handoff pins still report `regional_interiors_approved=false`, `publication_verified=false`, and `location_attribute_imports_ready=false`.

## Structural warning signs reviewed

The 185 direct source/current comparisons include 11 current multipart shapes (the largest has 118 components), 33 with interior holes, and 12 whose source and current component counts differ. Every direct source name matches its current Atlas name; none is anonymous in this source comparison. Those observations identify units for attention but cannot tell whether separated pieces or holes are legitimate, whether islands are missing, or whether a province-sized location is semantically valid. No official whole-country unit roster or sufficiently authoritative current district geometry was obtained, so completeness, omitted-island, anonymous-remainder, and province-scale claims remain unverified. The separate source-count gap is tracked by #396.

Current parent groups contain 13–66 reviewed children (Khakassia–Krasnoyarsk Krai). These counts and the common publisher role label do not establish an appropriate tier, parent purpose, or a valid size threshold. All six framework parents therefore remain individually `insufficient-evidence` for frozen boundary and complete membership. Neighboring granularity and province-scale suitability require the official crosswalk and coordinated parent review in #392; the packet does not imply that unmeasured topics passed.

## Source and geometry evidence

- **GeoBoundaries Russia ADM2:** pinned upstream commit `9469f09592ced973a3448cf66b6100b741b64c0d`; publisher vintage is boundary year 2017, source inputs last updated 2023-03-03, build date 2023-12-12; metadata license ODbL 1.0. The raw country file is 120,489,189 bytes with SHA-256 `74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0`, above the 32 MiB retained-file ceiling. Its exact 185 issue features and eight supporting district features are lawfully retained as scoped extracts; the publisher's full simplified version is retained as a comparison source. Restoration instructions and LFS pointer verification are in the source inventory. The publisher file has 2,327 features while its metadata claims 2,328; this known discrepancy belongs to [#396](https://github.com/ChengshuLi/WorldAtlas/issues/396).
- **RESOLVE ecoregions:** item `37ea320eebb647c6838c23f72abae5ef` describes the Dinerstein et al. 2017 ecoregion product; saved service metadata reports data last edited 2022-01-27 and the mutable ArcGIS item was modified 2026-05-28. The layer license is CC BY 4.0. Original query bytes are pinned. Three invalid source shapes (`resolve:707`, `resolve:710`, `resolve:737`) remain unchanged; diagnostic `make_valid` clones were used only for measurements.
- **Natural Earth lakes:** pinned public-domain GeoJSON commit `ca96624a56bd078437bca8184e78163e5039ad19`, whole-source SHA-256 `2d036f53dedec578001c5c30c2959ee7d4eebc1306900fa4367c49929ec8f2d9`. The Lake Baikal source feature has `year=-99`, so it does not establish year-specific hydrology. Terms: [Natural Earth terms of use](https://www.naturalearthdata.com/about/terms-of-use/); source description: [10m Lakes](https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-lakes/).
- **Official legal and classifier sources:** [Russian Constitution at the Ministry of Justice](https://www.minjust.gov.ru/ru/documents/8011/) Article 65 was read through web retrieval; direct byte retrieval returned 403, so this packet does not claim a local hash. [Rosstat classification](https://www.rosstat.gov.ru/classification) indicated amendments through 569/2026 and its [open-data record](https://rosstat.gov.ru/opendata/7708234640-okato) listed a current CSV, but certificate validation failed for the official download hosts. TLS checks were not bypassed. No unit-level classifier conclusion is asserted.

In EPSG:6933, the 185 current polygons versus the publisher's generalized polygons have IoU minimum/median/maximum `0.3992 / 0.9921 / 0.9980`; 74 are below 0.99, 31 below 0.95 and 16 below 0.90. Twelve feature component counts differ. These are triage comparisons, not correctness thresholds: no Atlas simplification method or acceptable tolerance was found, so the packet does not label these differences as errors or change geometry. The overlay IoUs are also measurements against source-derived intersections, not proof of legal or hydrologic boundaries.

## Reproduction

Use Node 24 and Python with Shapely 2 / pyproj. From repository root:

```sh
node data/regional-review/regional-review-5cf69eed7fdff0b5/reproduction/reproduce-scope.mjs
node data/regional-review/regional-review-5cf69eed7fdff0b5/reproduction/extract-geoboundaries-scope.mjs /path/to/verified-original.geojson
python data/regional-review/regional-review-5cf69eed7fdff0b5/reproduction/analyze-geography.py
python data/regional-review/regional-review-5cf69eed7fdff0b5/reproduction/render-review-table.py
```

For the extractor, first download the source inventory's pinned `media_url` to a temporary path and pass that path as the argument; it refuses mismatched bytes and deterministically extracts only the 185 direct scope features and eight overlay-support features. The raw 120 MB input need not be retained in the packet. The committed table and assessment were rendered from the saved source bytes; the two scope runs are byte-identical (225,036 bytes, SHA-256 `1a316bce1a5fc7b0c35e8abc132d2e8838f6df58aaf458133f9d6932de46732a`).

The reproduction verifies pinned identity, names, byte hashes, the exact scope and source-derived overlays. It cannot establish that the inputs are legally authoritative for every current unit, that mutable hosted services are historically complete, or that Atlas geometry is territorially correct.

## Follow-up and handoff

1. [#1125](https://github.com/ChengshuLi/WorldAtlas/issues/1125) verifies current administrative roles, statuses, codes, source vintage, and completeness for the 185 GeoBoundaries subjects using a retrievable official unit-level classifier and other primary legal/administrative records. It keeps the 2,327/2,328 publisher discrepancy coordinated with #396.
2. [#1126](https://github.com/ChengshuLi/WorldAtlas/issues/1126) reviews the role, parent, and source membership of 21 RESOLVE ecological fragments and the Lake Baikal fragment. It preserves their underlying district and overlay lineage and does not treat them as additional Raion units without primary evidence.
3. Coordinate semantic review of the six shared federal-subject parents and current province boundaries/membership with neighboring packets.
4. Engineering should implement any accepted hierarchy/role corrections in separately scoped work after sourced decisions. This packet changes no core geography, publication, or historical data.

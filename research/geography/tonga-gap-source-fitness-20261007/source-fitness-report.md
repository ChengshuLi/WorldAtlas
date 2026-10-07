# Vava’u source fitness: bounded assessment

**Scope.** This is a source-only assessment of the one-component complete family `gap-source-batch:baea0fbfa5673d262ff662ab`, for contact `gb:TON:ADM1:12702645B14713027314985` (Vava’u). It does not authorize a geography edit, boundary approval, physical-land classification, release, or deployment.

## Family and retained evidence

The frozen routing record contains one complete component and one complete contact, one original physical-source query (record 3792, level 1), no numeric-closure components, no unmeasured components, and no sibling contact/components. The source query is GSHHG 2.3.7, released 2017-06-15, with heterogeneous observation dates. Cause and physical authority are unknown/unapproved. Boundary length is unknown. The family retains the exact emitted mapped-land support sum `1371168824878867/549755813888 m²` (about 2,494.141562927083 m²); this is inherited binary64 output, not a new area calculation. All other recorded support categories are zero. See `inputs/complete-family-scope.json` and `inputs/physical-comparison-record.json` for the complete rows, query hashes, neighbor, extents, and unknowns.

## Product identity and source claims

The repository’s fetch recipe in `scripts/administrative.py` transforms the recorded geoBoundaries URL to request the `_simplified.geojson` product. The immutable source product retrieved for this assessment is the geoBoundaries TON ADM1 simplified GeoJSON at commit `9469f09592ced973a3448cf66b6100b741b64c0d`, 34,754 bytes, SHA-256 `e4937a7fcb49cc344f2e32f4525b90dbbbb3ef7e81d311b2d4b91a348b1f6f9d`. Its five feature IDs match the retained five-unit roster; Vava’u is shapeID `12702645B14713027314985`, ISO `TO-05`, ADM1. Its `shapeYear` is null.

The retained geoBoundaries metadata calls the represented year 2017, lists OpenStreetMap and Wambacher as contributors, says canonical role `Unknown`, and records an update date of 2023-01-19 and build date of 2023-12-12. These are metadata claims; no effective date or government certification was found. The prior #134 packet retains the related unsimplified product (1,202,782 bytes; SHA-256 `c879101306e56a83d5efc5cae56b5c92f02d1e3485ea6ac64bd3f94a67b7e24a`), which is not the fetched product consumed by the repository recipe.

## Bounded geometry comparison

On the exact retained candidate support coordinates, Shapely 2.1.2 planar XY predicates (no reprojection, buffer, repair, or densification) find that the complete Vava’u feature in both simplified and related unsimplified products covers the support pointset. The current Atlas Vava’u contact in `data/geography/part-23.json` intersects only at a boundary and does not cover the candidate. The approved `worldatlas-evidence-geometry-v1` helper measures this bounded support at 2,494.141562927083 m², equal at emitted precision to the inherited support metric. The source, unsimplified product, and current contact geometries are not topologically equal.

This establishes a source-to-current geometry discrepancy for the bounded retained support, not its cause or correctness. It does not establish dry land, legal boundaries, ownership, positional accuracy, registration, or which product should be released. Narrow shoreline/channel registration, observation-date mismatch, source precision, and physical authority remain unresolved.

## Purpose and authority limits

Tonga Statistics Department’s [Re-boundary Plan 2020–2021](https://tongastats.gov.to/download/279/reboundary/7658/reboundary-plan-v2.pdf) describes Tonga’s statistical hierarchy and the five island divisions, including Vava’u; it says the revision work focused on census blocks while division/village boundaries were retained for legal/reporting constraints. This supports the existence and statistical purpose of the division, not the exact geometry assessed here. The [Electoral Boundaries Regulations](https://ago.gov.to/cms/images/LEGISLATION/SUBORDINATE/2016/2016-2103/ElectoralBoundariesRegulations_2.pdf) define Vava’u electoral constituencies using estate boundaries, roads, and Mean High Water Mark; that is a different purpose and is not evidence that electoral geometries equal ADM1. The [Ministry of Lands survey services](https://www.lands.gov.to/programs/land-survey) describe survey/cadastral responsibilities, but no public Vava’u ADM1 geometry or certification was located there. A 1975 National Library of New Zealand Vava’u map catalog record is a historical lead only; the map itself was not inspected.

## Assessment

**Source fit: accepted with limits for a 2017-represented Vava’u statistical ADM1 comparison; not approved for any component.** The pinned source bytes and shapeID authenticate, the five-feature roster is complete, and the same-purpose statistical context is supported by TSD material. However, official/cadastral geometry, effective date, legal authority, and physical-land cause remain unverified. The observed discrepancy should be carried as an unresolved source/current mismatch for independent review; no geometry modification or release conclusion follows from this assessment.

## Evidence map

- `inputs/complete-family-scope.json` — complete frozen family row and hash of the complete routing shard.
- `inputs/physical-comparison-record.json` — complete physical row, query relation, source vintage, and retained unknowns.
- `inputs/source-provenance.json` — metadata, exact simplified product bytes/hash, feature roster, and related unsimplified product identity.
- `inputs/bounded-source-comparison.json` — geometry predicates, bounded ellipsoidal area, hashes, and explicit limits.
- `compare-bounded-support.py` — reproduction helper for the one retained component/source/contact comparison; it runs positive/negative controls with the approved geometry helper.
- `sources/official-source-register.json` — official/context source URLs, access dates, findings, and use limits.
- `sources/geoBoundaries-TON-ADM1_simplified.geojson` — exact retrieved product bytes.

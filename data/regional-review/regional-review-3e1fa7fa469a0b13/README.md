# Turkey districts: four-province evidence packet (issue #75)

This is a read-only, exact-scope review of the 30 issue-pinned location IDs under Ağrı, Van, Iğdır and Hakkâri. It does not alter locations or borders and does not certify the Anatolia/Eastern Mediterranean region, authorize imports, or approve source coverage.

## Findings

- All 30 IDs exist exactly once in the pinned WorldAtlas baseline and in the retained 2021 geoBoundaries Turkey ADM2 GeoJSON. Their source `shapeID`s and names are individually listed in `assessment.csv`. WorldAtlas parent IDs match the four province IDs declared by issue #75.
- Official province sources support the administrative roster interpretation: Ağrı Valiliği's current protocol table lists the seven district kaymakams in this packet; Van Valiliği's current administrators page lists all 13; Iğdır Valiliği's province page names Aralık, Karakoyunlu, Merkez and Tuzluca; Hakkâri Valiliği materials identify the five districts Merkez, Çukurca, Şemdinli, Yüksekova and Derecik. The exact locations in this issue account for all four province workloads, but roster completeness alone does not validate boundary geometry.
- geoBoundaries metadata describes TUR ADM2 as “Districts”, vintage 2021, under ODbL 1.0. Its GeoJSON has 973 features while the same pinned metadata reports `admUnitCount: 999` (26 more). This exact nationwide discrepancy is already tracked by #817; this packet does not duplicate that work or infer where omitted records belong.
- The source's only grouping field is `shapeGroup=TUR`; it does not encode the immediate province relationship. The Atlas parent linkage is separately pinned in its hierarchy, and the administrative rosters substantiate the names/parent assignment at the level of current administrative association.
- Three center records are labeled “Ağrı merkez”, “Hakkari merkez” and “Iğdır (merkez)”; Van has separate İpekyolu, Tuşba and Edremit district records. These are material city/district granularity questions. Available roster evidence establishes district names but does not establish whether central-city territories are represented in the intended atlas tier without overlap, omission or duplicated urban coverage.
- HGM's Turkey administrative-boundaries product page states that province/district/village limits are indicatively derived for display, carry no official status, and are reusable only outside commercial activity with attribution. It therefore cannot settle the boundary question for this atlas or be retained/distributed here under its stated terms.

**Disposition:** each of the 30 locations is `insufficient-evidence`. No row is marked `justified` solely because its name appears in an official administrative roster or because the source calls it ADM2. No row is marked `correction-needed` without evidence of an actual error. The four complete province workloads are likewise `insufficient-evidence` as geographic parent scopes. The immediate next engineering/research handoff is a lawful, versioned authoritative boundary layer and official district-code/name crosswalk for these four provinces, followed by coverage, topology, urban subdivision and adjacent-level comparisons. Preserve current IDs/parents until that evidence and a coordinated decision exist.

## Sources, terms, dates and reproduction

The original source bytes are retained in the prior packet [regional-review-ef67318527f5f3a3](../regional-review-ef67318527f5f3a3/), not copied or overwritten here. The compressed source SHA-256 is `a88007de2cf14f14e06da390aab8861442c7a8332ef8e70865d78e0d9b549d78`; its uncompressed GeoJSON SHA-256 is `8e7594ab12d916e3b93f920475a300c364dfb94a0e40bfa6d55f43aff0c7fd97`; metadata SHA-256 is `ace87195676281a6b58bc822a275646b71dbdca42ca4b7445bc928730596fdc7`. `source-register.json` records the pinned geoBoundaries commit and restoration URL. This is a lawful ODbL source; preserve its attribution and database-license obligations. The original source was retrieved 2026-10-04 America/Los_Angeles by the prior packet.

Official roster pages were inspected on 2026-10-04 America/Los_Angeles through their published HTML/web representations. The pages are dynamic and no raw HTML response bytes were retained, so this packet does not claim content hashes for them. Their restoration URLs and the exact facts relied upon are recorded in `source-register.json`; a future verifier should retrieve fresh official records and compare, since page contents can change. They establish administrative role/name association, not legal boundary coordinates.

Reproduce the ID, parent, source-membership and roster-scope checks from repository root with Python 3:

```sh
python3 data/regional-review/regional-review-3e1fa7fa469a0b13/build_review.py
```

The script reads the pinned baseline commit `f9a1dfa98b664dcf322806c843e82ab29d2b7935` using Git blobs, verifies the retained compressed source SHA-256 before decompression, checks all 30 exact IDs in both source and baseline, checks their four expected Atlas parents and emits `scope.json` and `assessment.csv` only in this owned directory. It also records each retained source geometry's type and polygon component count; all 30 are single Polygon features. It does not calculate authoritative borders or claim source completeness. Its current output hashes are listed in `source-register.json`; two identical successful reproductions and a failing wrong-source-hash control are recorded in `verification.json`.

## Turkey area and neighboring granularity

The parent geography in issue #75 is the entire Turkey area (911 reference members); this packet assesses only 30 districts in four border provinces. The larger Turkey subset in packet #71 reviewed 198 locations; other Turkey/province subsets remain owned by the remaining initial batch work. Neither subset individually explains the area's full extent, island/enclave coverage, district population completeness or neighboring administrative levels. The fixed area purpose stays open for the regional integration #76, which depends on all initial packets and source/restoration follow-ups. At this packet's immediate parent edge, all four province parents match the explicit issue scope; there is no versioned official polygon/code crosswalk to independently measure the district-to-province interface or compare neighboring provinces. The district names “center” require particular city-scale scrutiny: the roster evidence does not say whether central-district boundaries encompass continuous urban areas or how settlements are distributed across adjacent districts.

## Limits and handoffs

1. #817 owns the national geoBoundaries 973-versus-999 source discrepancy and broader Turkish coverage/crosswalk. Keep it open until source membership and omissions are reconciled against a lawful source.
2. HGM cannot be used as an authoritative or redistributable boundary source under its published terms. Any future reuse must have a separate license review and still would not establish legal status.
3. The four official rosters do not provide versioned boundary geometries or stable district codes on the pages inspected. Secure those from an authorized, reusable primary source before any proposed correction.
4. District/municipal boundaries in dense Van urban areas and three “central” districts need separate semantic/granularity inspection. No conclusion about urban fragmentation, connectivity, islands, gaps, or neighboring-tier fit is claimed from counts or names.
5. Turkey completeness remains national, not local: exact inclusion of these 30 rows cannot explain the 26-feature national mismatch or prove omitted geography elsewhere.

No geometry correction is proposed because no independent, concrete local error is established by the retained/official roster evidence. The demonstrated nationwide feature-count/source reconciliation remains in #817. The distinct missing authoritative boundary/code crosswalk and center/urban granularity work has been split into blocked follow-up #874 (exact same subjects; disjoint owned evidence directory; depends on #75 and #817). Regional integration remains #76. Completing this packet cannot approve the four provinces or the whole region.

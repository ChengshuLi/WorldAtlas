# Equatorial Micronesia interior batch 1 evidence

**Issue:** [#140](https://github.com/ChengshuLi/WorldAtlas/issues/140)  
**Review baseline:** current `main` at `39188aadf6efdae60357d9d4a1bbb62ffd981003`; frozen region release v5  
**Region:** `atlas:macro-review:region:ba863bc35dac7390` (Equatorial Micronesia)  
**Assigned:** 3/3 locations, 3/3 provinces, 2/2 areas. Evidence is read-only; no hierarchy, geometry, grid, identity, claims, schemas, app code, certificates or live releases were changed.

## Decisions

| Subject | Assessment | Main finding | Follow-up |
|---|---|---|---|
| `gb:KIR:ADM1:97431129B55805139245338` Gilbert Islands | correction-needed | 2017 ADM1 archipelago aggregation is 14 current parts (~119.65 km²) against 29 source parts (~249.27 km²); KNSO documents 19 Gilbert census-island rows but no cadastral geometry. The current broad group is not demonstrated complete or suitable as a local location. | #611 |
| `gb:KIR:ADM1:97431129B36644055464690` Western equatorial Pacific source remainder | correction-needed | Two retained components are east near Banaba/Tarawa but derive from the source feature named Phoenix Islands; current Phoenix province sits under Gilbert area. Exact component-to-island/source-history crosswalk is unknown. This is a cross-region identity/parent inconsistency. | #611 coordinated with #526, #404 and #139 |
| `atlas:territory:NRU` Nauru | insufficient-evidence | One-island location is plausible; official 2021 21.1 km²/14-district description conflicts with the present (~19.84 km²) and 2005 geoBoundaries district union (~21.45 km²). Census charts are not boundaries; Yaren/Location also needs alias resolution. | #612 |

Province and area purpose assessments are recorded individually in `assessment.json`. Singleton repeated names and footprint equality do not prove either redundant tiers or distinct geographic roles. Gilbert’s area/province combination includes the unresolved B366 item. Integration retains ownership of combined parent decisions.

## Methods and reproducibility

1. `build_baseline_extract.py` copies all three exact scoped location features, complete location→province→area→region→subcontinent→continent chains, member rows, source properties, current projection rows and baseline-input hashes from the pinned v5 `main` checkout. Exact IDs and hashes are in `baseline-extract.json`.
2. The compressed frozen region envelope was independently read from its pinned source; the union of the 3 current location geometries is topologically equal to it (zero symmetric difference), matching frozen membership and bounds. This checks only baseline membership/envelope consistency; it does not endorse interior completeness.
3. `screen_gshhg_land.py` screens all 243 level-1 land records in the declared windows (22 intersect at least one assigned geometry), preserving each hit and nearest unmatched candidates. Run with the verified GSHHG 2.3.7 full-resolution shapefile path. This is generalized physical coastline evidence only: it is neither administrative nor legal evidence, and upstream registration/scale uncertainty precludes treating overlap as a boundary verdict.
4. `write_packet.py` reproduces the source and current equal-area measurements plus assessment/source manifests. The task venv used Python 3 with `shapely==2.1.2`, `pyproj==3.7.2`, `pyshp==2.3.1`, and `numpy==2.3.5`; these are already project geometry dependencies except pyshp, which is only for the external shapefile. No app dependency changed.
5. Run `verify_packet.py` with the documented geometry venv for exact issue scope, complete parent closure, retained/baseline hashes, source record counts, GSHHG output counts, and topological comparison of the frozen envelope to the bottom-up location union.
6. Kiribati 2020 census report/2022 atlas and Nauru 2021 census report were downloaded and reviewed but not retained because explicit re-use permissions were not located. Canonical URLs, exact byte counts, SHA-256, inspected pages/facts and restoration instructions are in `source-receipts.json`. Never reconstruct official geometry from census charts.
7. Full original geoBoundaries source objects and license metadata are retained unchanged in `sources/`; `sources-manifest.json` gives per-file byte counts and SHA-256. GSHHG archive is not retained (149 MB); its canonical URL, hash and exact shapefile restoration recipe are recorded.

Source area comparisons use EPSG:6933. All geometry measurements are screening results. Administrative assignment, sovereign attribution, historical ownership, island land, settlement distribution and geographic parentage are separate evidence questions.

## Scope audit coverage

- All assigned location features, their source roles/vintages/licenses, original names, disconnected parts, retained source candidates, direct settlement/island clues, complete parent chains, ancestor membership and the frozen region member/envelope hashes were reviewed.
- Gilbert group: the official KNSO Table G-1 / Census Atlas island rows enumerate Banaba, Makin, Butaritari, Marakei, Abaiang, North/South Tarawa, Maiana, Abemama, Kuria, Aranuka, Nonouti, North/South Tabiteuea, Beru, Nikunau, Onotoa, Tamana and Arorae. These are reporting units, not a 19-location quota. Island-specific official spatial boundaries remain missing.
- Banaba is identified by the official atlas as the separate raised coral island in the Gilbert group. The second B366 remnant component cannot yet be sourced to an exact named island; it remains explicitly unresolved.
- Actual Phoenix Islands coverage lies in the South-Central Pacific region and is reviewed under #526. The KIR ADM1 source feature and its eastern remnant do not establish how that source was split/assigned. Neighbor integration must coordinate any change.
- Nauru: the 14 district names and chart are population evidence, not spatial boundaries. “Location” is a settlement and chart label; report narrative places it in Denigomodu, next to Aiwo. `Yaren` ↔ `Location` is not assumed to be a proven alias.
- GSHHG physical land candidates and neighboring windows were screened exhaustively within the declared boxes; results and uncertainty are explicit in `gshhg-land-screen.json`. No false claim of complete island verification is made from that generalized coastline source.

## Bounded source follow-ups

- #611 requests a full-source crosswalk for the two KIR IDs, Banaba/Tarawa remnant components and the Phoenix neighbor family, coordinated across Equatorial Micronesia and South-Central Pacific. No parent or shared-boundary edit is proposed here.
- #612 requests authoritative Nauru district/island spatial source restoration and a 14-district crosswalk, including Yaren/Location, with no geometry mutation.

These packets do not approve either regional interior or enable historical/location-attribute imports. Regional integration must validate and publish the complete branch separately.

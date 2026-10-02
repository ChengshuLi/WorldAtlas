# Location scale and audit

EU5 supplied a rough granularity reference only. No EU5 files, names, boundaries, or count quotas are used. Atlas locations are territories, not settlement points. A city's territorial location can include surrounding countryside; its historical settlement, name, rank, and population require independent dated evidence.

## Selection rules

1. Select a named local administrative role for each country, recorded in `data/location-policy.json`. ADM numbers are not globally comparable. Italy uses provinces/metropolitan cities, France arrondissements, Germany districts, Japan municipalities, and China the reviewed county/district layer. The old mean-area optimization is removed.
2. Consolidate compact states/territories (at most 3,000 km² and 150 km extent) so their wards do not become peers of surrounding districts. Hong Kong, Singapore, and Macau are examples. Dispersed archipelagos fail the extent guard.
3. Combine constituent wards within published city territories. Examples include Greater London's 33 boroughs, New York's five boroughs, Mumbai's two districts, and Korea's metropolitan cities. Natural Earth city classification/footprints and named source parents supply membership; the complete matched-member evidence is recorded. Korean districts use an independent GeoNames crosswalk to repair erroneous source parents. Major cities remain separate when surrounding rural municipalities are aggregated. Taiwan’s six special municipalities and three provincial cities use independently checked same-source ADM1 membership (170 districts), which takes precedence over Natural Earth city-outline overlap at urban seams. Disconnected small components with the same source district name are consolidated, with distance and size checks; a polygon part is not automatically another location.
4. In unusually fine rural source layers, use published named groupings: Spain's MAPA agricultural districts, Brazil's IBGE immediate geographic regions, and Canada's named census divisions. Brazil's intermediate regions supply the province tier. These are atlas groupings, not invented contemporary government tiers.
5. Replace anonymous Canadian census remainders with AAFC named ecoregions and ecoprovinces. Audit every other rural location above 50,000 km² against published physical regions: Australia's IBRA subregions and global RESOLVE ecoregions. Subdivisions follow source district and physical boundaries, never arbitrary rectangles or equal-area cuts. Natural Earth named lakes cover inland-water portions where the ecological source omits water.
6. Retain a named remote territory when the geographic evidence cannot justify multiple substantial subdivisions or has unresolved offshore coverage. Each such decision is listed in `remote_scale_reviews` and its location metadata. Source-edge adjustments are bounded to 0.1° and recorded. The threshold triggers review; it is not a universal size target.
7. Screen every named Natural Earth ADM1 territory for omissions caused by selecting mainland-only country layers. Restore absent named overseas/island territories and missing city cores, preserving existing source interiors. Source coastlines, lakes and boundary vintages can differ; the coverage report distinguishes these differences from recovered territories.

The output deliberately has variable area. Equal area is incompatible with coherent compact cities, inhabited islands, rural districts and remote physical regions. Small islands may still be smaller than a rendered grid cell. Large protected/remote territories can remain coarse where stronger source evidence is unavailable. These exceptions are visible in the audit; the map does not claim uniform historical granularity or worldwide exact coastline coverage.

## Source evidence

| Source | Use and attribution |
|---|---|
| geoBoundaries gbOpen | Reviewed ADM1–ADM3 district polygons; per-country source year, original license and SHA in `administrative-sources.json` |
| geoBoundaries gbHumanitarian, Algeria and Angola | Named commune/municipality polygons from OCHA/HDX; CC BY 3.0 IGO; replaces incomplete Algerian names and the obsolete Angola layer, whose Catumbela polygon was a point-like artifact |
| Natural Earth | Public-domain city/territory boundaries, populated places and named lakes, pinned revision `ca96624a56bd078437bca8184e78163e5039ad19` |
| [IBGE localities API](https://servicodados.ibge.gov.br/api/v1/localidades/municipios) | 2017 immediate/intermediate geographic regions and municipality membership; ambiguous joins checked against IBGE municipality polygons |
| [MAPA official agricultural districts](https://sig.mapa.gob.es/arcgis/rest/services/25830/comunComarcasAgrarias/MapServer/2) | © Ministerio de Agricultura, Pesca y Alimentación; free reuse with attribution. Uses the official service, not the separately restricted Esri Spain mirror |
| [Statistics Canada census divisions](https://www.arcgis.com/home/item.html?id=24f45c7b49d84aaf8e55e566a7fd670b) | 2021 named census divisions; Statistics Canada general-use terms; attribution/metadata retained |
| [AAFC ecological regions](https://www.arcgis.com/home/item.html?id=ee462b0692cc4005aefee69dc44f010d) | Agriculture and Agri-Food Canada National Ecological Framework; Open Government Licence – Canada; source ecoregion/ecoprovince names |
| [IBRA 7.1](https://www.arcgis.com/home/item.html?id=0e78c21ba12543019b92e10272f980fe) | Commonwealth of Australia / DCCEEW, 2025; CC BY 4.0; named Australian biogeographic subregions |
| [RESOLVE Ecoregions 2017](https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef) | RESOLVE / Esri; CC BY 4.0; remote geographic subdivisions |
| [Geolonia Japanese administrative boundaries](https://github.com/geolonia/japanese-admins/tree/d302c49670b5252970649a6481e25d56c64fd08c) | MLIT National Land Numerical Information, adapted by Geolonia; MIT repository and underlying MLIT government reuse terms. Independent municipal polygons identify missing Japanese labels |
| [GeoNames](https://download.geonames.org/export/dump/KR.zip) | CC BY 4.0; independently matched Korean ADM2 names, coordinates, aliases and metropolitan membership |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | © OpenStreetMap contributors, ODbL 1.0; named Turkmenistan district crosswalk for unnamed source fragments; adapted polygons and evidence are distributed with source |

The reviewed evidence bundle `data/semantic-evidence/` (a split compressed archive) and its SHA-256 manifest preserve external snapshots and crosswalks. Gazetteer populations only help identify major city municipalities; they are **never imported as location population or historical rank**. Gazetteer aliases are search aids, not historical names.

## Reproducible validation

`npm run data:prepare` runs source selection, hierarchy completion, overlap reconciliation, geographic grouping, coverage review, semantic aggregation, remote review, final geometry checks and the full audit. It fails for unresolved labels, invalid geometry, missing parent chains, or overlapping interiors above 1e-10 square degrees. Aggregation/refinement scripts retain source membership and compare coverage; final numerical seam repairs have strict area tolerances.

`data/granularity-audit.json` lists every active location, its basis, area and province; country distributions; all small/coarse units; and the checks and their scope. `semantic-report.json` lists merges, replaced source IDs, matching evidence and remote exceptions. `coverage-report.json` records all low-coverage reference comparisons. `hierarchy-report.json` records hierarchy classification. All are available from the interface's source information panel.

The audit hashes its geography and policy inputs. Static publishing refuses stale or failed audits. Structural checks are exhaustive over the dataset; they do **not** certify every source's real-world accuracy, every geographic judgment, or historical names and borders. New source vintages require renewed review.

Database migration archives replaced IDs and retains their original geometry and historical records. History is never reassigned from a borough to a metropolitan union, or from a large territory to its subdivisions. The London demonstration is a newly labeled illustrative fixture on the new footprint; original imported records remain attached to their original entities. Custom locations are preserved.

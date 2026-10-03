# Western North America interior batch 2 — evidence packet

Issue: [#486](https://github.com/ChengshuLi/WorldAtlas/issues/486)
Claim: `codex-20261003-wna-486-d7aeefc5f37a450c8247ddbe8df5ffac`
Snapshot date: 2026-10-03 UTC
Owned path: this directory only. This packet is a research finding and proposed correction record; it does not change hierarchy, geometry, certificates, schemas, application code, or live data.

## Audit completion

The exact issue scope contains **211 of 533** region locations: 120 Mountain and 91 Pacific. The packet includes a row for every assigned ID in `assessment.json`, the pinned scope in `scope.json`, complete current parent chains, and reproducible extracts. The full current chains were checked through location → province → area → region → subcontinent → continent. The workflow is bottom-up: location membership defines footprints; the top-down workflow only sets review order.

| Evidence cohort | Audited | Result |
|---|---:|---|
| Direct geoBoundaries 2018 ADM2 county/equivalent subjects | 178 rows / 185 distinct predecessors | All assigned source IDs crosswalked against 2024 Census TIGER state rosters; 0 unmatched predecessors and 0 unmatched current roster features in the five assigned states |
| Alaska derived ecological fragments | 33 | All exact Eco_IDs overlaid against the seven 2018 county predecessors they divide; all seven predecessor unions reconciled. All 33 carry `source_role=Counties` despite RESOLVE ecoregion provenance: correction needed in future integration |
| Complete parent chains | 211 | Preserved with cohort and sibling context; no parent or boundary edits proposed here |
| Census Places settlement polygons | 1,996 features across five states | Spatial intersection screen for every subject; 8 ecological fragments have no polygon hit |
| USGS GNIS populated-place points | 6,067 five-state records | Spatial point screen for every subject; 9 have no hit; the same 8 ecological fragments have no hit in either screen |
| GSHHG land screen | 179,832 level-1 source records | Every assigned representative point tested (210 land hits, 1 no-hit); 30 assigned features received a GSHHG land-polygon centroid hit. Neither point screen proves complete islands, coastlines or land area |
| Alaska–Canada boundary screen | IBC sections 27–29 | Map-only proximity evidence; coordinated review required with the Canadian-side issue owner and regional integrator; no boundary correction is asserted |

### Findings and proposed handling

1. **33 Alaska ecoregion fragments:** `derived-portion-audit.json` names each fragment, current province/area chain, exact RESOLVE Eco_ID, and parent county. RESOLVE describes ecological units, not administrative jurisdictions. Record a bounded integration follow-up to replace/clarify role semantics while preserving location membership and derived footprints. No unilateral shared-boundary change.
2. **2018 Valdez-Cordova predecessor:** `gb:USA:ADM2:52423323B16539688175930` is a 2018 source-vintage predecessor; the 2024 TIGER roster has Chugach and Copper River. Crosswalk both successor features, do not relabel the predecessor as a current legal administration, and request a bounded ID/vintage integration follow-up.
3. **Alaska parent split:** the complete Alaska cohort is represented by two distinct current province IDs, one containing Aleutians West and one the remaining 54 assigned locations. Their combined 2018 ADM2 union agrees closely with 2018 Alaska ADM1. This is a parent-grouping question for regional integration, not a permission to merge/reparent either node in this packet.
4. **Alaska–Canada:** IBC 1.3 sections 27 (Portland Canal), 28 (Southeast Alaska), and 29 (141st Meridian) are map representations of treaty boundaries and explicitly not for defining boundaries. Distances to 2018 geoBoundaries/current location geometries are screening only; scale, datum and source-vintage differences prevent claiming an error. Coordinate with issue #485 for neighboring Canadian coverage and #484 for shared integration. Preserve the affected Canadian and Alaskan subjects in a joint follow-up; no unilateral correction.
5. **Settlement gaps:** the eight physical fragments listed in `assessment.json` have no intersecting 2024 incorporated-place/CDP polygon and no GNIS Populated Place point. They remain unresolved. Census/GNIS no-hit is not evidence of absence; inspect local authoritative settlement/administrative sources in a bounded follow-up.
6. **Other land/island cases:** GSHHG screening is deliberately limited to representative points and candidate land polygon centroids. A no-hit or hit cannot establish full component, island, coastline, sovereignty, or settlement completeness. Require named authoritative local review for any proposed correction.

No political ownership is inferred from ecological membership or physical proximity. County identity and names are tied to geoBoundaries ADM2 2018 and separately compared with 2024 Census features. Historical or legal attributes are not inferred from current parent nodes. Antarctica is outside this issue scope.

## Reproduction and validation

Run from the repository root with Python 3, GDAL/OGR Python bindings, and internet access only if restoring omitted raw source material:

```sh
python3 data/regional-review/regional-review-93f8f3bee8e205be/extract_baseline.py
python3 data/regional-review/regional-review-93f8f3bee8e205be/screen_gshhg.py data/regional-review/regional-review-93f8f3bee8e205be/sources/gshhs_f.b
python3 data/regional-review/regional-review-93f8f3bee8e205be/build_assessment.py
python3 data/regional-review/regional-review-93f8f3bee8e205be/audit_ibc_border.py
```

`scope.json` was extracted against the pinned upstream issue metadata. `extract_baseline.py` deterministically regenerates the owned baseline snapshots from the current regional source without editing it. `sources.json` lists the retained source byte counts and SHA-256 values. Derived geometry calculations use temporary EPSG:3338 for Alaska and EPSG:5070 for contiguous U.S.; source geometry remains unchanged. OGR reports invalid/self-intersecting inputs during projection; these are not silently repaired into repository data. Reported overlays and area values are exploratory checks, not certified topology.

## Canonical sources, dates, licenses and restoration

All retained packet files are enumerated and SHA-256 hashed in `sources.json`. Key source decisions:

- **geoBoundaries USA ADM1/ADM2, 2018 boundary vintage.** Canonical API: `https://www.geoboundaries.org/api/current/gbOpen/USA/ADM1/` and corresponding `/ADM2/`. Raw GeoJSON and metadata retained. Open license metadata is retained with each extract. These are source-vintage administrative representations, not a declaration of present legal status.
- **U.S. Census Bureau TIGER/Line 2024 Counties and Places.** Canonical counties ZIP `https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip` (83,913,260 bytes; SHA-256 `04e668d3502757c837c13444730547cd967f28a2c49aeffb873d1792ab2cb97b`; DBF update 2024-09-16). This national archive was used to produce the retained 1,039-feature 17-state neighbor subset; it is omitted to keep the packet smaller. Restore by downloading that URL and verifying the hash. Selected Alaska/Colorado/New Mexico/Oregon/Wyoming Places archives are retained and hashed; DBF update 2024-09-13. TIGER files are U.S. federal works; Census geography is not a legal land survey.
- **RESOLVE Ecoregions 2017 / ArcGIS item and layer metadata.** Canonical item `https://www.arcgis.com/home/item.html?id=28f7e3e126b4422a9c1c7d4e9d6d746e`; feature service and exact Eco_ID query references are in `resolve-item-metadata.json` and `resolve-layer-metadata.json`. Data last edit 2022-01-27; item metadata modified 2026-05-28. Item license CC BY 4.0. The exact 15-feature selection is retained compressed. Ecological classification is not administrative ownership.
- **USGS The National Map Gazetteer / GNIS REST.** Service `https://cartowfs.nationalmap.gov/arcgis/rest/services/geonames/MapServer`; layer 0. Query receipt records the five-state filter, date, pages and result count (6,067). The records are U.S. federal public-domain geographic names. Official format reference `GNIS_file_format.pdf` retained. The service is a flat names database, not a settlement census or administrative hierarchy. Its `isunknowncoords=2` flag was retained; coordinates were screened from actual point geometry because sampled records have valid nonzero positions. No data was skipped on that flag alone.
- **GSHHG 2.3.7 (2017-06-15), full-resolution physical shoreline data.** Official archive `https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip`; archive SHA-256 `28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc`, member `gshhs_f.b` 95,809,336 bytes SHA-256 `af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6`. Restore by downloading/verifying the archive and extracting/verifying the member. The large archive and raw member are omitted; matched records are retained compressed. LGPLv3-or-later terms and upstream notice are retained. This physical shoreline compilation is not an administrative or island gazetteer.
- **International Boundary Commission, Canada–U.S. boundary v1.3 (2018-04-20).** Official coordinates page `https://www.internationalboundarycommission.org/en/maps-coordinates/coordinates.php`; source archive retained, NAD83/EPSG:4269, 30 rows. Official metadata warns the mapped treaty line is not for boundary definition. Canadian metadata combines Open Government Licence Canada language with an “all rights reserved” statement and cites OGL conditions; U.S. metadata carries the same OGL constraint. This license-text tension is preserved for downstream review, not resolved by assumption. The accompanying feature-scale and datum limits mean proximity findings are not boundary error findings.
- **Project baseline.** `current-scope-and-parents.geojson.gz` and `current-parent-chains.json.gz` are pinned scope/context extracts from current project baseline; hashes in `sources.json`. They preserve source IDs and complete hierarchy for reproducible review.

No source is included to authorize bulk location-attribute imports. A completed packet does not approve either area or regional geography; integration and full branch validation remain prerequisites.

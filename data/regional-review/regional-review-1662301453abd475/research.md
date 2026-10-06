# West North Central batch 5: source and semantic findings

Research date: 2026-10-05, America/Los_Angeles (the corresponding UTC date is 2026-10-06). Scope is the 186 exact location IDs in the captured #264 issue body, two complete state/province groups (Iowa and Minnesota), and the **partial** West North Central area slice. This packet is evidence only; it does not approve the region or certify the complete area.

## Source lineage and what the shapes mean

The 186 Atlas IDs each end in a geoBoundaries `shapeID`. All 186 match unique features in the full `gbOpen/USA/ADM2` file at immutable geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d`. That file has 3,233 national features. Its retained release metadata identifies the boundary year as 2018, its source as the U.S. Census Bureau MAF/TIGER database, its canonical unit as counties, and its source-data update/build dates as January 19 and December 12, 2023. The matching ADM1 file identifies Iowa and Minnesota as states, with the same source lineage and release dates. These exact metadata files and source bytes are retained under `source/`; the LFS source commit and per-file hashes are in `geometry-and-membership-results.json`.

The geoBoundaries metadata points to the Census Bureau's **2018 1:500,000 Cartographic Boundary File**. The official file is retained and independently joined to every subject by Census `GEOID`; both complete Census county and state archives contain the scoped rows. The Census documentation describes these as simplified small-scale thematic map boundaries. It cautions that they are unsuitable for geographic area/perimeter analysis or precise geographic relationships, and that some small areas can be absent. The close Atlas-to-source match therefore verifies source lineage and county identity; it does **not** prove detailed or exhaustive boundaries.

Two independent Census TIGERweb vintages were also retained: the January 1, 2018 county/state layers and the January 1, 2026 current county/state layers. All 186 county `GEOID`s appear in both, and the county codes use LSADC `06` throughout. Current and 2018 detailed TIGERweb geometry is almost unchanged across the batch (median Jaccard 0.99999990). That comparison helps distinguish a continuing source-product portrayal difference from an observed 2018-to-2026 county-code or boundary change. Census says TIGER depictions are for statistical collection and tabulation and do not determine jurisdictional authority, ownership, or legal land descriptions.

Reuse: the pinned geoBoundaries metadata reports Public Domain for the underlying Census boundary data. Its retained citation/use notice requires attribution for geoBoundaries derivative products under CC BY 4.0; attribution to both geoBoundaries and the U.S. Census Bureau is recorded here. Census federal data is retained with Census attribution. Exact downloaded bytes, compressed and uncompressed hashes, pinned URLs/queries, and restoration instructions are in `source/` and `geometry-and-membership-results.json`.

## Source documentation and interpretation

- Census [2018 cartographic boundary downloads](https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html) and [Cartographic Boundary File description](https://www.census.gov/programs-surveys/geography/technical-documentation/naming-convention/cartographic-boundary-file.html): product scale, simplification, potential small-area omissions, and limits on precise relationship/area use.
- Census [2018 TIGER/Line documentation](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2018.html) and [2018 TIGER user note](https://www.census.gov/programs-surveys/geography/technical-documentation/user-note/tiger-geo-line.2018.html): Jan. 1, 2018 vintage and the distinction between statistical depiction and jurisdictional/ownership authority.
- Census [geographic terms glossary](https://www.census.gov/programs-surveys/popest/about/glossary/geo-terms.html): counties are primary legal divisions in most states and generally functioning county governments, with functions varying by state. This supports an administrative county tier, not a claim that Census geometry settles each county's legal land/water extent.
- Census [official regions and divisions list](https://www2.census.gov/geo/docs/maps-data/maps/reg_div.txt): the seven-state membership used to check the West North Central hierarchy parent and identify the five peer states outside this batch.
- geoBoundaries [API and data-level documentation](https://www.geoboundaries.org/api.html) and the pinned local [citation/use notice](source/geoboundaries-citation-use.txt): release metadata and derivative attribution obligations. The notice itself and exact source commit are retained with original bytes.

## Subject and parent findings

The reproduction makes a one-to-one join for all 186 rows: Atlas `metadata.original_id` / geoBoundaries `shapeID` to Census 2018 `GEOID`, using maximum polygon overlap and a unique match, then name, state code, parent ID, and current-vintage code checks. All 186 Atlas labels equal the geoBoundaries source labels; all 186 Census county names match after dropping the `County` suffix; all Atlas parent IDs agree with the state indicated by the Census FIPS code. Counts are 99 Iowa counties and 87 Minnesota counties, with no omitted or duplicate county `GEOID`s in either two-state TIGERweb extract. The exact map, names, codes, parent IDs, and per-unit comparisons are recorded row by row in `geometry-and-membership-results.json`.

The issue's West North Central area is a named Census division containing seven states and 618 locations. The official Census division list confirms all seven state names in the pinned hierarchy. This packet owns only Iowa and Minnesota: 186/618 locations, 2/7 state groups. Its other five peer states (Kansas, Missouri, Nebraska, North Dakota, and South Dakota) remain outside this packet and require their own evidence. The 186 rows form a county tier under complete Iowa and Minnesota state groups; there are no city-cluster or metropolitan units in this source layer. The Census glossary says counties are the primary legal divisions of most states and usually function as governments, with powers varying by state. This supports their administrative role here; it does not assert urban functional regions or legal boundary authority from Census map lines.

**Iowa:** the 99 named county units and parent state have source/tier support. The Atlas county union versus the pinned 2018 cartographic Iowa state is Jaccard 0.99908; that cartographic state versus TIGERweb state is 0.99980. Assessment: `justified` for the state and county identities/tier, subject to the cartographic source's general completeness limits.

**Minnesota:** the 87 named county units and parent state are correctly linked by IDs and state parents, but extent remains unresolved. The Atlas county union matches the geoBoundaries/cartographic Minnesota state closely (Jaccard 0.99889), while the cartographic state versus TIGERweb state is 0.97049. Assessment: `insufficient-evidence` for the province footprint.

Three counties receive individual `insufficient-evidence` classifications:

- **Cook County, GEOID 27031** (`gb:USA:ADM2:52423323B35428884505626`): Atlas-to-cartographic Jaccard 0.98872, but cartographic-to-TIGERweb Jaccard 0.48116. The detailed Census depiction contains far more area than the cartographic depiction. Do not infer from this number alone whether that difference is Lake Superior water, omitted detail, or another representation boundary.
- **Lake County, GEOID 27075** (`gb:USA:ADM2:52423323B21927262007954`): Atlas-to-cartographic Jaccard 0.99101; cartographic-to-TIGERweb Jaccard 0.76438. The source-generalization caveat and exact intended county/water extent still need a focused decision.
- **Koochiching County, GEOID 27071** (`gb:USA:ADM2:52423323B71326746759120`): Atlas shape has seven polygon components while the source/cartographic shape has one. The main Atlas component is about 8,164,460,432 m² and overlaps the source nearly completely; a separate approximately 2,129 m² component is covered by the source, another approximately 206 m² component is outside it, and four sub-square-metre components are also present. The retained product cannot determine whether these are island remnants or topology slivers. Its county identity is supported; the fragments need review.

The other 183 counties are classified `justified` **for county identity and administrative tier**, based on their unique names/IDs, parent-state match and same-vintage source lineage. No classification certifies exhaustive island/coastline detail. The per-unit result file retains full overlap measurements for each unit rather than applying a single numeric pass threshold.

## Area, neighbors, fragmentation, and follow-up

This partial batch does not claim the entire West North Central area, the five other states, regional completeness, or a complete mainland/island inventory. At the scoped county tier every unit is named and has one matching 2018 and 2026 Census county code. There is no anonymous remainder or urban/city unit in these 186 source rows. One disconnected-feature exception, Koochiching, is enumerated above. The Census cartographic product's warning about excluded small areas means the broader omitted-island question remains open even where the individual identity and broad tier are supported.

Follow-up #1079, **Investigate Minnesota county extents and Koochiching fragments**, now records Cook, Lake, and Koochiching plus the Minnesota state parent, with exact IDs and release-file pins. It remains blocked on this packet. The handoff should compare detailed lawful county/state sources with the cartographic product, establish the intended land/water representation and complete neighboring boundaries, and recommend any engineering/source-restoration work by exact ID. No Atlas geometry edit is proposed in this research packet.

## Reproduction and limits

From the managed checkout root, install the recorded Python packages in an isolated environment, then run:

```sh
python -m pip install -r data/regional-review/regional-review-1662301453abd475/requirements.txt
PYTHONPATH=. python data/regional-review/regional-review-1662301453abd475/reproduce.py
```

The run uses `worldatlas-evidence-geometry-v1`: longitude-first EPSG:4326; WGS84 straight-source-edge ellipsoidal area; WGS84 inverse-geodesic distance policy. The 2018 Cartographic Boundary shapefiles start in NAD83/EPSG:4269 and are transformed to EPSG:4326 with explicit `always_xy=True`. Area-overlap metrics discard zero-area line/point overlay fragments without repairing source input geometry. Controls pass for a same-feature positive self-overlap (Jaccard 1) and a distant Iowa/Minnesota county negative overlap (Jaccard 0). A 186-row unique crosswalk and matching 2018/2026 GEOIDs are useful evidence checks, not proof of factual completeness.

The pinned environment is Python 3.12.14, Shapely 2.1.2, pyproj 3.7.2, pyshp 2.3.1, and certifi (version recorded in `provenance.json`). Exact commands, original source URLs, retrieval date, compressed and uncompressed hashes, Census layer queries, and restoration instructions are recorded in `source/RESTORE.md` and `source/provenance.json`. Reproduction result SHA-256 after the final source inventory and focused per-county findings were added: `42228b70e581b4d6a949e934b33a3cc66a2331f3c685c1c56f54dabbf97c381b`. No live Atlas geometry, production data, release, or history was changed.

**Decision boundary:** research for the packet can complete with explicit open footprint findings. It does not certify any geography release, approve #258, permit imports, or replace the required separate exact-head substantive review and serialized merge queue.

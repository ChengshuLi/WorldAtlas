# North-Central Pacific supplemental NWHI source review (#523)

This packet assesses all seven issue-assigned locations. It is a partial audit of the Hawaii area (7 of 14 descendant locations) and does not certify the full North-Central Pacific region or enable historical imports. The current published v5 parent counts are: 14 area descendants, 13 descendants of the Hawaii province, and 15 region locations. Every assigned location follows the same current bottom-up parent chain through Hawaii province, Hawaii area, North-Central Pacific, Polynesia, and Oceania.

## Findings by location

- **Laysan — correction needed:** a closed salt-lagoon water ring is in the retained OSM extract, and USFWS describes a central hypersaline lake. The accepted source polygon has only the exterior coastline, so it currently counts that lagoon inside its land footprint. Recommend a dated, licensed water boundary and a local interior-hole correction that retains the Laysan identity and all history.
- **French Frigate Shoals — insufficient evidence:** USFWS describes an atoll with a crescent reef and numerous islets; the retained 2026 OSM union has eight components. OSM notes question whether four named features remain above high tide and identify washed-away islets. Exact modern above-water composition is unresolved.
- **Kure Atoll — insufficient evidence:** atoll-level location role is coherent; OSM reconstructs two land components, but an exhaustive named-islet and high-tide inventory is not in the retained sources.
- **Lisianski Island — justified:** USFWS describes one raised coral-bank island and separately names Neva Shoals; the OSM union has one closed land component, with area close to USFWS’s rounded value. The submerged reef is not included as dry land.
- **Necker Island (Hawaii) — justified, with a naming follow-up:** USFWS uses Mokumanamana and describes one small basalt island. The OSM union has four components, one named Mokumanamana and three unnamed. Obtain Hawaiian-language/cultural gazetteer evidence before changing the displayed name. Historical cultural use does not establish current habitation.
- **Nihoa — insufficient evidence:** USFWS describes one rugged basalt island and historical short-stay use. OSM reconstructs three components, but two coastline ways carry Mapbox imagery source tags and have no independent primary shoreline reference in the retained packet. The named-island location role is plausible; full component completeness is not verified.
- **Pearl and Hermes Atoll — insufficient evidence:** USFWS describes a dynamic atoll with seven reported exposed islets; the retained OSM-derived union has 13 components. Neither source’s underlying observation date resolves the difference.

The assigned objects are named islands or atoll/islet-group territories, not province-sized administrative polygons. OSM rings and land components describe source geometry; they are not a quota for separate atlas locations. French Frigate Shoals and Pearl and Hermes require current, high-tide source restoration before their component lists can be called complete.

## Shared administrative source finding

The 2024 U.S. Census TIGER/Line Honolulu County boundary (GEOID `15003`, StateFP `15`, CountyFP `003`) contains all seven candidate land geometries. The current indexed Honolulu ADM2 location `gb:USA:ADM2:52423323B23592629733445` is bounded to Oʻahu and intersects none of the seven candidates. This is a possible disconnected county remainder/source-completeness gap or a difference in source role. It is recorded for regional coordination on #339; this packet changes no shared county geometry, source, or parent. Census county inclusion is administrative evidence, not an inference of sovereign ownership.

## Source records and reproduction

`assessment.json` contains the exact seven IDs, individual classifications, canonical references, dates, license/restoration notes, all coastline ways, raw/stored hashes, topology counts, methods, uncertainty and follow-up recommendations. `issue-metadata.json` is the issue 523 metadata snapshot used by the verifier. Original OSM XML bytes remain in `data/macro-improvements/macro-coverage-oceania/`; no original evidence was edited. They were retrieved 2026-10-02 under ODbL 1.0 with OpenStreetMap attribution. The inherited OSM `NOAA U.S. Vector Shoreline` tags do not identify the NOAA shoreline product vintage. Nihoa also includes two Mapbox-traced ways; the OSM data remains ODbL, but imagery is not retained or treated as independent proof.

USFWS’s Hawaiian Islands National Wildlife Refuge `About Us` and refuge overview pages are the primary sources for island/atoll descriptions, refuge and seasonal-use context. Their pages have no publication/update date or explicit license notice visible in the accessed content. The packet paraphrases their facts and gives canonical restoration URLs and access date (2026-10-03). Their rounded, undated areas do not prove modern high-tide shorelines. Upstream #501 retains GSHHG 2.3.7 Hawaiʻi/NWHI search-domain records under LGPL-3-or-later. This packet did not establish a one-to-one GSHHG component crosswalk for these seven identities, so that older source cannot resolve their modern completeness.

The official Census boundary archive is 83,913,260 bytes, SHA-256 `04e668d3502757c837c13444730547cd967f28a2c49aeffb873d1792ab2cb97b`, from [TIGER/Line 2024 County and Equivalent](https://www2.census.gov/geo/tiger/TIGER2024/COUNTY/tl_2024_us_county.zip). It is a U.S. federal public-domain work. Restore it to a temporary location and run:

```sh
python3 data/regional-review/regional-supplement-256993a64222ee97/verify.py --census-zip /tmp/tl_2024_us_county.zip
```

The verifier checks exact issue membership, current index geometry equality and complete parent chains, retained source hashes and all seven complete coastline reconstructions, the Laysan water-ring omission, current Honolulu-location nonintersection, area/province/region counts, and (when the ZIP is supplied) all seven TIGER containment results. It requires GDAL/OGR command-line tools for spatial checks. It does not edit repository geography.

## Follow-ups

1. Source and resolve the Laysan hypersaline-lake boundary under the accepted dry-land convention.
2. Restore date-stamped emergent-land/islet inventories for French Frigate Shoals, Kure, Pearl and Hermes, with component-level cross-checks for Nihoa and Necker.
3. Coordinate a bounded review of Honolulu County’s detached Northwestern Hawaiian Islands in its original administrative source and the Hawaii parent packet.
4. Verify Mokumanamana/Necker naming precedence from Hawaiian-language and cultural authorities.

No current sovereign owner, present settlement, historical attribute, or region-wide approval is inferred from these findings. Missing evidence stays explicit.

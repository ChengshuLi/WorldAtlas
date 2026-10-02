# Africa and Americas named-land coverage review

Issue #41 extends the macro audit without changing regional interiors, hierarchy, location identities, canonical grid, historical records or the published Site. All **25** named-land routes from the approved macro decisions are accounted for, including the **18** whose full family coverage was uncertified. No additional full-family coverage certificate is asserted.

The complete results are in `report.json`; `components-dry-land.json.gz` retains every tested source component, its original source identity, whole-footprint intersections, named gazetteer context and uncertainty. The original decisions and exact envelope index are pinned by hash. Those frozen envelopes remain the comparison baseline, not proof that all real land is represented.

## What was tested

The review scanned all 188,612 full-resolution GSHHG 2.3.7 records. Defined geographic windows produced **35,902 family/component observations covering 33,753 distinct coastal components**. Every positive-area candidate was retained; summaries use an explicit **0.1 km²** threshold. This is a practical review threshold, not a promise that all smaller rocks exist in the atlas.

GSHHG Level 1 coastal components were compared with all 81 actual regional envelopes. The headline dry-land comparison subtracts **393 direct Level 2 inland-water polygons affecting 14 components**. Freshwater islands (Level 3) are outside this ocean-island inventory; this review does not certify freshwater shoreline detail. Areas use oriented rings and WGS84 ellipsoidal calculations. Longitude unwrapping and validity repair occur only in independent audit geometries, never in the atlas.

Country-specific GeoNames gazetteers supply independent named island context. Their coordinates identify candidate components; they do not certify complete archipelagos. Only exact point-in-polygon matches enter the stricter named component summaries. Provisional nearby matches, unnamed polygons and conflicting/coarse coordinates remain visible in the evidence. Country codes disambiguate modern gazetteer entries and do not set continent or region ownership.

Broad windows around Greenland and the Caribbean include neighboring geographies. Their raw candidate counts must **not** be reported as missing-island counts. Similarly, a mainland exclave cannot be tested by asking whether its region covers a majority of an entire continent. Focused comparisons show Ceuta and Melilla's actual location footprints have approximately **93.7%** and **89.0%** support in the independent African dry-land mask. These checks do not certify legal borders or offshore rocks.

## Substantive confirmed findings

Three currently existing named islands are absent from every atlas region, independently confirmed using current closed OpenStreetMap coastlines:

| Island | Current coastal area | Whole current footprint overlap with atlas | Current-source corroboration |
| --- | ---: | ---: | --- |
| Disko / Qeqertarsuaq | 8,537.95 km² | 0 | 16,684-vertex closed coastline; 99.55% overlaps GSHHG |
| Milne Land | 3,766.43 km² | 0 | 778-vertex closed coastline; 95.44% overlaps GSHHG |
| Inaccessible Island | 14.545 km² | 0 | 466-vertex closed coastline; only 36.88% overlaps older GSHHG |

These are **outer coastal areas**, with the current OSM inland-water mask still requiring final footprint preparation. The dry-land comparisons in the component ledger have a separate GSHHG water mask. `osm-correspondence.json` records all exact OSM way IDs, geometry hashes, source timestamps and whole-polygon measurements; normalized candidate footprints are under `osm/`. They are audit candidates, not approved locations or imported geometry.

The weak old/new overlap at Inaccessible is important: GSHHG positional errors can approach kilometres for small islands. An old source polygon with no overlap cannot by itself establish an actual missing island. Conversely, the two large Greenland omissions remain absent against both old and current sources and are not explained by a small shoreline offset.

The review also identifies named or associated coverage candidates in Madeira, the Canaries, Cabo Verde, Comoros/Mayotte, Seychelles, Greenland, Bermuda, the Lucayan and Caribbean island groups, Galapagos, Falklands and South Georgia/South Sandwich. They retain individual source IDs, names and measured coverage in the ledger. Other routes remain principal-land-only or source-precision unresolved. No raw candidate receives an invented location identity, political owner or historical interval.

The pinned original geoBoundaries 2020 Greenland municipal source also has zero intersection with the two confirmed Greenland islands. This is an upstream completeness problem. The exact original source is retained as `original-grl-adm1-source.geojson.gz`; no spatial parent match can be invented from absent source geometry. Four new requests for named Greenland administrative articles failed and remain recorded as failures. `restoration-candidates.json` preserves existing location/province candidates, confirmed macro destinations and the unresolved lower-tier choices.

Restoration follows issue #146: corroborate current geometry and identity, determine a supported adjacent-tier parent, record a geographic migration, check fixed-grid representation, and publish coordinated macro-envelope/certificate amendments. Existing historical evidence must be preserved. This source review does not authorize silently expanding a frozen regional envelope.

## Sources and original bytes

- **GSHHG 2.3.7**, released June 15, 2017, University of Hawaii/NOAA; LGPL 3.0 or later. The original global ZIP URL, full ZIP hash and full native binary hash are recorded. Exact selected native shoreline and water records are retained as binary fragments with original offsets, lengths and SHA-256 values. The full 118.6 MB distribution is not duplicated into Git; it is recoverable from the pinned versioned public URL. `README.TXT.gz`, `LICENSE.TXT` and `COPYING.LESSERv3` preserve notices. Header areas use the magnitude exponent encoded in flag bits 26–31, not the stale `/10` description.
- **GeoNames**, daily country dumps retrieved October 2, 2026; CC BY 4.0. `geonames-country-dumps.tar.gz` retains the downloaded original country ZIP bytes and original license README. Inventories record successes, failures, byte lengths and hashes. A failed source is not treated as successful evidence.
- **Wikipedia**, 65 page requests with 64 successes, retrieved October 2, 2026; CC BY-SA article text. `wikipedia-pages.tar.gz` retains original HTML; the inventory keeps URLs, hashes and parsed coordinate context. Coordinate summaries of archipelagos are not treated as individual island footprints.
- **OpenStreetMap contributors / Geofabrik**, ODbL 1.0. The retained Greenland PBF is the unmodified downloaded source, last modified October 1, 2026. Twenty thousand and ninety-five coastline ways stitch into **16,312 closed, valid, land-left rings, with zero open chains**. The separate successful Inaccessible Overpass response (original bytes compressed as `osm/inaccessible.json.gz`) and exact query are also retained. Disko and Milne Land Overpass requests failed; the successful Geofabrik source, not failed requests, supports their result.

`manifest.json` hashes every committed evidence file. Original raw source fragments are distinguished from parsed derivatives and normalized WKB. No private credentials, Site tokens or database credentials are present. These audit files are not added to browser deployment assets.

## Reproduction

The scripts under `reproduce/` document the exact audit procedure and write only temporary audit outputs. They expect the repository at `/workspace/WorldAtlas` and a temporary directory `/tmp/worldatlas-macro-coverage-africa-americas`; adjust those paths for another environment. Their source-only scope must not be confused with a production geographic installer.

Restore retained raw page/country archives into that temporary directory; obtain the versioned GSHHG ZIP and verify its SHA-256 before extracting `gshhs_f.b`. Start from the retained approved-decision input pins, not an unpinned future geographic release. Use the temporary `osmium==4.2.0` parser only for reproducing the OSM PBF extraction; it is not an application dependency. The separate manifest/source-fragment verifier can run without downloading sources or modifying application data.

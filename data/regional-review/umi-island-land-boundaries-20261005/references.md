# Inspected sources and restoration instructions

All source metadata and NOAA/OSM data archives retained below were retrieved on 2026-10-05 America/Los_Angeles unless otherwise dated. SHA-256 and exact byte lengths are in `evidence-quality.json`.

## NOAA NGS CUSP

- Product metadata: [NOAA InPort 60812](https://www.fisheries.noaa.gov/inport/item/60812), saved at `sources/noaa-inport/60812-cusp-full-list.html`.
- Catalog terms/access metadata: [Data.gov CUSP record](https://catalog.data.gov/dataset/noaa-ngs-continually-updated-shoreline-product-cusp), saved at `sources/data-gov/noaa-ngs-cusp.html`. It lists CC0 1.0 and `accessLevel=non-public`; NOAA's public NSDE region download was accessible. Preserve this catalog contradiction.
- Product documentation: [NOAA Shoreline Data Explorer More Information](https://nsde.ngs.noaa.gov/more.html), saved at `sources/noaa-ngs/nsde-more.html`.
- Regional download: [Pacific Islands ZIP](https://geodesy.noaa.gov/dist_shoreline/Pacific_Islands.zip), retained at `sources/noaa-ngs/CUSP-Pacific_Islands.zip`. Retrieval was 2026-10-05 21:17 PDT; response headers were re-read and saved at 21:34 PDT as `sources/noaa-ngs/CUSP-Pacific_Islands.http-headers.txt`. Header `Last-Modified` is 2026-08-05 16:45:34 GMT, ETag is `"68f3db-6584f80090780"`, and content length is 6,878,171 bytes. License stated by Data.gov: CC0 1.0. NOAA InPort constraints: no access constraints; not for litigation; no warranty; attribution to NOAA requested. CUSP metadata: may not be complete, source types vary and lines can be updated rather than newly compiled; record source date separately from regional ZIP vintage.

## NOAA project surveys retained in CUSP

Each source ZIP and completion PDF is kept unchanged. Restore from its direct NOAA download URL if needed. The project report describes imagery-based source dates and accuracy; InPort records 60798–60801 are retained under `sources/noaa-inport/` and each includes access/use terms and process/completeness notes.

| Site | InPort record | Survey/project | Source imagery date | Reported horizontal accuracy at 95% | NOAA project data ZIP | Completion report |
| --- | --- | --- | --- | --- | --- | --- |
| Palmyra | [60798](https://www.fisheries.noaa.gov/inport/item/60798) | UM0501 | 2001-12-15 | 17.6 m | `https://nsde.ngs.noaa.gov/downloads/UM0501.zip` | `https://www.ngs.noaa.gov/desc_reports/UM0501.PDF` |
| Baker | [60799](https://www.fisheries.noaa.gov/inport/item/60799) | UM0502 | 2004-04 | 15 m | `https://nsde.ngs.noaa.gov/downloads/UM0502.zip` | `https://www.ngs.noaa.gov/desc_reports/UM0502.PDF` |
| Howland | [60800](https://www.fisheries.noaa.gov/inport/item/60800) | UM0503 | 2005-05 | 15 m | `https://nsde.ngs.noaa.gov/downloads/UM0503.zip` | `https://www.ngs.noaa.gov/desc_reports/UM0503.PDF` |
| Jarvis | [60801](https://www.fisheries.noaa.gov/inport/item/60801) | UM0504 | 2004-03 | 12 m | `https://nsde.ngs.noaa.gov/downloads/UM0504.zip` | `https://www.ngs.noaa.gov/desc_reports/UM0504.PDF` |

The four InPort HTML metadata receipts are retained as `sources/noaa-inport/{item}-full-list.html`; the corresponding Data.gov metadata pages are `sources/data-gov/{palmyra-atoll-us-pacific-islands-um0501,baker-island-u-s-pacific-islands-um0502,howland-island-u-s-pacific-islands-um0503,jarvis-island-u-s-pacific-islands-um0504}.html`. Each Data.gov page lists CC0 1.0 but also `accessLevel=non-public`, although NOAA's viewer distribution and direct NGS files are publicly accessible. The InPort records show no data-access constraint and document NOAA's use disclaimer/credit request. NOAA reports the product lines are clipped to survey/project neatlines, and its rectangular data management boundary does not imply complete surveyed coverage. For Palmyra the report specifically says an artificial alongshore-feature boundary line was added for continuity. Use only natural shoreline classes for these diagnostics. Project archives also contain non-shoreline classes and project-boundary polygons; do not mistake those for island land.

NOAA datasets are listed as CC0 in Data.gov metadata; InPort requests NOAA credit and disclaims warranty/fitness, and says the project datasets are not for litigation. This packet is research evidence, not a legal shoreline determination.

## Territorial/protected-area context (restoration-only citations)

FWS's descriptive pages were inspected, but not copied because the pages contain mixed media with page-specific reuse that cannot be established from the page alone. Restore them by visiting these URLs; cite page title and retrieval date:

- [Baker Island National Wildlife Refuge](https://www.fws.gov/refuge/baker-island), retrieved 2026-10-05: distinct refuge/island; current page gives 531 terrestrial / 409,653 submerged acres within 410,184 total refuge acres and describes a low coral island with sand/coral shingle beaches.
- [Howland Island NWR, About Us](https://www.fws.gov/refuge/howland-island/about-us), retrieved 2026-10-05: distinct island/refuge; 648 terrestrial / 410,351 submerged acres within 410,999 total, shallow fringing reef and extended monument protection.
- [Jarvis Island NWR, About Us](https://www.fws.gov/refuge/jarvis-island/about-us), retrieved 2026-10-05: separate island; current displayed protection total 429,853 acres, 1,273 terrestrial / 428,580 submerged, including 200-nautical-mile monument protection.
- [Palmyra Atoll NWR](https://www.fws.gov/refuge/palmyra-atoll), retrieved 2026-10-05: about 26 islets, several lagoons, and refuge waters/submerged lands to 12 nautical miles; monument protection extends farther.
- [FWS 2013 Palmyra rat-removal release](https://www.fws.gov/story/2013-01/native-species-expected-rebound-palmyra-atoll), retrieved 2026-10-05: historical statement of 25 islets and 580 land acres.
- [FWS final Palmyra rat-eradication environmental impact statement](https://www.fws.gov/sites/default/files/documents/FINAL%20-PalmyraRatEradicationFEIS-complete.pdf), retrieved 2026-10-05: describes the atoll before the restoration effort as approximately 54 small islets surrounding three central lagoons; this historic framing is not a present-day roster.
- [FWS copyright and disclaimer](https://www.fws.gov/disclaimer): linking is allowed; not all page material is public domain. No page graphics were retained.

These facts distinguish dry land from protected marine extent; they do not provide reusable vertices or a complete islet/cay roster.

## OpenStreetMap independent screen

- Query endpoint: `https://overpass-api.de/api/interpreter` (POST); replay query: `sources/openstreetmap-overpass-query.txt`.
- Raw result: `sources/openstreetmap-overpass-20261005.json`, retrieved 2026-10-05 America/Los_Angeles; embedded `osm3s.timestamp_osm_base` is 2026-10-06T04:08:02Z. Exact whole-file hash is in the evidence manifest.
- OSM terms: [OpenStreetMap copyright and license](https://www.openstreetmap.org/copyright) and [OSMF licence/legal FAQ](https://osmfoundation.org/wiki/Licence/Licence_and_Legal_FAQ). Data is ODbL 1.0; attribution is to OpenStreetMap contributors and this extract/derived geographic diagnostics are distributed under the applicable share-alike terms (see `LICENSE-OSM.txt`).
- The saved equivalent query covers natural coastlines, place/natural island, islet or atoll way/relation features, and named island/islet nodes in four fixed site windows. The initial exact POST body was not saved; do not assert byte-identical query restoration. OSM user-contributed mapping is neither official nor completeness evidence.

## Pinned Atlas baseline and predecessor evidence

The exact subject geometries and pins are read from immutable baseline commit `947b991690a5720b48b9a664b34cba3f5e4a515d`, not reconstructed from this branch's mutable files. `data/geography/part-28.json` holds all four subjects. `data/hierarchy.json` preserves their province identities and physical area ancestors. The pinned Natural Earth source extract is in the completed #405 predecessor packet. Its physical grouping does not authorize changing U.S. reference-owner identities; see that packet's references and issue #405 for the source crosswalk.

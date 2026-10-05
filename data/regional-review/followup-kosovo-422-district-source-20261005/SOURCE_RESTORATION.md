# Source restoration record

Retrieval date for all network observations below: **2026-10-05 UTC**. Hashes are SHA-256 of the exact response body bytes retrieved on that date, except geoBoundaries' geometry and metadata hashes, which are also upstream Git LFS object IDs. The official PDF response bodies were inspected through a text extraction/search view; they are not retained in this packet because a redistribution license for those documents was not established. Re-fetch the given URL and confirm its hash before relying on a new retrieval. Current legal web pages can change; a hash mismatch means create a new evidence vintage rather than replacing this receipt.

## Original geoBoundaries seven-feature collection

The original lawful-restoration candidate already exists in the immutable #422 packet at `data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/`. Do not create a second geometry copy under this child while the source and service rights conflict remains unresolved.

- Repository: `https://github.com/wmgeolab/geoBoundaries`
- Exact commit: `9469f09592ced973a3448cf66b6100b741b64c0d` (commit time 2023-12-13T04:03:07Z)
- GeoJSON path: `releaseData/gbOpen/XKX/ADM1/geoBoundaries-XKX-ADM1.geojson`
- Direct immutable media URL: `https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/XKX/ADM1/geoBoundaries-XKX-ADM1.geojson`
- GeoJSON size/hash: 1,898,578 bytes; SHA-256 `9b07b08fe0f9ca5a26ddb6de2008ac235b38ffaf069063df9851711c2d358315`
- Metadata path: `releaseData/gbOpen/XKX/ADM1/geoBoundaries-XKX-ADM1-metaData.json`
- Metadata hash: SHA-256 / LFS OID `a912dcaefa1096a6c0af067af9723b2a67c32f5b0147b8198f99751eb591b49c`, size 799 bytes.
- Citation/use file hash: `f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5`, size 4,316 bytes.
- Existing parent packet manifest: `data/regional-review/regional-review-3c4fe25a21fa428d/source/source-manifest.json`, SHA-256 `fded0febc8ef8d934b1f7358755b3102ec8043cc027a88ad8106dec8247b7f56`.

To restore for authorized private/source analysis, GET the raw media URL without changing the commit, save the body in the authorized research destination, and require both the exact size and SHA-256 above. The GitHub `raw` web URL may return an LFS pointer; use the media URL and verify it is full JSON, not the small pointer. Never substitute the current geoBoundaries API result for this 2021-representative vintage.

The metadata says `boundaryYear=2021`, `sourceDataUpdateDate=Thu Jan 19 07:31:04 2023`, `buildDate=Dec 12, 2023`, `boundarySource=Open Street Map`, `boundarySourceURL=https//osm-boundaries.com/`, `boundaryCanonical=Municipalities`, `boundaryLicense=Creative Commons Attribution-ShareAlike 2.0`, `licenseSource=https//www.openstreetmap.org/copyright`, and `admUnitCount=48`. It does not give an OSM database date/snapshot, OSM relation IDs, an OSM-Boundaries database ID, or terms for the exact service-generated geometry. `boundarySourceURL` and `licenseSource` are malformed (`https//` lacks a colon) in the retained original; do not repair the archived bytes.

## Official Kosovo sources

| Source | Retrieval/restoration URL | Retrieved body SHA-256 | Inspected fact and limit |
|---|---|---|---|
| Kosovo Agency of Statistics, *Classification of Statistical Regions in Kosovo*, April 2022 PDF | `https://askapi.rks-gov.net/Custom/baa59b95-af3f-4117-8c84-edc9ef401bf7.pdf` | `aa322791fa3d683e8f054c57551437e754846b5094f4b413879011c152a6cb0f` (2026-10-05) | Pages 4–7 describe 38 administrative municipalities, seven non-administrative NUTS III statistical regions, and each region's member municipalities. No vector geometry or boundary reuse license. |
| Official Gazette, consolidated Law 03/L-041 record, published 2025-07-08 | `https://gzk.rks-gov.net/ActDetail.aspx?ActID=107377` | `4d45a816aaef692e52d037b121cb49f1a4cbcbb81f6fcc4332aa01583e2ba246` (2026-10-05; 14,622 bytes) | Current official consolidated record. Its incorporated law defines municipalities as basic local self-government units and boundaries by cadastral zones; this HTML response is not a boundary dataset. |
| Official Gazette, original Law 03/L-041 record (2008-06-02) | `https://gzk.rks-gov.net/ActDetail.aspx?ActID=2518&langid=2` | `a44c1ed6b3e0ac3d2e102158122f47b008f79796c088b4bc0f03d6569a44afff` (2026-10-05; 26,813 bytes) | Legal text and the original municipal/cadastral-zone annex. The 2008 text alone is not evidence of present-day polygon geometry. |
| Kosovo Agency of Statistics, 2024 census final-results publication | `https://askapi.rks-gov.net/Custom/5f6ee57f-f5e1-4cac-86d4-6e68447a0f91.pdf` | `efe9dad731595df9ac5e5a87d2dd9fd76308db92713476251a5e3f9bec74a909` (2026-10-05) | Map in annex credits municipal boundaries to Kosovo Cadastral Agency (KCA), 2024; shows municipality units and seven statistical regions. It is a published map, not machine-readable geometry or a data license. |
| Kosovo Cadastral Agency Geoportal | `https://geoportal.rks-gov.net/portal/main` | No data asset retrieved | Identifies an official geospatial portal. Candidate ArcGIS REST URLs tried at `/arcgis/rest/services?f=json` and `/arcgis/rest/services/AdministrativeUnits?f=json` returned the Angular application shell, not JSON; no public REST/WMS/WFS boundary export or reuse terms were verified. |

## Upstream license/reuse statements

- OpenStreetMap Foundation, OSM copyright/license: `https://www.openstreetmap.org/copyright`; response SHA-256 `8798f9e206b1a0b419f1d554cedd69b7cc3562fd5775424435716622cd4a5905` (2026-10-05; 21,314 bytes). It says OSM data is ODbL 1.0, and separately identifies OSM documentation as CC BY-SA 2.0.
- OpenStreetMap Foundation, license change history: `https://osmfoundation.org/wiki/Licence/About_The_License_Change`; response SHA-256 `03afcd647173e16ef8d21a19c117b4d4cadf514012c9ea2dc8355f5b0345b693` (2026-10-05; 47,779 bytes). It says the data license moved from CC BY-SA 2.0 to ODbL in 2012. Source vintage 2021 is after that change, but its missing OSM snapshot prevents a source-by-source database license audit.
- geoBoundaries API/license metadata documentation: `https://www.geoboundaries.org/api.html`; retrieved HTML response SHA-256 `b60cb9a2de8e2a1bcd82b1c53264de665a1c5f0e6a66b66c3c8206d10bd3baff` (2026-10-05; 18,941 bytes). It calls gbOpen typically CC BY 4.0 compliant while defining `boundaryLicense` as the original source license; this does not resolve obligations inherited from the specific OSM-derived source.
- OSM-Boundaries documentation: `https://osm-boundaries.com/about/documentation`; public indexed page inspected 2026-10-05 says downloaded data follows OSM licensing, explains Planet extracts/database vintages, and requires authentication/credits for downloads. A direct HTTPS retrieval returned 403, so no exact response hash was obtained.
- OSM-Boundaries terms: `https://osm-boundaries.com/about/contact`; public indexed text inspected 2026-10-05 reserves site material and bars reproduction/redistribution. Direct HTTPS retrieval returned 403; no exact response hash was obtained. The relationship between those current site terms and the ODbL status of data delivered by the service remains unresolved for this source.

No KCA vector, OSM-Boundaries export or paid/account-gated service was retrieved. No license compatibility conclusion is made. The two official PDF hashes and law-page hash are retrieval checksums only; their original bytes are not shipped with this packet.

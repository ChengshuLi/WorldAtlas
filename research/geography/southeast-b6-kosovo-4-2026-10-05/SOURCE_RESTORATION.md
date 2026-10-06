# Source restoration and lawful-retention record

Research retrieval date: 2026-10-06. Hashes below identify exact whole response bodies or immutable Git blobs; they do not establish factual accuracy, license compatibility, or permission to redistribute.

## Reuse the retained seven-feature source; do not duplicate it

The original geometry already exists in the merged #422 evidence packet. Use these baseline blobs for internal, bounded research only:

- Source repository: `https://github.com/wmgeolab/geoBoundaries`
- Immutable upstream commit: `9469f09592ced973a3448cf66b6100b741b64c0d`
- Source media URL: `https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/XKX/ADM1/geoBoundaries-XKX-ADM1.geojson`
- Existing baseline path: `data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/gb-XKX-ADM1.geojson`; 1,898,578 bytes; SHA-256 `9b07b08fe0f9ca5a26ddb6de2008ac235b38ffaf069063df9851711c2d358315`.
- Existing metadata path: `data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/XKX-ADM1-geoBoundaries-XKX-ADM1-metaData.json`; 799 bytes; SHA-256 `a912dcaefa1096a6c0af067af9723b2a67c32f5b0147b8198f99751eb591b49c`.
- Existing citation/use notice: `data/regional-review/regional-review-3c4fe25a21fa428d/source/gb/XKX-ADM1-CITATION-AND-USE-geoBoundaries.txt`; 4,316 bytes; SHA-256 `f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5`.
- Existing original source manifest: `data/regional-review/regional-review-3c4fe25a21fa428d/source/source-manifest.json`; 6,787 bytes; SHA-256 `fded0febc8ef8d934b1f7358755b3102ec8043cc027a88ad8106dec8247b7f56`.
- Upstream original geometry LFS SHA is the same `9b07b08...`; metadata LFS SHA is the same `a912dca...`. Verify returned response bytes against these exact lengths/digests. A `raw.githubusercontent.com` fetch may return a small LFS pointer; use the immutable media URL and reject a pointer or any mismatch.

The metadata records `boundaryYear=2021`, `sourceDataUpdateDate=Thu Jan 19 07:31:04 2023`, `buildDate=Dec 12, 2023`, source OpenStreetMap, canonical “Municipalities”, `admUnitCount=48`, license text CC BY-SA 2.0 and malformed `https//` URLs for the source/license links. Preserve these original values; the collection actually contains seven features. Do not treat 2021 as the retrieval date or 48 as the collection feature count.

## Official evidence restored by URL and response hash

No official PDF or law-page bytes are shipped here. Re-fetch the exact URL and compare its response to the recorded SHA if a future review relies on the same retrieval; if it differs, create a new dated source vintage.

| Evidence | Exact URL | Retrieved | Response SHA-256 | What it supports / limit |
|---|---|---:|---|---|
| KAS, *Classification of Statistical Regions in Kosovo*, April 2022 PDF | `https://askapi.rks-gov.net/Custom/baa59b95-af3f-4117-8c84-edc9ef401bf7.pdf` | 2026-10-05 | `aa322791fa3d683e8f054c57551437e754846b5094f4b413879011c152a6cb0f` | 38 municipalities; seven proposed Level III non-administrative regions; pages 4–7 have region memberships. Proposal, not polygon equivalence or reuse license. |
| Official Gazette, consolidated Law 03/L-041 | `https://gzk.rks-gov.net/ActDetail.aspx?ActID=107377` | 2026-10-05 | `4d45a816aaef692e52d037b121cb49f1a4cbcbb81f6fcc4332aa01583e2ba246` (14,622 bytes) | Consolidated legal municipal-boundary framework; published 2025-07-08. HTML is not current vector boundaries. |
| Official Gazette, original Law 03/L-041 | `https://gzk.rks-gov.net/ActDocumentDetail.aspx?ActID=2518&langid=2` | 2026-10-05 | `a44c1ed6b3e0ac3d2e102158122f47b008f79796c088b4bc0f03d6569a44afff` (26,813 bytes) | Original municipal/cadastral-zone descriptions and separate North/South Mitrovica municipalities. Historic text is not a current GIS dataset. |
| KAS 2024 census final-results publication | `https://askapi.rks-gov.net/Custom/5f6ee57f-f5e1-4cac-86d4-6e68447a0f91.pdf` | 2026-10-05 | `efe9dad731595df9ac5e5a87d2dd9fd76308db92713476251a5e3f9bec74a909` | Annex map credits municipal boundaries to KCA 2024. Map is neither vector data nor a reuse license. |
| KCA Geoportal, Administrative Units theme | `https://geoportal.rks-gov.net/portal/main` and `https://geoportal.rks-gov.net/Temat` | inspected 2026-10-05/06 | no data response hash | Identifies an official administrative-units theme, not a retrieved vector. No public download endpoint or applicable data reuse terms verified. |
| KCA Geoportal manual | `https://geoportal.rks-gov.net/assets/documents/Manual-Gjeoportal.pdf` | inspected 2026-10-05 | no retained response hash | Describes administrative-unit and cadastral layers; does not identify a redistributable vector file/license for this task. |
| OpenStreetMap copyright | `https://www.openstreetmap.org/copyright` | 2026-10-05 | `8798f9e206b1a0b419f1d554cedd69b7cc3562fd5775424435716622cd4a5905` (21,314 bytes) | OSM data is ODbL 1.0; documentation has a separate CC BY-SA 2.0 statement. Does not identify the exact source database used for this polygon product. |
| OSM license change history | `https://osmfoundation.org/wiki/Licence/About_The_License_Change` | 2026-10-05 | `03afcd647173e16ef8d21a19c117b4d4cadf514012c9ea2dc8355f5b0345b693` (47,779 bytes) | OSM data moved from CC BY-SA to ODbL in 2012, before the represented 2021 vintage. Missing snapshot still prevents exact lineage confirmation. |
| geoBoundaries API/license documentation | `https://www.geoboundaries.org/api.html` | 2026-10-05 | `b60cb9a2de8e2a1bcd82b1c53264de665a1c5f0e6a66b66c3c8206d10bd3baff` (18,941 bytes) | Product-level CC BY 4.0 statement also says individual boundary source metadata terms must be honored. It does not resolve this source's OSM chain. |
| OSM-Boundaries documentation and terms | `https://osm-boundaries.com/about/documentation` and `https://osm-boundaries.com/about/contact` | inspected 2026-10-05 | no response hash; direct fetch returned HTTP 403 | Indexed documentation describes OSM-derived data; exact historical service record/terms for this source were unavailable. |

## Reused prior packet extracts

This packet carries only the small machine-readable KAS membership extraction and the prior #999 seven-feature crosswalk so reproduction can be repeated without copying the source geometry. Their origin is `0de4b1f` in the repository history; copied bytes and hashes are:

- `prior-kas-extract.json`: 1,811 bytes; SHA-256 `0f33913b6a36b057ecc9d51cbe7e14c11954fc1d3a89565eb63a64ffb4be6fff`. The extraction records its source PDF's hash above; it is not an independently published KAS GIS file.
- `prior-source-crosswalk.json`: 10,417 bytes; SHA-256 `7339a45153c1a7e6f7c594b6c87be2f8b6294e7407ec63ab2598c839bb4cc5e7`. The prior packet marks regional names as name-only correspondence, not geometry identity. Its adjacent source-layer details are context only.

Reuse compatibility for the source polygon remains **unknown**. geoBoundaries describes its generated product as CC BY 4.0 while directing users to source metadata; the metadata claims CC BY-SA 2.0 and points at OSM, whose 2021 data was ODbL. The OSM snapshot, relation IDs, OSM-Boundaries database identifier and exact applicable service terms are missing. Do not infer whether redistribution is allowed or prohibited. No new polygon geometry or official publication was downloaded into this packet.

# Cabinda source checkpoint — 2026-10-05

This is a source-research/restoration checkpoint for issue #896. It does not establish current municipal footprints, certify Cabinda, or approve an import or publication.

## Retained lawful legacy comparison

The four-feature extract in `sources/geoboundaries-2018/cabinda-four-features.geojson` is derived from geoBoundaries `gbHumanitarian/AGO/ADM2`, pinned release commit `9469f09592ced973a3448cf66b6100b741b64c0d`, retrieved 2026-10-05. The original full layer is 161 features and SHA-256 `44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404`; retrieve it from `https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbHumanitarian/AGO/ADM2/geoBoundaries-AGO-ADM2.geojson`. Its stated license is CC BY 3.0 IGO. The retained extract SHA-256 is `539737a4231d6c823a3c3efe823ac8d789042dc6f0bf8cd6f92d6990d5537394`; it contains only the four issue-scoped IDs, all Polygon geometries. The restoration script verifies both the whole-source digest and exact scoped IDs before writing the extract.

The official Gazette Law 14/24 PDF was inspected and hashed, but is not retained because no open redistribution terms were located. Restoration URL: `https://c2a.portais.gov.ao/uploads/Lei_14_24_de_5_de_Setembro_Cabinda_5c86d750e1.pdf`; retrieval date 2026-10-05; SHA-256 `dfaab2fa7059d8447aee3cab492deb94793971883b6a4998dc5353bf3d6e6e6a`.

## Candidate source limits

A public ArcGIS feature service advertised a Cabinda layer based on the Gazette, but item/service/layer license, copyright, and attribution fields were blank. The item was published by `kuyengap_msugis`; publisher organization metadata identifies Michigan State University Online ArcGIS, not an Angolan competent authority. No geometry was downloaded. Metadata response receipts were retrieved 2026-10-05: item `787f98730e8143100abf218dff1fc47806a47cacb13512222a6b68582fa762c0`, municipality layer `4839dd0d3ab05d2824c835306f969bfbf252eea8fa835853107d6a05b769991a`, service `9e2a998d1709e0916261bac270be313a3cf2474c0dd38d4ae8719fb20e4d4210`, publisher `da7edd7d74b40a262e6c8d5440e5350063877515d1c62f9f37dc87e66fffef09`. Retained JSON files are normalized metadata extracts; these hashes identify the received responses, not the normalized files.

The official INE 2024 reports confirm the ten-municipality reporting roster but do not provide reusable vector geometry. The current public-domain geoBoundaries open ADM2 API is 2006 vintage and is not evidence of current 2024 boundaries. See the issue's dated comments for URLs, source hashes, name-level findings, and unresolved access/rights requests.

## Handoff

All four legacy labels match four names in the law roster. This supports name-level crosswalk candidates only; it does not establish identity continuity or footprint persistence. Six statutory names are absent from the four legacy IDs. The remaining requirement is written access/reuse permission for authoritative current ten-municipality vector boundaries or the official annex maps, plus georeferencing instructions/CRS and a lawfully valid evidence-pin contract. No coordinates have been inferred from prose or unlicensed maps.

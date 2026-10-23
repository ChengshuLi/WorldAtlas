# Jordan ADM2 source row: Al-Azraq

**Issue:** [#124](https://github.com/ChengshuLi/WorldAtlas/issues/124)

**Packet:** `regional-review:edbb8a26c777b89d`

**Region pin:** `geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e` (v5)

**Reviewed:** 2026-10-19

**Disposition:** `insufficient-evidence` for current/official territorial fit; this is not a geometry or hierarchy correction.

## Exact scoped subject

| Field | Value |
|---|---|
| Atlas/source member ID | `gb:JOR:ADM2:86222999B33973362353345` |
| Packet province | `framework:province:zarqa:1a6af2ad9aea` — Zarqa, from #124's pinned `province_scopes` roster |
| Inspected source name | `Al-Azraq` |
| Source properties | `shapeID=86222999B33973362353345`; `shapeName=Al-Azraq`; `shapeGroup=JOR`; `shapeType=ADM2`; `shapeISO` is empty |

The exact ID is in #124's 224-member list and in its Zarqa province roster. The retrieved source feature file contains 52 features; each of the 52 Jordan IDs in the issue roster matched exactly one feature by `shapeID` (52/52, no missing or duplicate IDs). This check establishes the source-file join only, not geographic accuracy or complete Jordan administrative coverage.

## Source inspected

The original geoBoundaries feature bytes and companion metadata are retained in `sources/` in this packet. The official ministry record is linked below; its page terms reserve rights, so the HTML response is not included in the PR. A local response snapshot was inspected in the work slot (117,793 bytes; SHA-256 `a80511fc7e437c3ef8bdf3e63fb8b8939788a1694e91a5c370a8245aad9d062d`).

- Feature file: [geoBoundaries JOR ADM2 GeoJSON at pinned commit](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/JOR/ADM2/geoBoundaries-JOR-ADM2.geojson). Retrieved 2026-10-19; 1,267,706 bytes; SHA-256 `d575a50ed8382a67aee5b716c9ca45b35447d857dadb2cf4af74ad936db8dc34`; pinned Git blob is an LFS pointer with SHA-1 `ccb76270cba656d93d9b4ffe7a0332c7ccb2a623` and payload OID matching that SHA-256.
- Dataset metadata: [geoBoundaries JOR ADM2 metadata at pinned commit](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/JOR/ADM2/geoBoundaries-JOR-ADM2-metaData.json). Retrieved 2026-10-19; 787 bytes; SHA-256 `9e77bad84276c5c28a8d2c83c98acbec084c1e8199b0fe74f1aeb6d07436fd6c`; pinned LFS pointer blob SHA-1 `57bc73f6cf5fb2686d4317854d8b570378ade738`.
- Product terms: [geoBoundaries citation and use notice at the pinned commit](https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/JOR/ADM2/CITATION-AND-USE-geoBoundaries.txt). It says the geoBoundaries product and derivatives require CC BY 4.0 attribution and users must additionally cite each boundary's metadata source. This is separate from the file metadata's per-boundary `Public Domain` value.
- Current administrative cross-check: Jordan Ministry of Interior, [Qada Al-Azraq page](https://moi.gov.jo/AR/Pages/%D9%82%D8%B6%D8%A7%D8%A1_%D8%A7%D9%84%D8%A3%D8%B2%D8%B1%D9%82), Arabic, accessed 2026-10-19; page's last-modified field is `09/11/2025`. The breadcrumb places it under the administrative divisions of Zarqa Governorate. The page says Qada Al-Azraq was established on 1996-01-01, lists communities served by it, and gives verbal neighboring-place/border descriptions. The embedded location-map image request returned HTTP 503 when inspected; no geometry was read from it.

The pinned metadata says `boundaryYear=2006`, `boundaryType=ADM2`, `boundaryCanonical=Nahias`, `boundarySource="geoBoundaries, Wikimedia Commons"`, `boundaryLicense=Public Domain`, `sourceDataUpdateDate=Thu Jan 19 07:31:04 2023`, and `buildDate=Dec 12, 2023`. Its `licenseSource` and `boundarySourceURL` values both read `https//commons.wikimedia.org/wiki/File` (missing the colon and without a file-specific path). The geoBoundaries citation notice says the product and derivatives are CC BY 4.0, and instructs users of individual boundary files to cite the source given in each file's metadata. These are distinct claims: the record metadata's per-boundary license is Public Domain, while use of the geoBoundaries product requires CC BY 4.0 attribution.

## Row finding and uncertainty

The inspected record supports that the pinned 2006 geoBoundaries ADM2 product labels this feature `Al-Azraq` and classifies the collection's canonical hierarchy as “Nahias.” The feature has no ISO subdivision code. The Jordan Ministry of Interior independently confirms a current administrative Qada called Al-Azraq under Zarqa Governorate, with establishment date 1996-01-01 and a named settlement roster. This supports a current unit with the same name and parent, but it is not a unique source-to-source identity crosswalk. It does not show that the 2006 polygon corresponds to the current Qada: geoBoundaries' canonical role label is “Nahias,” its metadata cites only an unidentified Wikimedia Commons file, and the Ministry's linked location map was unavailable. The Ministry page gives no boundary coordinates or geometry. The GeoJSON itself has no governorate/parent field; the issue inventory's Zarqa assignment is a scope fact, not evidence of the source polygon's parent.

**Classification:** `insufficient-evidence` for source-to-territory/boundary equivalence. The official record supports the current Al-Azraq administrative entity and Zarqa parent, but the available evidence does not establish that the 2006 ADM2/Nahia polygon is the same unit with the same boundary. A specific upstream map or inspectable official boundary is still needed. No name, parent, footprint, geometry, or canonical record was changed. The remaining 223 packet members and all neighboring rows remain open.

## Reproduction

The retained source file's `shapeID` can be matched to the issue member ID after the `gb:JOR:ADM2:` prefix is removed. The one-to-one Jordan roster check above used the exact pinned issue body and retained source bytes. It did not inspect or validate any polygon coordinates, perform GIS overlay, infer land coverage, inspect the unavailable ministry map, or verify the underlying Wikimedia Commons source.

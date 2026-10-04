# Alaska settlement-response verification follow-up

Issue: [#676](https://github.com/ChengshuLi/WorldAtlas/issues/676)

Source packet: [#603 / PR #672](https://github.com/ChengshuLi/WorldAtlas/pull/672), merged at `529deb71f911e9a675b49a11d1deaff1d894d1b7`.
Owned scope: the eight exact physical-fragment IDs below. This packet preserves the original #603 packet and #486 inherited evidence unchanged. It proposes a strict reproducer; it does not change shared geometry, hierarchy, or settlement attributes.

## Assigned-subject audit

All eight IDs occur exactly once in the #603 scope and assessment, the inherited #486 parent assessment, and the pinned parent polygon file. The verifier requires the exact ID set and unique polygon occurrence before a source request. Each child chain matches the inherited parent assessment at every ID/name/parent link:

| Assigned subject | Full parent chain after the fragment | DCRA live point hits |
| --- | --- | ---: |
| `atlas:physical:15fa62117dba20fdd7a3` — Yukon-Koyukuk · Beringia upland tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:2e1dd8f380b0a4f65ad9` — Yukon-Koyukuk · Ogilvie-MacKenzie alpine tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:3c48debb2430313aff99` — Yukon-Koyukuk · Beringia lowland tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:674981b93623e9cbe385` — North Slope · Interior Alaska-Yukon lowland taiga | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:770135c5de8a7faad962` — North Slope · Interior Yukon-Alaska alpine tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:d5c6a8a99d213d352ffc` — Nome · Interior Yukon-Alaska alpine tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:db25f36496f102a4e01b` — Yukon-Koyukuk · Alaska-St. Elias Range tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |
| `atlas:physical:f1337f9008d75f1a400d` — Bethel · Alaska-St. Elias Range tundra | Alaska → Pacific → Western North America → Northern America → North America | 0 |

The parent chain IDs are respectively province `framework:province:alaska:4057e2fddbc5`, area `framework:area:pacific:31aced66907e`, region `framework:region:western-north-america:d2a1c2775a57`, subcontinent `framework:subcontinent:northern-america:477e054b32f2`, and continent `framework:continent:north-america:1ca27616f338`. These eight subjects are existing physical fragments, not administrative remainders or new subdivisions. No settlement absence or geographic correction is inferred from zero DCRA point hits.

## Source and vintage record

The authoritative service is Alaska DCCED Division of Community and Regional Affairs (DCRA), [Communities item](https://www.arcgis.com/home/item.html?id=95a724c867364ff88def7d3d0b0672f5), [item metadata](https://www.arcgis.com/sharing/rest/content/items/95a724c867364ff88def7d3d0b0672f5?f=json), and [Alaska Communities point layer](https://maps.commerce.alaska.gov/server/rest/services/Community_Related/Community_Locations_and_Boundaries/MapServer/0). The item metadata was modified 2024-11-12. It says DCRA provides Community Database Online data as-is for information/research and does not provide an explicit open reuse license. Therefore this packet does not retain the raw point response. It records retrieval instructions, byte hashes, sizes, counts, response summaries and the source's stated limits only.

Layer metadata fetched 2026-10-04 UTC / 2026-10-03 America/Los_Angeles: 7,137 bytes, SHA-256 `e3aa7fea2abf25d817a3c6007a892665e12864fde800ee94dbcf07b4e580b408`; layer `Alaska Communities`, type `esriGeometryPoint`, `maxRecordCount=2000`, pagination supported, `isDataArchived=false`. Item metadata fetched the same date: 5,837 bytes, SHA-256 `b75e19baedf8ae51b0cc1c1aa1244b342217b4345d3c17e71b003b2d36fdad3c`. Metadata bytes are not retained; these canonical endpoints are the restoration instructions.

The original #603 source receipt records a 2026-10-03 UTC query response of 415,447 bytes, SHA-256 `a1c13f271c4a67ab470b99a7adfe5979b2673724fd69a7bde54c61aefa4b5654`, with 487 records. The raw bytes were not retained in #603. A new read-only retrieval on 2026-10-03 America/Los_Angeles (2026-10-04 UTC, exact UTC timestamp in `vintages/2026-10-03-live.json`) returned 487 validated features in one page; its byte length and SHA-256 exactly match that receipt. This independently reproduces the recorded content fingerprint and count. It cannot establish the original capture time: the service reports no historic archive and does not expose a historic-moment query. Future runs report a separate timestamp and simply record whether their live response matches the earlier fingerprint; a changed live response is not treated as corruption or as the original vintage.

The response inventory was requested for the documented envelope `xmin=-180,ymin=51,xmax=-129,ymax=72` in EPSG:4326 using `where=1=1`, point layer object IDs, and complete offset pages. The verifier first fetches exact object IDs, then validates the union of paginated GeoJSON feature IDs against that inventory. It checks schema, nonempty inventory/pages, `exceededTransferLimit`, duplicate object/community IDs, valid point coordinates, and returned feature count. The source distinguishes Community (`CommunityAreaTypeID=1`, a DCRA assistance-program definition) from Place of Interest (`2`, a mixed set including CDPs/localities, seasonal sites, vacant former places, service/resource sites and other types); it is not a comprehensive current-settlement census. A point hit would be a review lead, not proof the physical fragment is a settlement. Zero hits cannot establish absence.

## Reproduction and controls

Run from the repository root with Python 3, Shapely 2.x, pyproj and the repository's installed requirements:

```sh
python3 research/geography/alaska-settlement-verification-followup/verify.py --self-test
python3 research/geography/alaska-settlement-verification-followup/verify.py
```

The first command checks positive one-hit and zero-hit geometries, absent and empty feature lists, partial pages, transfer-limited pages, duplicate response/object/community IDs, missing/duplicate subjects, changed polygon baseline bytes, and invalid polygons. The second verifies immutable inputs before contacting the current endpoint. To retain a new summary, pass a previously unused path under this owned directory with `--output`; the script refuses to overwrite. It does not save feature-response bytes.

The PR's current base is `e9aa7c1da6ae6c2aec1c1580f4b0265110d6f6f2`. Main advanced from `038d611ee5c275812d53af044f389e85e0f303f9` through `df7f37ac91f6c3897ad4d23cfb166bc308a1c5ef` to this base while the PR was under review; I checked the assigned #603/#486 source paths across those advances and their pinned bytes were unchanged. The verifier uses the actual PR-base commit and checks the exact whole-file sizes and SHA-256 for the #603 scope, assessment and source receipt, and the #486 scope, assessment, source registry and compressed polygon collection; validates exact eight-ID scope and assessment lists; compares all eight full parent chains; and verifies one valid, nonempty Polygon/MultiPolygon for each subject. GeoJSON coordinates are interpreted longitude then latitude in WGS84 and checked with `worldatlas-evidence-geometry-v1`; Shapely/GEOS `intersects` is a topological point-in-footprint screen, not an area, ownership, or population calculation.

Control results are retained under `controls/`; the separately timestamped live summary is under `vintages/`. The original #603 query script, response receipt, assessment, and source evidence remain untouched.

## Findings and limits

- The verifier defect is repaired in this proposed evidence packet: absent, empty, malformed or incomplete responses cannot become a successful zero-hit result, and baseline descriptors/parent context are checked before spatial analysis.
- The fresh query returned 487/487 inventory features and zero hits for all eight assigned subjects. It exactly matches the old recorded response digest, size and count, but its later live access does not certify the old capture timestamp.
- The DCRA source does not support a comprehensive conclusion about settlement absence, and the source's category definitions mix administrative/statistical places with a broad set of points of interest.
- No result differences were found in this live retrieval. Any changed future vintage must receive its own dated summary and row-level review; it must not overwrite this receipt.
- The current historic-provenance limit is explicit and bounded: independently proving the original UTC capture time would require a lawful dated archive or a source-published historical export. The service currently reports no archive. That is not inferred evidence of settlement absence and does not justify modifying shared boundaries or hierarchy.
- Bounded follow-up recommendation: if an audit later requires the original UTC capture timestamp, seek a lawful DCRA archive or source-side request log. Until such dated provenance exists, retain that point as unresolved; the matching current digest does not supply a timestamp.

Evidence receipt and source limits are recorded in `evidence-quality.json`. This packet is research evidence only; it does not approve the regional branch, authorize imports, or alter published geography.

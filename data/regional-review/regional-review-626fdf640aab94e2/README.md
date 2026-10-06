# Issue #395 research packet: West Siberian Russia

Research snapshot: 2026-10-06 UTC. Atlas baseline: `origin/main` commit `8e1162e3e364cebdec700ec796e2730379494922`. Issue #395 owns exactly 210 pinned member IDs under `data/regional-review/regional-review-626fdf640aab94e2/`. The issue scope digest is recorded in `baseline/issue-scope.json`; all edits and findings in this packet stay within its owned path.

The exact sorted member-ID list digest is `416cf260d42cd9b2a05f8f5df893ae708bf03b2d8df6000352faf9fcce88d6d0`. The retained `baseline/issue-scope.json` byte hash is `bd01cfec3fa206b2e99dd3505c923fbec185be16842da260b440800fa9cd2117`.

This packet assesses source lineage and flags uncertainties. It does not certify the seven provinces, the complete West Siberian region, or any current legal boundary. No core geography or production data was changed.

## Reproduce

Use Node.js 24 or later. From repository root, after restoring the two full geoBoundaries input files as described in [Source register](#source-register):

```sh
node data/regional-review/regional-review-626fdf640aab94e2/reproduce-current-lineage.mjs
node data/regional-review/regional-review-626fdf640aab94e2/extract-pinned-source.mjs data/regional-review/regional-review-626fdf640aab94e2/sources/geoboundaries-rus-adm2-2017-original.geojson
node data/regional-review/regional-review-626fdf640aab94e2/extract-parent-baselines.mjs
node data/regional-review/regional-review-626fdf640aab94e2/verify-area-partition.mjs
node data/regional-review/regional-review-626fdf640aab94e2/assess-members.mjs
python3 data/regional-review/regional-review-626fdf640aab94e2/check-parent-source-coverage.py data/regional-review/regional-review-626fdf640aab94e2/sources/geoboundaries-rus-adm2-2017-original.geojson
python3 data/regional-review/regional-review-626fdf640aab94e2/screen-parent-area-ratios.py
```

The scripts check the pinned base commit, issue IDs, raw source hashes and exact extracted feature sets. The raw full-country files are intentionally not included in this packet: they are 120,489,189 and 59,162,098 bytes, respectively, and exceed GitHub's regular file limit. Their hashes and restore URLs are retained below. Scoped original features, sufficient to inspect every in-scope unit and parent, are preserved in the packet.

## Findings

`findings/member-assessments.json` contains one assessment for each of the 210 pinned IDs (165 justified for source lineage only, 34 insufficient evidence, 11 correction needed). These labels do not certify current territorial meaning, legal status, geography, boundary accuracy, or completeness.

* All 199 native administrative rows map by source identifier to an original feature in the pinned geoBoundaries RUS ADM2 file. The remaining 11 Atlas physical-region rows are ecological portions derived from just four administrative source districts. Each is nevertheless assigned the Raion role and a district-tier selection rationale. This semantic/source-role contradiction needs an engineering and product decision; this packet does not restore whole districts or alter geometry.
* Of the 199 native units, 25 source names identify city/urban okrugs while Atlas metadata calls them Raion. They need a current, authoritative hierarchy crosswalk. Another nine native units have multiple geometry components and are flagged for component-level review; the 25 and nine categories are disjoint in the 34-row insufficient-evidence assessment. The 45-component Yamalsky and 12-component Tazovsky source features merit particular scrutiny. The MChS Yamal-Nenets page confirms islands in internal sea waters can belong to municipal districts, but does not establish that every component in these source geometries is correct.
* Seven Atlas province parents match seven source ADM1 features by source ID and name. Counts match the issue's declared full-province membership counts. The parent extract includes their original geometries. Omsk has four components and Yamalo-Nenets has 148; count and name matching alone do not certify boundaries.
* A spatial source-coverage comparison found exactly 203 ADM2 source unit polygons with non-trivial area overlap in the seven source ADM1 parents. They match the 203 distinct original administrative source IDs represented by the 199 native Atlas members plus the four source units from which the 11 ecological portions derive. Every parent set matches exactly: 69 Altai Krai, 22 Khanty-Mansiysk, 20 Tomsk, 35 Novosibirsk, 33 Omsk, 13 Yamalo-Nenets, and 11 Altai Republic. The reproducible comparison uses Shapely 2.1.2, source GeoJSON longitude/latitude planar intersection area, and a documented 1e-6 area-fraction cutoff. This supports completeness only against this pinned source dataset and these parent geometries, not legal or present-day boundaries.
* The size screen compares all 210 Atlas geometries and 203 distinct source ADM2 shapes with their source ADM1 parent. No original unit exceeds 28.2% of its parent (largest: Kargasok region in Tomsk); 18 exceed 10%. These larger source units are listed individually in `findings/size-screen.json` and crosswalked in `findings/source-crosswalk.json`. It found no province-sized whole-source shape and no material mismatch between the source units and parent extents at its stated tolerance. This relative-size screen cannot establish legal hierarchy and is not an island/omission check.
* The archived geoBoundaries ADM2 metadata declares 2,328 units, while its complete pinned GeoJSON has 2,327 features. This discrepancy is unresolved and may affect broader source completeness. Do not represent the source as complete based on this packet.
* “2017” is the source's represented boundary year, not the archive's creation date: its metadata records source data updated 2023-03-03 and a 2023-12-12 build. This does not show the boundaries remain current. No authoritative source retrieved here establishes all current municipal roles and boundaries for all seven provinces.
* The intended West Siberian area membership is partial across three packets: #394 has 26, #395 has 210, #396 has 34. `findings/area-packet-partition.json` validates their disjoint union against the pinned 270-ID area roster. That is an assignment cross-check, not a geography validation. #396 has exhausted its PR budget; see its issue for its unresolved checkpoint.

The exact 11 ecological fragments and four source parents are in `findings/source-crosswalk.json`; ecoregion identities and the FID-vs-ECO_ID negative control are retained under `sources/` and `findings/`. The four ECO_ID features are Urals montane forest and taiga (719), West Siberian taiga (720), Northwest Russian–Novaya Zemlya tundra (776), and Yamal–Gydan tundra (784). ArcGIS item's listed license is CC BY 4.0; the administrative districts underlying these fragments retain the geoBoundaries source metadata's OpenStreetMap/Wambacher attribution and ODbL license. The ArcGIS data describes ecoregions, not administrative units.

## Source register

Hashes are SHA-256 of exact retained or retrieved bytes. Retrieval timestamps are local filesystem capture times, equivalent to America/Los_Angeles; dates are also represented in the UTC research snapshot above. Metadata's source vintage and license claims are transcribed rather than independently certified.

| Evidence | Source / retrieval | SHA-256 and size | Meaning and limits |
|---|---|---|---|
| Full ADM2 archive (not retained) | [Pinned geoBoundaries commit](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d), retrieved 2026-10-05 22:51:01 PDT. Restore: `curl --fail --location 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson' --output data/regional-review/regional-review-626fdf640aab94e2/sources/geoboundaries-rus-adm2-2017-original.geojson` | `74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0`, 120,489,189 bytes | Raw SHA verified before extraction. 2,327 actual features vs metadata-declared 2,328. Metadata says boundary year 2017, source update 2023-03-03, build 2023-12-12, source OpenStreetMap/Wambacher, ODbL 1.0. |
| ADM2 metadata | Same pinned commit; retained | `2064a236e3473d76adf00729b4482a22ffefae22a40364a4cfe78ef43ce3c672`, 815 bytes | Original source metadata and license declaration. |
| Scoped ADM2 original features | Extracted from full archive; retained | `7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129` | 203 original features: 199 direct members plus four source districts underlying ecological fragments. |
| Full ADM1 archive (not retained) | [Pinned geoBoundaries commit](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d), retrieved 2026-10-05 22:59:54 PDT. Restore: `curl --fail --location 'https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM1/geoBoundaries-RUS-ADM1.geojson' --output data/regional-review/regional-review-626fdf640aab94e2/sources/geoboundaries-rus-adm1-2017-original.geojson` | `b86ab28823569a4ec881091b0c8608ae31194cb2b195943b8b34fbd56f492320`, 59,162,098 bytes | Raw SHA verified. 83 features; metadata also says 83. Seven scoped province geometries extracted. |
| ADM1 metadata | Same pinned commit; retained | `5c8f45f4965693016d70e08dae4c195d614644eed8c8fa3dca5948c9d89b84a1`, 856 bytes | ADM1 source metadata. |
| Scoped ADM1 parent features | Extracted; retained | `4dab95fa1bbb8aa0ffeeecca9bc269ece139aab4368faff8ed2d0890c05d6602` | Seven source province geometries. |
| Current Atlas members | Pinned main commit; exact selected feature set retained | `44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070` | 210 current features reconstructed from 34 pinned geography parts. Reproducer and per-row source crosswalk identify each. |
| geoBoundaries commit record | Pinned GitHub API commit response; retained | `5f1b2549c5741c6708fae329dc3fe25c0bdb3185dfca34575fe8bffdf22da6ce` | Commit `9469f09592ced973a3448cf66b6100b741b64c0d`, 2023-12-13, “gB Core Data Update 2023-12-12 23:03”. |
| ArcGIS item | [RESOLVE Ecoregions and Biomes](https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef), retrieved 2026-10-05 22:51:28 PDT | `9ccbb076714184b4565ca6546f988aca1fad7afabf17191f920f3da64ba85340`, 9,587 bytes | Item owner/access info and CC BY 4.0 license listing. |
| ArcGIS layer metadata | Same ArcGIS item, retained | `d1feffd594812affdc08e089607bab2ed76e256ba7748784d37536797a777d4e` | ECO_ID unique key; source's data last edit 2022-01-27; schema edits are newer. |
| ArcGIS query request | REST query by `ECO_ID`; retained | `cc42c18d35c06b794914ccbfe11ebe8c74d39c26c5b7ae3e35ad9935c187f998` | Exact four ECO_ID values and request parameters. |
| Four ecoregion features | ArcGIS queried by ECO_ID; retained | `95557a6db0dffeda4786e3961a2daf3aa977160adf09dbada2ec73cc8305a3b3` | Identity evidence for four ecoregion fragments. Negative control shows using those integers as FID yields different regions. |
| FID negative control | Same ArcGIS layer queried by FID; retained in `findings/` | `8f0ad61cc693e5d39db8d06adcc0a8cc19327d6e1e8fe5efa8b76e98160dd554` | Records that integer-key confusion returns different geographic identities. |
| MChS Yamal-Nenets profile | [Russian Ministry of Emergency Situations, regional profile](https://89.mchs.gov.ru/glavnoe-upravlenie/harakteristika-subekta), retrieved 2026-10-05 23:10:05 PDT | `a73397b83e44731675ce5ddda196f29a752696975840b03524344674c9de22fa`, 91,038 bytes | Official current page describes 13 municipal entities, six city districts and seven municipal districts; CC BY 4.0 footer. Not a full crosswalk for the issue scope. |
| MChS Yamal islands note | [Russian Ministry of Emergency Situations, district islands note](https://89.mchs.gov.ru/deyatelnost/press-centr/novosti/3921938), retrieved 2026-10-05 23:10:07 PDT | `b325387ce5f8e18217aaf822afef33e2c8969c8b85b6fae64672abf5303fe723`, 104,060 bytes | Supports that some internal sea islands belong to municipal-district territories; does not validate all multipart components. CC BY 4.0 footer. |
| Rosstat OKATO source discovery | [Rosstat open data](https://rosstat.gov.ru/opendata/7708234640-okato) and [classification page](https://www.rosstat.gov.ru/classification?print=1), checked 2026-10-05 | No source bytes retained; local TLS issuer validation failed | Official search results identify Federal State Statistics Service and a 2026-08 dataset update. Retrieval failed without bypassing TLS; no claims based on uninspected dataset bytes. A verified current OKATO/municipal source is a follow-up. |

## Reproduced finding files

These result hashes identify the exact checked outputs in this packet. `current-lineage.json` and `sources/current-scoped-features.geojson` were regenerated twice from the same pinned main files with matching SHA-256 values, confirming byte-for-byte determinism. The original source-coverage comparison is reproducible from the full ADM2 archive restored by the command above; output lists every matched source unit by parent.

| Result | SHA-256 |
|---|---|
| `baseline/issue-scope.json` | `bd01cfec3fa206b2e99dd3505c923fbec185be16842da260b440800fa9cd2117` |
| `findings/current-lineage.json` | `0781ff358d8e1e574eaecf1deea1b7fb1931a890105b17468ffecbe20d6f4874` |
| `sources/current-scoped-features.geojson` | `44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070` |
| `findings/source-crosswalk.json` | `c53666d041cfbf6e87ffe67d3cf64f78bbea10a66de2fd6e49a64b1e687c913b` |
| `findings/member-assessments.json` | `55e20fc63247dd81a3d23dac405811c34e7dee79dc7b7a72712febbe813d913f` |
| `findings/parent-crosswalk.json` | `e18b8402857f6633f3458140a697363de946742a6b75c78a4471d6e80820c432` |
| `findings/parent-source-coverage.json` | `b33c95268e368ec54ed2f6031367a1189bcb58bd3b9cfd2eb8331e723a0cc210` |
| `findings/area-packet-partition.json` | `809b8ad3a97652b957974e3f986c9e2e65e10d40924dbc621a7d58648895a6b1` |
| `findings/size-screen.json` | `ce91549ffcd0676ef7d79c9414ff11ecf8f60f411bd97f58632655c1db12d91f` |

## Follow-up / handoff

1. Engineering: decide whether the 11 `atlas:physical` items belong in an administrative district roster. Keep their source lineage and current IDs available; any removal, relabeling, restoration, or boundary change needs a separately owned correction with exact source and dependent-region impact review.
2. Research: obtain a TLS-verified, dated, authoritative national or regional hierarchy and boundary source covering all seven provinces, crosswalk the 25 city/urban okrugs and compare all 199 native units including their parent relationships.
3. Research: inspect multipart components against authoritative sources, including all islands and separated areas; source multipart representation and a single MChS islands statement are not sufficient proof.
4. Source stewardship: resolve the 2,328-vs-2,327 ADM2 metadata/data discrepancy with geoBoundaries; coordinate with #394/#396 and the regional source owner so the issue is handled once.
5. Do not certify the 270-ID West Siberian region or close its parent based on this packet. Preserve the #396 checkpoint; its issue records budget exhaustion and remaining work.

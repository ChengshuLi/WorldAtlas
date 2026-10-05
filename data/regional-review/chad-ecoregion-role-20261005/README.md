# Chad ecological-fragment role and predecessor lineage

**Issue:** #875 · **Baseline:** `e063b72150b294898d83277d04a5dfc165600664` · **Worker:** `worldatlas-geography-875-20261005-r1-3b79b0d1`

This packet covers the exact 17 Atlas physical IDs in #875. It is source-role and predecessor research only. It does not approve the ecological footprints, a Chad region, an administrative boundary, a hierarchy change or historical imports. The row-level lineage, metrics, original source retrieval receipts, preserved-release context and proposed engineering metadata are in `vintages/20261005-r4/lineage-assessment.json`.

## Finding

The existing Atlas metadata is internally inconsistent. All 17 records have `source_role: "Departments"` and an administrative selection rationale, but their `source_id` points to one of five 2017 RESOLVE ecological features. Each record's `source_member_ids` points to one of six 2019 TCD ADM2 department features. The Atlas names themselves join a department name and an ecological feature name. This supports a composite lineage description: an ecological fragment with an administrative predecessor. It does not identify the exact historical clipping recipe or establish that the fragments are complete ecological units or appropriate subdivisions at the current Atlas tier.

The 2017 RESOLVE item says that ecoregions represent ecosystems and distinct biodiversity assemblages, use natural rather than political boundaries, and cover 846 terrestrial ecoregions in 14 biomes and 8 realms. Its referenced 2017 paper likewise treats the 846 units as terrestrial ecoregions for conservation analysis ([Dinerstein et al., *BioScience* 67(6), 534–545](https://academic.oup.com/bioscience/article/67/6/534/3102935)). The selected attributes report `CC-BY 4.0`. The names and source IDs therefore describe ecological source features, not whole administrative departments. The retained item and layer response hashes and the exact five-feature query are listed below and in the manifest.

### Exact 17-member crosswalk

| Atlas ID suffix | RESOLVE ECO_ID · name | 2019 TCD ADM2 predecessor | 2017 ADM1 parent screen | Existing Atlas parent |
| --- | --- | --- | --- | --- |
| `039e9aed4c3f60bdb4b3` | 844 · Tibesti-Jebel Uweinat montane xeric woodlands | Tibesti Ouest | Tibesti | Tibesti |
| `1a8dfa5d55e056663801` | 53 · Sahelian Acacia savanna | Fada | Ennedi-Ouest | Ennedi-Ouest |
| `211ad3000d0e261c1959` | 53 · Sahelian Acacia savanna | Am-Djarass | Ennedi-Est | Ennedi-Est |
| `45fbb334fdad853f2c06` | 822 · East Sahara Desert | Tibesti Ouest | Tibesti | Tibesti |
| `49cee21465f10da9661b` | 842 · South Sahara desert | Am-Djarass | Ennedi-Est | Ennedi-Est |
| `4ef653826b687f699627` | 842 · South Sahara desert | Borkou Yala | Borkou | Borkou |
| `6fb3186a475bbf01eafd` | 822 · East Sahara Desert | Tibesti Est | Tibesti | Tibesti |
| `9e00def6045964a40a34` | 844 · Tibesti-Jebel Uweinat montane xeric woodlands | Tibesti Est | Tibesti | Tibesti |
| `a22d3e30f8f05346e690` | 53 · Sahelian Acacia savanna | Borkou | Borkou | Borkou |
| `b5f3e1387c85754a83e2` | 842 · South Sahara desert | Fada | Ennedi-Ouest | Ennedi-Ouest |
| `bb2738933d8402555a90` | 823 · East Saharan montane xeric woodlands | Am-Djarass | Ennedi-Est | Ennedi-Est |
| `cb3b4c07ca149f790a56` | 823 · East Saharan montane xeric woodlands | Fada | Ennedi-Ouest | Ennedi-Ouest |
| `cfe1c57c717a4f565b55` | 842 · South Sahara desert | Tibesti Ouest | Tibesti | Tibesti |
| `d6cf62f7d9d4452b2869` | 842 · South Sahara desert | Tibesti Est | Tibesti | Tibesti |
| `e19768af527b61d7a0e8` | 842 · South Sahara desert | Borkou | Borkou | Borkou |
| `e74339c4e4f9d2bab2fc` | 53 · Sahelian Acacia savanna | Borkou Yala | Borkou | Borkou |
| `f580491d6010c19d648c` | 53 · Sahelian Acacia savanna | Tibesti Ouest | Tibesti | Tibesti |

The six predecessor IDs, parent candidates, neighboring same-tier source units and all feature-level measured values are fully qualified in the JSON by exact source feature IDs. The 2019 source file contains 70 ADM2 departments; the parent comparison file contains 23 ADM1 shapes. Immediate neighboring ADM2 units were enumerated from positive-length shared polygon boundaries (EPSG:4326 planar length threshold `> 1e-6°`), excluding point-only contacts. They are a source-version granularity screen, not a claim about current borders.

| 2019 predecessor | TCD ADM2 source ID | Atlas portions | 2017 ADM1 top-overlap candidate | Same-tier source neighbors |
| --- | --- | ---: | --- | --- |
| Am-Djarass | `50815135B96833037498211` | 3 | Ennedi-Est (99.9783%) | Fada; Mourtcha; Wadi Hawar |
| Borkou | `50815135B4564368173337` | 2 | Borkou (99.8128%) | Barh-El-Gazel Nord; Batha Est; Batha Ouest; Biltine; Borkou Yala; Fada; Mourtcha; Nord Kanem |
| Borkou Yala | `50815135B13621547433724` | 2 | Borkou (99.9146%) | Borkou; Fada; Nord Kanem; Tibesti Est; Tibesti Ouest |
| Fada | `50815135B99861554638026` | 3 | Ennedi-Ouest (99.9985%) | Am-Djarass; Borkou; Borkou Yala; Mourtcha; Tibesti Est |
| Tibesti Est | `50815135B39039287340708` | 3 | Tibesti (99.9984%) | Borkou Yala; Fada; Tibesti Ouest |
| Tibesti Ouest | `50815135B44379234996248` | 4 | Tibesti (99.7794%) | Borkou Yala; Tibesti Est |

## Source role, vintage and reuse terms

- **RESOLVE ecological layer:** item “RESOLVE Ecoregions and Biomes,” layer “Biomes and Ecoregions 2017”; exact `ECO_ID` set 53, 822, 823, 842 and 844. Item metadata, layer metadata and query bytes were retrieved 2026-10-05 at 04:46:11–04:46:13 UTC. The retained query is 3,778,571 bytes, SHA-256 `0602ed638e259b81e2ec8c7a48552f2e612c753ba5dce4c83fc0868f40436de0`. The item response records RESOLVE/Esri attribution and a [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/); selected feature attributes report `CC-BY 4.0`. Reuse must retain attribution, license link and modification indication. The ArcGIS service is mutable; this packet pins the retrieved bytes. The item labels the product 2017, while its captured layer response reports a later data-edit timestamp. The product vintage label is not evidence that the service has never changed since 2017.
- **TCD predecessor layer:** the geoBoundaries file is pinned to repository commit `9469f09592ced973a3448cf66b6100b741b64c0d`; the 70-feature ADM2 source was retrieved 2026-10-05 at 04:45:38 UTC, SHA-256 `be3fd41eebe73189f52bca21150af159a3b88bb0f7784315bc0c3fab7ae00c35`. The retained geoBoundaries metadata snapshot reports OCHA Chad, boundary year 2019, concept “Departments,” 70 units and [CC BY 3.0 IGO](https://creativecommons.org/licenses/by/3.0/igo/). The source register preserves the original restoration URL and the mutable-metadata response hash `5abed3e7988689c0ded5f705b388e13ff03b0d77b23a6d3c92ec56019a1cea28`. Attribute source credit to OCHA Chad and geoBoundaries; retain the license notice and identify modifications.
- **ADM1 parent screen:** the retained 23-feature ADM1 geometry is a different 2017 source from OpenStreetMap/Wambacher, retrieved 2026-10-05 at 04:48:30 UTC, SHA-256 `bb27be043ba03e9166e34f08816e9cfc9639247c20ab548b6536baf2ee7e532b`. Its source metadata records [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), not the 2019 ADM2 layer’s CC BY 3.0 IGO terms. ODbL requires attribution and has share-alike conditions for adapted databases; keep its source and reuse obligation distinct. Because ADM1 is 2017 and ADM2 is 2019, the parent result below is explicitly only a geometric candidate screen, not a same-vintage official crosswalk.

The immutable original query and administrative files remain in the #462 packet; this packet references and hashes them instead of making copies. The 2019 administrative and 2017 RESOLVE datasets retain separate attributions and license obligations. The derived packet does not purport to sublicense either source or settle legal compatibility questions for future database integration.

## Overlay reproduction and limits

`reproduce.py` reads only immutable baseline commit `e063b72150b294898d83277d04a5dfc165600664`; it verifies the issue’s four file-byte pins, the actual Atlas subject-containing file (`data/geography/part-23.json`), agreement with the retained #462 member geometries, the exact five ecological source features and all 80 geometry metrics. Run it with Python 3.12.14 and the repository’s `numpy==2.3.5`, `shapely==2.1.2`, `pyproj==3.7.2` pins:

```sh
python data/regional-review/chad-ecoregion-role-20261005/reproduce.py --check
```

The calculated overlays use Shapely topology on EPSG:4326 coordinates and the repository’s `worldatlas-evidence-geometry-v1` shared helper for WGS84 straight-source-edge ellipsoidal area (`m²`). The two invalid original RESOLVE geometries (ECO_ID 53 and 842) remain unchanged in their retained files. For measurements only, the script makes explicit in-memory `make_valid()` diagnostic clones and unions their polygon components; no repaired geometry is exported or treated as authoritative. Independent positive and negative controls and two-run generator reproducibility receipts are in the vintage directory.

| TCD ADM2 predecessor | Atlas portions | New WGS84 fragment-union coverage | Unrepresented source area |
| --- | ---: | ---: | ---: |
| Am-Djarass | 3 | 99.686645% | 227.6 km² |
| Borkou | 2 | 99.998425% | 1.1 km² |
| Borkou Yala | 2 | 99.998749% | 1.0 km² |
| Fada | 3 | 99.850445% | 155.3 km² |
| Tibesti Est | 3 | 99.770734% | 286.2 km² |
| Tibesti Ouest | 4 | 99.925938% | 63.8 km² |

These ratios are geometric correspondence screens; even a small fractional gap may cover hundreds of square kilometres. The inherited #462 report used planar square degrees and recorded 99.6833%–99.9988% coverage. That exact prior report was independently regenerated with its recorded Shapely 2.0.7 method and matched the retained `geometry-audit.json` byte-for-byte (SHA-256 `76dbc998e16051fc592f97c77e5dbd368990a3b112879d1d7d601e3bdcab92d5`). The new ellipsoidal ratios are a separate method and should not be substituted into the inherited audit.

Per-fragment overlays compare the Atlas footprint with its TCD ADM2 source feature, RESOLVE ecoregion, and their geometric intersection. Measured coverage of each expected intersection ranges from 98.9278% to 99.9854%, rather than exact equality. This near correspondence supports the dual lineage, but the deviations and invalid original ecology geometries mean that the historic construction recipe cannot be asserted. A tiny positive overlap screen exists among some fragments; it is recorded rather than converted to a claim that the subdivision is topologically exact.

The 2017 ADM1 parent overlay agrees by normalized name with all six current Atlas parent slugs and covers 99.7794%–99.9985% of the paired 2019 ADM2 source units. The source-vintage mismatch, differing licenses, small cross-boundary overlap/slivers and lack of a dated national parent-code crosswalk prevent this from proving legal or current parentage.

## Engineering handoff and unresolved questions

For exactly these 17 rows, consider updating descriptive provenance to the row-level proposal in the JSON:

- `source_name`: `RESOLVE Ecoregions and Biomes (2017)`
- `source_role`: `Ecological fragment`
- `selection_reason`: identify that row’s RESOLVE ECO_ID/name and its linked 2019 TCD ADM2 predecessor ID/name; say the department is lineage, not the selected whole-unit boundary; retain the explicit uncertainty about clipping recipe, completeness and tier suitability.

Preserve every Atlas ID, `source_id`, `source_member_ids`, geometry, parent and released hierarchy/footprint digest. Engineering should first confirm the intended schema meaning of these metadata fields and review the original assembly history; this source packet authorizes neither geometry changes nor publication. No national code crosswalk, official current geometry, exact generation script, source-complete ecoregion tiling, or final Atlas tier justification was found in the scoped retained evidence. Keep those findings open for any later correction decision.

## Original evidence and restored sources

| Evidence | Original restoration / source URL | Captured hash |
| --- | --- | --- |
| RESOLVE item metadata | [ArcGIS item REST](https://www.arcgis.com/sharing/rest/content/items/37ea320eebb647c6838c23f72abae5ef?f=json) | `695914f9daa43676c980525ad6680c9e784b8445f22a9d9d983adef7dd5a5c9a` |
| RESOLVE layer metadata | [FeatureServer layer 0](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0?f=json) | `4ae61d5e18ee8d02203dda087805737a25cdfcf48a1f31567c92c09572d8a5e3` |
| RESOLVE selected five features | [Exact ECO_ID query](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0/query?where=ECO_ID%20IN%20(53%2C822%2C823%2C842%2C844)&outFields=*&returnGeometry=true&f=geojson&outSR=4326) | `0602ed638e259b81e2ec8c7a48552f2e612c753ba5dce4c83fc0868f40436de0` |
| TCD ADM2 source | [Immutable geoBoundaries commit `9469f095`](https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/TCD/ADM2/geoBoundaries-TCD-ADM2.geojson) | `be3fd41eebe73189f52bca21150af159a3b88bb0f7784315bc0c3fab7ae00c35` |
| TCD ADM1 parent-screen source | [Immutable geoBoundaries commit `9469f095`](https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/TCD/ADM1/geoBoundaries-TCD-ADM1.geojson) | `bb27be043ba03e9166e34f08816e9cfc9639247c20ab548b6536baf2ee7e532b` |
| OCHA COD-AB context | [HDX Chad COD-AB catalog](https://data.humdata.org/dataset/cod-ab-tcd) · [OCHA COD-AB specification](https://github.com/OCHA-DAP/hdx-cod-ab-spec/blob/main/specs/boundaries/README.md) | Original 2019 boundary bytes are retained above; catalog/spec are context, not a substitute geometry |

The release context retains semantic hierarchy SHA-256 `03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d` and footprint SHA-256 `2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286`; these are unchanged. The manifest pins the actual hierarchy JSON and #462 full geometry-inventory file by their file-byte SHA-256 values instead.

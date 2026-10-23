# Issue #380: ArcGIS source-role correction register

Retrieved 2026-10-19 01:26:52 UTC. This is a bounded, additive source-evidence record for the 17 retained Atlas IDs and eight `resolve:` IDs in [issue #380](https://github.com/ChengshuLi/WorldAtlas/issues/380). It does not assign the eight source IDs to individual Atlas IDs, select county replacements, or certify any geography.

## Checked issue input

The current issue body’s exact scope JSON names batch `regional-review:9a60c04e62c9739e`, region `framework:region:northwest-china:af856cea1806`, owned path `data/regional-review/regional-review-9a60c04e62c9739e/`, and 129 members total. Its current region release pin is `geography:review:df86cbaeaf2e18f16ddf2906ef089768baac22f4428e28ed0a4724296cbb413e` (v5), hierarchy SHA-256 `03d23534f87cdd0582bcb228780f00f65090bec2e8a760acbab528383f28549d`, footprints SHA-256 `2ac42eeb9fef8af923a0d4c4e55af49ca0a103de891ffbfb2c1181ad75950286`, and member-ID list SHA-256 `c78e119561059e34c2c30df0589e5e57141c3bc072d5d39ea36fafb9d425b64f`. The issue also scopes 112 `gb:CHN:ADM2` members; this register does not assess or reproduce their rows.

## Scope and result

The current issue body’s embedded exact scope JSON identifies 17 unique `atlas:physical:` IDs and eight unique `resolve:` source IDs in this grouped assignment. The issue does not provide a per-Atlas-ID `ECO_ID` join, original administrative predecessor ID/name, or county-level geometry crosswalk. The issue’s `County Level` role claim is therefore not traceable per row from its exact scope inputs.

The cited ArcGIS item is **RESOLVE Ecoregions and Biomes**, not an administrative county dataset. Its public item description defines ecoregions as ecosystems whose boundaries draw on natural rather than political boundaries. Its linked layer 0 is named **Biomes and Ecoregions 2017**; the layer fields identify ecological features (`ECO_NAME`, `BIOME_NAME`, `REALM`, `ECO_ID`). These metadata do not support a County Level source role. They also do not show that an underlying administrative source, if any exists elsewhere, is licensed under the item’s terms.

The item-level `licenseInfo` states Creative Commons Attribution 4.0 International. The eight queried feature records each report `LICENSE = CC-BY 4.0`. This supports that license statement for this ecoregion item/records, with attribution to RESOLVE and Esri as shown by item `accessInformation`; it does not establish a license for any unidentified administrative predecessor.

| Stable source ID | Citation / role | Vintage and retrieval | Reuse terms / verification status |
| --- | --- | --- | --- |
| `arcgis-resolve-ecoregions-2017:37ea320eebb647c6838c23f72abae5ef` | [Item](https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef) and [layer 0](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0?f=pjson); global ecological ecoregion/biome layer, not administrative/county boundaries. | Dataset vintage 2017 per item/layer title and description. Item metadata, layer metadata, and eight attribute records retrieved 2026-10-19 01:26:52 UTC. | Item `licenseInfo` links CC BY 4.0 and each of the eight retained rows says `CC-BY 4.0`; attribution is `RESOLVE, Esri`. Verified item identity, layer identity/name/fields and the eight attribute rows. Underlying administrative lineage, county geometry and any separate administrative-source license remain unverified. |

The eight-row query used `where=ECO_ID IN (684,709,759,767,808,827,835,843)`, `outFields=ECO_ID,ECO_NAME,BIOME_NAME,REALM,LICENSE`, `returnGeometry=false`, and `f=json`. It is an attribute-only identification/license check, not a spatial overlay or join.

## Eight source records

The retained query is limited to these eight `ECO_ID` values and requests no geometry. The issue’s `resolve:<number>` values match the layer’s `ECO_ID` values by number. The record fields and values are copied from the retained response linked below.

| Issue source ID / `ECO_ID` | Ecoregion name | Biome | Realm | Record license |
| --- | --- | --- | --- | --- |
| `resolve:684` | Tarim Basin deciduous forests and steppe | Temperate Broadleaf & Mixed Forests | Palearctic | CC-BY 4.0 |
| `resolve:709` | Tian Shan montane conifer forests | Temperate Conifer Forests | Palearctic | CC-BY 4.0 |
| `resolve:759` | North Tibetan Plateau-Kunlun Mountains alpine desert | Montane Grasslands & Shrublands | Palearctic | CC-BY 4.0 |
| `resolve:767` | Tian Shan montane steppe and meadows | Montane Grasslands & Shrublands | Palearctic | CC-BY 4.0 |
| `resolve:808` | Alashan Plateau semi-desert | Deserts & Xeric Shrublands | Palearctic | CC-BY 4.0 |
| `resolve:827` | Junggar Basin semi-desert | Deserts & Xeric Shrublands | Palearctic | CC-BY 4.0 |
| `resolve:835` | Qaidam Basin semi-desert | Deserts & Xeric Shrublands | Palearctic | CC-BY 4.0 |
| `resolve:843` | Taklimakan desert | Deserts & Xeric Shrublands | Palearctic | CC-BY 4.0 |

## Seventeen retained Atlas members

Each member remains held. The repeated status below is deliberately not an inferred source assignment: the issue groups eight source IDs with 17 Atlas members but does not state which feature corresponds to which member. The ArcGIS records establish ecological feature identity and license only. No per-location county identity, predecessor, roster match, geometry match, or replacement is asserted.

| Atlas ID | Disposition |
| --- | --- |
| `atlas:physical:1a820b25b2253ed47981` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:2980de0a538a3474eb8c` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:2be66bb9c27334dfd694` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:6ecf16b2678d36abf80b` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:7985280ba9bf72449e18` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:816d698cbdad11d9855b` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:82a47911ff6f9f099e7f` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:8f9fead9996aa35e51be` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:935da103a90de448153a` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:9c7e3cbe41ee2f72453b` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:a804477afb18f65febe0` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:adf8bfeda0b2772c6085` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:c1ad6c17eee5d2cdac16` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:cf4fb8af88391f3760b4` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:d19f2bc57289ff23bca3` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:d27e8403516120bb64d2` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |
| `atlas:physical:de31be43fbcc4ff5cfae` | Held — no source-to-Atlas row join; County Level assignment unsupported by the cited ecoregion layer. |

## Retained source responses

These small public API responses are retained under this directory; the feature query contains attributes only, with `returnGeometry=false`.

| File | Source and content | SHA-256 |
| --- | --- | --- |
| [`arcgis-item.json`](arcgis-item.json) | ArcGIS item REST metadata for item `37ea320eebb647c6838c23f72abae5ef`; includes title, description, attribution, access and license statement. | `7ea6c301274bca6c29a6c24e0a37b6cf6f10b9b949eb17d9905a133f6cb94f5e` |
| [`arcgis-layer-0.json`](arcgis-layer-0.json) | Layer 0 REST metadata; records layer name, geometry type, service item ID, field names and field descriptions. | `d1feffd594812affdc08e089607bab2ed76e256ba7748784d37536797a777d4e` |
| [`resolve-eight-records.json`](resolve-eight-records.json) | Attribute-only feature query for ECO_ID 684, 709, 759, 767, 808, 827, 835 and 843. | `7a3a793e9c29ef80fc5b039a100f2476ec5c885737de40972f1672c934e2b05a` |

The retained responses were retrieved on the timestamp above. Recompute the listed hashes from the files to verify their exact received bytes; the JSON formatting is preserved verbatim. This is a hosted service and live metadata may change; these snapshots identify what was inspected at retrieval. No full feature geometry, county overlay, or 2017 underlying administrative dataset was downloaded.

## Citations and next evidence needed

- [Issue #380](https://github.com/ChengshuLi/WorldAtlas/issues/380), current exact workload JSON and issue-stated role/license assignment.
- [ArcGIS item 37ea320eebb647c6838c23f72abae5ef](https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef), item title, description, attribution and item license information.
- [ArcGIS FeatureServer layer 0](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0?f=pjson), layer name, type, fields and geometry type.
- [RESOLVE Ecoregions 2017 project](https://ecoregions2017.appspot.com/), dataset description and published CC BY 4.0 attribution.
- [Dinerstein et al. (2017), *An Ecoregion-Based Approach to Protecting Half the Terrestrial Realm*](https://doi.org/10.1093/biosci/bix014), cited by the item as the 2017 ecoregion work.

To replace a county-level assignment, recover the actual immutable source/predecessor register that links each Atlas ID to its administrative unit, vintage and native ID; then verify each native unit against a suitable dated administrative source and an independently usable boundary source. Check the underlying source rights separately. A roster, ecological polygon, or matching `ECO_ID` alone cannot supply those missing joins. Until then, preserve all 17 rows as held. This source-role finding does not approve a county geometry, alter any stable identity, resolve any location, or complete the regional packet.

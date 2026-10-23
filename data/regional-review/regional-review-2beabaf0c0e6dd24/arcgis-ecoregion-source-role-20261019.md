# #379 source-role evidence: ArcGIS ecoregion group

Retrieved 2026-10-19. This is a bounded evidence addition for the eight ArcGIS source/entity IDs and fifteen atlas members named together in [issue #379](https://github.com/ChengshuLi/WorldAtlas/issues/379). It does not complete the Northwest China packet, approve geography, assign an ecoregion to an atlas member, or select an administrative replacement.

## Finding and classification

The issue describes this source group as **County Level**, vintage **2017**, and licensed **CC BY 4.0; underlying administrative source license retained**. The cited ArcGIS item is **RESOLVE Ecoregions and Biomes**. Its current layer 0 title is **Biomes and Ecoregions 2017**; the layer schema describes `ECO_NAME`, `BIOME_NAME`, `REALM`, and `ECO_ID` as ecoregion, biome, realm, and ecoregion identifiers. The eight records below return ecological names, biomes, and realms. The layer's feature schema and records do not provide a county name, administrative code, or county-tier designation. The source therefore supports an **ecological ecoregion classification**, not a **County Level administrative role**.

**Group-level disposition:** `correction-needed` for the issue's County Level attribution of this ArcGIS source group. This finding is limited to source role; it is not a proposed administrative hierarchy or boundary correction.

**Atlas-member disposition:** `insufficient evidence` for each of the fifteen rows below. The issue identifies the eight source IDs and fifteen atlas IDs as a group but supplies no per-member `ECO_ID` join. The source extracts contain no atlas IDs. Do not join by name, proximity, order, or ecological footprint. All fifteen administrative identities and any county replacements remain held.

## Current source inspection

Sources were read on 2026-10-19 from the public ArcGIS REST service, with the feature query restricted to attributes and `returnGeometry=false`.

- [ArcGIS item page](https://www.arcgis.com/home/item.html?id=37ea320eebb647c6838c23f72abae5ef) identifies the item; current item REST metadata reports title `RESOLVE Ecoregions and Biomes`, type `Feature Service`, attribution `RESOLVE, Esri`, and a CC BY 4.0 license link: [item metadata JSON](https://www.arcgis.com/sharing/rest/content/items/37ea320eebb647c6838c23f72abae5ef?f=pjson).
- [Layer 0 metadata](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0?f=pjson) reports `Biomes and Ecoregions 2017`, polygon geometry, and fields for ecological ecoregion/biome/realm names and IDs. The layer's `dataLastEditDate` is 2022-01-27; the later service and schema edit timestamps (2026-03-03 and 2026-01-20 UTC) are metadata changes, not a different product vintage. The title is the evidence for the 2017 product label.
- The [direct attribute-only query](https://services.arcgis.com/P3ePLMYs2RVChkJx/arcgis/rest/services/Resolve_Ecoregions/FeatureServer/0/query?where=ECO_ID%20IN%20(750%2C759%2C763%2C765%2C768%2C808%2C835%2C843)&outFields=ECO_ID%2CECO_NAME%2CBIOME_NAME%2CREALM%2CLICENSE%2COBJECTID&returnGeometry=false&f=pjson) and its [retained, losslessly compressed response](./arcgis-ecoregion-features-20261019.json.gz) contain exactly eight records and no geometry. Decompressed response SHA-256: `41296e8d7f894f1493307af78856a9b30ca7a75d985dfd94543b824e8ac3866c` (4,640 bytes). Each record's `LICENSE` is `CC-BY 4.0`.

| Source/entity ID | `ECO_ID` | `OBJECTID` | Current `ECO_NAME` |
| --- | ---: | ---: | --- |
| `resolve:750` | 750 | 152 | Central Tibetan Plateau alpine steppe |
| `resolve:759` | 759 | 492 | North Tibetan Plateau-Kunlun Mountains alpine desert |
| `resolve:763` | 763 | 584 | Qilian Mountains subalpine meadows |
| `resolve:765` | 765 | 664 | Southeast Tibet shrublands and meadows |
| `resolve:768` | 768 | 741 | Tibetan Plateau alpine shrublands and meadows |
| `resolve:808` | 808 | 9 | Alashan Plateau semi-desert |
| `resolve:835` | 835 | 582 | Qaidam Basin semi-desert |
| `resolve:843` | 843 | 723 | Taklimakan desert |

The current item and feature license statements apply to this ArcGIS-hosted ecological product. They do not establish the license, lineage, date, or reuse rights of any underlying administrative source that could replace the claimed county data. That source has not been identified or verified here.

## Exact atlas members in this limited review

The following fifteen atlas IDs are the exact group listed in #379. No per-row mapping to the eight `resolve:` IDs is present in the cited issue contract or in the inspected feature attributes. `Insufficient evidence` below means the administrative source identity and county role cannot be determined for that atlas row from this group; it does not mean that the atlas row is necessarily incorrect.

| Atlas ID | Source join established? | Classification | Held next step |
| --- | --- | --- | --- |
| `atlas:physical:2bf73021d41d13950002` | No | insufficient evidence | Recover exact source-membership row and verify the original dated administrative source, tier, and reuse terms. |
| `atlas:physical:48bc99a9b9604031958a` | No | insufficient evidence | Same: recover exact source-membership row and verify original administrative source, tier, and reuse terms. |
| `atlas:physical:4973af0f9f73eb02a8bc` | No | insufficient evidence | Same. |
| `atlas:physical:511a7beabdd01bc6ab0d` | No | insufficient evidence | Same. |
| `atlas:physical:58e5e5f6b6184a3fb07f` | No | insufficient evidence | Same. |
| `atlas:physical:7617b337de9b0a99d784` | No | insufficient evidence | Same. |
| `atlas:physical:846760d3d9cabcf88859` | No | insufficient evidence | Same. |
| `atlas:physical:87c22fa4bdb389d42549` | No | insufficient evidence | Same. |
| `atlas:physical:8aa2cfb0a4b47df33650` | No | insufficient evidence | Same. |
| `atlas:physical:95183d46816a1cdfa320` | No | insufficient evidence | Same. |
| `atlas:physical:9d604919d8aaf9102379` | No | insufficient evidence | Same. |
| `atlas:physical:a0a4eaa441cdadbb5e1a` | No | insufficient evidence | Same. |
| `atlas:physical:d87d83d6cb8b4020cca3` | No | insufficient evidence | Same. |
| `atlas:physical:e18a1a0c1e8f48485f97` | No | insufficient evidence | Same. |
| `atlas:physical:f92caf4f27628a38f4da` | No | insufficient evidence | Same. |

## Limits and continuation

This inspection verifies the current ArcGIS item metadata, layer schema, and eight current attribute records. The layer provides polygon geometry but this capture intentionally excludes geometry; neither geometry overlay nor a county-boundary comparison was performed. The source-membership input that would link features to atlas IDs was not available in the issue contract or this scoped evidence directory at the pinned main commit. No administrative replacement was sought, because the present evidence does not identify which county source or individual row to search.

Next: recover the retained per-member source-membership/crosswalk input, then identify and verify the original administrative source for each joined row (date, boundary role/tier, source completeness, license, and attribution). Keep rows held until exact joins and adequate source evidence are available. This partial evidence does not close #379 or enable geography approval, a regional branch certificate, or history imports.

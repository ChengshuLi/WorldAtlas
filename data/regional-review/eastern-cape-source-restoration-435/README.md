# Eastern Cape: exact 17-ID research packet (issue #1137)

**Stage:** research complete with unresolved boundary-effective-date and completeness questions. This packet does not approve the Eastern Cape, replace geography, modify a release, or authorize import. **Evaluation date:** 2026-10-06. **Pinned main baseline:** `e8138aef2004b419cb8c458ccc1fb2ce31b639f6`.

## Findings

- The issue’s 17 source IDs are reproduced from geoBoundaries gbOpen ZAF ADM3 2020, release commit `9469f09`, against the exact concatenated source hash `74e489fd4370972403950719026a317abba443668cea7d49f4b36c61637958f1`. The original is 50,705,428 bytes, lawfully redistributed under CC BY 3.0 IGO, already retained unchanged in two ordered parts by ancestor packet `data/regional-review/regional-review-b9aef9289b79194e/`. To avoid duplicating the dataset, this packet pins and reads those exact base-commit parts in place. The script checks both part hashes, exact total bytes/hash and all 213 source features, then requires the scoped 17 original IDs/names to match.
- The MDB 2021 ArcGIS item/service returned the full Eastern Cape roster of 33 municipal features: 31 Category B and two Category A. All 17 exact scoped crosswalks have unique MDB codes and served geometry: 16 B and one A (Nelson Mandela Bay). All 17 records are `Polygon` with one polygon part in the response. That does **not** establish legal extent or rule out omitted detached land outside the service response. The served layer is based on MDB 2018, came into effect in 2021 and its service metadata was last edited in December 2023. MDB reuse terms require attribution, permit research/publication/value-added use, bar sale/commercial use and prohibit altering/re-presenting altered data as MDB’s product.
- The prospective MDB 2026 item says it takes effect on 2026-11-04 after the local elections. At evaluation on 2026-10-06 it is not current. Do not substitute it for a current boundary layer.
- The official 2024 MDB gazette search records confirm decisions DEM6500, DEM6506 and DEM6611 in Section 21(5) notice 805 (Gazette 5064, 2024-03-11), following Section 21 determinations in Gazette 5030 (2024-01-08). They affect Intsika Yethu (EC135), Sakhisizwe (EC138) and source Engcobo/current code Dr AB Xuma (EC137). The named community/administrative-area changes are detailed in `findings/mdb-crosswalk-and-reproduction.json`. These establish MDB decisions; the later Section 23 effective-date notices from the Electoral Commission and Eastern Cape MEC have not been located. Therefore, whether and when the new limits superseded the 2021 layer is **unresolved**. The 2026 item’s date cannot fill this gap.
- The official Stats SA 2022 Eastern Cape page says Cacadu District was renamed Sarah Baartman in 2018. Seven 2020 children retain the `Cacadu` parent ID/name in the Atlas. Preserve this historical source relationship and stable IDs; current MDB uses Sarah Baartman / DC10. No shared hierarchy edit is in scope.
- Source/Atlas says `Engcobo`; MDB code EC137 calls the municipality `Dr AB Xuma`. The municipality’s current page identifies Dr AB Xuma as Category B and Engcobo as its town/urban location. The code provides an exact crosswalk clue, not the missing legal naming Gazette/date. Keep the source name and record a name-date engineering follow-up.
- MDB classifies Nelson Mandela Bay as Category A metropolitan municipality (NMA), not an ordinary Category B local municipality. Existing same-name repeat in the Atlas parent chain needs a separate hierarchy/parent-level engineering review.
- Diagnostic comparison of all 33 2021-service and prospective-2026-service features matched by MDB municipal code found all 33 returned geometries differ. For the three confirmed redetermination codes, full-feature symmetric differences are: EC135 30,303,182 m²; EC138 32,875,123 m²; EC137 20,794,717 m². These are entire-feature gained-plus-lost diagnostic areas, not measurements of the named villages/administrative areas. The changes to all other served geometries, which may include source/vintage edits, have no attribution from this evidence. The comparison cannot choose a correct footprint and uses no threshold.

## Reproduction

From repository root with the bundled Python runtime (Python 3.12.14, Shapely 2.1.2, pyproj 3.7.2):

```sh
python data/regional-review/eastern-cape-source-restoration-435/reproduce_source_audit.py
python data/regional-review/eastern-cape-source-restoration-435/measure_boundary_vintages.py
PYTHONPATH=scripts python test/evidence-geography.py
PYTHONPATH=scripts python test/ellipsoidal-area.py
node scripts/evidence-quality.mjs data/regional-review/eastern-cape-source-restoration-435/evidence-quality.json
```

`findings/mdb-crosswalk-and-reproduction.json` contains the exact 17-row crosswalk, baseline pins, all 2021 and 2026 roster results, 2024 confirmed cases, parent findings and source hashes. `findings/boundary-vintage-differences.json` contains every returned code (including the contextual other Eastern Cape features), area/IoU metrics and controls. All output files are dated/vintage-specific; reruns overwrite only generated results within this owned packet.

## Restoration and limitations

See `findings/source-register.json` for retained bytes/hashes, access dates, URLs, terms and restoration instructions. Original PDFs were not retained when direct requests timed out/returned 502; search indexing exposed relevant official Gazette passages. Restore official PDFs from the recorded URLs and inspect the DEM map sheets. Also locate: (1) the IEC’s Section 23 materiality opinion for DEM6500/6506/6611; (2) corresponding Eastern Cape MEC effective-date Gazette notice, if required by the IEC opinion; (3) an authoritative current post-2023 MDB boundary source that bridges those notices and the prospective 2026 release; (4) the Gazette that establishes the Dr AB Xuma naming change and effective date; (5) authoritative evidence for detached/island coverage and neighbouring tiers. A lack of a result in this packet is not proof that no notice or detached territory exists.

## Engineering handoff

1. Keep all 17 IDs and 2020 source names; separately resolve the Dr AB Xuma legal name date and Cacadu/Sarah Baartman parent history.
2. Obtain Section 23 notices and a controlling-current MDB source before any boundary correction. 2021 output has a demonstrated age gap; 2026 data is prospective as evaluated.
3. Review Nelson Mandela Bay’s A-tier/parent chain in a separately scoped hierarchy task.
4. Inspect local gazettes/maps and authoritative source records for the full roster and detached territory. No geometry was copied or replaced here.
5. Keep issue #955’s disjoint 196 IDs with its owner. Exact scope overlap is zero.

No geography or production data was changed.

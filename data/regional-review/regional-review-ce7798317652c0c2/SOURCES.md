# Croatia ADM2 batch 4 source and findings (2026-10-05)

## Scope and method

This is the exact 224-member subset and eight whole-county scopes from #419, at immutable baseline `7646e0962afab6cc4f566439bb2f96890ae4b91e`. `scope.json` is the exact scope extracted from the preserved issue API response; its member digest is `c5816fc5587099904fd5c5cff51801676ec361606153cb39c70e9fb19ef0f116`. `build_assessment.py` resolves those IDs from the pinned world index and actual containing geography part, verifies every native geoBoundaries shape ID/name/tier/country, compares local name/type against the DZS official 2021 roster grouped by the Atlas baseline parent’s county alias, and compares source versus baseline geometry *types* as a screening signal. The geoBoundaries object has no independently inspected county parent field, so the source does not independently verify any Atlas county parent relationship. It does not compare boundary coordinates or establish territorial correctness.

Reproduce after restoring the exact upstream object and DZS detail workbook to temporary locations (do not commit either full source object):

```sh
curl --fail --location --output /tmp/geoBoundaries-HRV-ADM2-9469f09.geojson \
  https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/HRV/ADM2/geoBoundaries-HRV-ADM2.geojson
printf '%s  %s\n' 68a317129a0c295fd8baf7acc0f31ffefdf65ff2f1f62f8ed90a765cc57cf01e /tmp/geoBoundaries-HRV-ADM2-9469f09.geojson | shasum -a 256 -c -
curl --fail --location --output /tmp/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx \
  https://podaci.dzs.hr/media/td3jvrbu/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx
printf '%s  %s\n' c2b1cff240a19b5bfbf6dcb5e919a264284dfa444a326adae5517bf39b6d7d42 /tmp/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx | shasum -a 256 -c -
python3 data/regional-review/regional-review-ce7798317652c0c2/extract_dzs_roster.py \
  --workbook /tmp/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx \
  --output /tmp/dzs-census-2021-detail-extract.csv
cmp /tmp/dzs-census-2021-detail-extract.csv data/regional-review/regional-review-ce7798317652c0c2/source/dzs-census-2021-detail-extract.csv
python3 data/regional-review/regional-review-ce7798317652c0c2/build_assessment.py \
  --baseline 7646e0962afab6cc4f566439bb2f96890ae4b91e \
  --source /tmp/geoBoundaries-HRV-ADM2-9469f09.geojson \
  --output-dir data/regional-review/regional-review-ce7798317652c0c2/vintages/2026-10-05
```

The full geometry object was fetched 2026-10-05 from the immutable geoBoundaries commit URL above; 20,788,018 bytes, SHA-256 `68a317129a0c295fd8baf7acc0f31ffefdf65ff2f1f62f8ed90a765cc57cf01e`, 560 features, unique `shapeID`. The redirect resolved to commit `9469f09592ced973a3448cf66b6100b741b64c0d`. Response headers and actual upstream LFS metadata/citation text are retained. The metadata says ADM2 “Municipalities and Towns,” representative year 2021, source OSM/geoBoundaries, data updated 2023-01-19 and built 2023-12-12, 560 units; this does not establish a 2021-08-31 legal boundary snapshot.

## Sources, role, and reuse

* Croatian Bureau of Statistics (DZS), 2021 Census detailed towns/municipalities workbook, retrieved 2026-10-05 from `https://podaci.dzs.hr/media/td3jvrbu/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx`; full original 18,279,747 bytes, SHA-256 `c2b1cff240a19b5bfbf6dcb5e919a264284dfa444a326adae5517bf39b6d7d42`, restoration-only. The lawful complete 555-row names/type/county excerpt is retained as `source/dzs-census-2021-detail-extract.csv`, 35,680 bytes, SHA-256 `225021e29f4ec2eeeffda3801031f4c0587241e91eed984394c9d2d56b09785c`; `extract_dzs_roster.py` recreates it from the exact pinned workbook. DZS states datasets may be reused without restriction under its Open License, with attribution: `https://dzs.gov.hr/o-zavodu/pravo-na-pristup-informacijama/otvoreni-podaci/1812`. Role: official names, local-government types and county roster at census reference time 2021-08-31. Not boundary geometry or legal change history.
* DZS, 2021 Census consolidated summary workbook, retrieved 2026-10-05 from `https://podaci.dzs.hr/media/qlyhbd0f/popis_2021-stanovnistvo_zbirni_pregledi.xlsx`; 63,196 bytes; SHA-256 `99feecc93627db02509aee7d625b391c33a69f201f377464ac15c2fd7c16f20f`. Role: independent county-level town/municipality count cross-check; same open reuse terms and attribution.
* geoBoundaries HRV ADM2 exact object as described above. The retained upstream LFS pointer identifies metadata object SHA-256 `e2b5d837084f3a2360a16b51e198d35799903c4b99687dd547f1b73a11847790`; actual metadata is retained with SHA-256 `e2b5d837084f3a2360a16b51e198d35799903c4b99687dd547f1b73a11847790`. The file metadata asserts CC BY-SA 2.0 and points to OpenStreetMap, while geoBoundaries documentation says individual source files have their own license and current OSM terms concern ODbL. We have not reconciled these statements or made a legal determination. The geometry is therefore restoration-only and is not redistributed here; use is for reproducible internal comparison only pending license clarification.
* State Geodetic Administration (DGU) official Register of Spatial Units purpose: `https://dgu.gov.hr/registar-prostornih-jedinica-172/172`; INSPIRE Administrative Units Atom feed (English and Croatian snapshots retained) `https://geoportal.dgu.hr/services/atom/au/en.xml` and `https://geoportal.dgu.hr/services/atom/au/xml`, retrieved 2026-10-05. The feed advertises an entire-country administrative-unit GML archive updated 2026-10-04, but explicitly marks a public-access limitation under INSPIRE 13(1)(e). No linked polygons were downloaded or reused. DGU is the authoritative lead for an appropriately licensed, dated official extract; availability and reuse permission for a 2021 comparison remain unresolved.
* Official Croatian 2006 territorial-unit law: `https://narodne-novine.nn.hr/clanci/sluzbeni/2006_07_86_2045.html`. Supports statutory local-government role context; does not prove 2021 boundaries.
* TDWG WGSRPD purpose: `https://www.tdwg.org/standards/wgsrpd/`. Its level-3 Botanical Country framework is designed for plant-distribution recording and allows botanical usage to ignore purely political considerations. The Atlas area `framework:area:yugoslavia:cff5e9ba6c8e` cites WGSRPD level 3; that citation alone does not establish this shared area as a general-purpose atlas region or settle its boundary. The area includes 1,169 IDs; this packet checks only 224, and neighboring batches remain separate work.

## Reproduced findings

`vintages/2026-10-05/assessment-summary.json`, `province-completeness.csv`, and `scoped-location-assessments.csv` are deterministic outputs. 224/224 issue IDs resolve uniquely in baseline `data/geography/part-10.json`, exist in the exact source object with matching native source ID, country `HRV`, tier `ADM2` and unchanged source name, and map to one declared Atlas county by baseline parent ID. Against the DZS local name/type rows grouped under that inherited county, 220 labels match. This does not independently verify the parent assignment. Four have a unique same-parent-county, same-type official name candidate but differ in spelling/presentation:

* `gb:HRV:ADM2:41942358B70634803465556`: `Općina Hvratska Dubica` → candidate `Hrvatska Dubica`.
* `gb:HRV:ADM2:41942358B35075150352147`: `Općina Donji Kukuzari` → candidate `Donji Kukuruzari`.
* `gb:HRV:ADM2:41942358B91711209403379`: `Općina Veliki Pisanica` → candidate `Velika Pisanica`.
* `gb:HRV:ADM2:41942358B6406776425998`: `Grad Ivanić Grad` → candidate `Ivanić-Grad`.

The complete required-dimension review (role, parent, completeness, source vintage/license, fragmented and island territories, anonymous units, scale and neighboring granularity) is in `findings/review-coverage.md`; it records what is screened and what remains unverified per dimension.

The DZS roster has 231 towns/municipalities across these eight counties, against 224 issue IDs. After the four name candidates are crosswalked (not silently corrected), seven official rows remain absent: Zagreb County — Zaprešić, Bistra, Stupnik; Varaždin County — Ljubešćica; Bjelovar-Bilogora — Ivanska, Rovišće, Zrinski Topolovac. The other five scoped county rosters reconcile by local name/type. DZS establishes this census-time roster, not Atlas IDs or boundary polygons for missing rows. Do not create IDs by inference.

13 scoped source/baseline features disagree in GeoJSON geometry type (12 source MultiPolygon vs baseline Polygon; one source Polygon vs baseline MultiPolygon). This is evidence of changed/lost multipart representation across source vintages, not by itself proof of missing islands or incorrect boundaries. Inspect those IDs in the output before any engineering proposal. The source has 19 MultiPolygon features in the scope; component counts are screening metadata only.

## Unresolved findings and handoffs

1. Created blocked source-restoration/crosswalk follow-up [#1028](https://github.com/ChengshuLi/WorldAtlas/issues/1028) for the seven absent 2021 local governments. Required: original DGU RPJ identifiers, official 2021-08-31 polygon geometry or explicit reproducible and lawfully reusable archive path, name/type/county and predecessor/successor history, and a source-to-Atlas identity crosswalk. Current DGU feed's access limitation prevents a geometry correctness conclusion.
2. Record a bounded engineering handoff for the four name candidates and 13 geometry-type differences, retaining stable IDs and original source. DZS supports local-name/type/county roster comparisons only; it does not independently verify county parents. Any canonical geometry change needs suitable dated boundary evidence and an engineering-owned PR/release review.
   Bounded source adjudication for these exact 17 IDs is tracked in blocked follow-up [#1029](https://github.com/ChengshuLi/WorldAtlas/issues/1029); the engineering handoff is in `findings/engineering-handoff.md`.
3. Leave broader WGSRPD area role/shape and cross-batch membership as open shared-area work. Cross-reference #416–#418 and #420–#424; this exact batch is not integrated-area acceptance.
4. No boundary correctness, official-island completeness, regional approval, publication or import authorization is claimed.

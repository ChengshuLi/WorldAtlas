# Engineering handoff from issue #419 (2026-10-05)

This packet proposes review, not direct modification. The four source-to-DZS local-name/type candidates are in `../vintages/2026-10-05/scoped-location-assessments.csv` under `classification=correction-needed`:

| Stable Atlas ID | Baseline/source label | DZS 2021 candidate | Note |
|---|---|---|---|
| `gb:HRV:ADM2:41942358B70634803465556` | Općina Hvratska Dubica | Hrvatska Dubica | Source spelling differs |
| `gb:HRV:ADM2:41942358B35075150352147` | Općina Donji Kukuzari | Donji Kukuruzari | Source spelling differs |
| `gb:HRV:ADM2:41942358B91711209403379` | Općina Veliki Pisanica | Velika Pisanica | Candidate is uniquely county/type-matched; verify source alias and label policy |
| `gb:HRV:ADM2:41942358B6406776425998` | Grad Ivanić Grad | Ivanić-Grad | Hyphen/presentation candidate |

Do not rewrite names in this packet. DZS is evidence for 2021 local-government name, type and county roster; it is not sufficient for canonical feature renaming without source lineage and name policy review.

The pinned geoBoundaries object and baseline differ in geometry type for these 13 stable IDs:

* `gb:HRV:ADM2:41942358B11408332242039` — Grad Korčula: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B19243079676848` — Grad Vis: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B24847699776979` — Grad Kaštela: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B27040282046651` — Grad Solin: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B3051457735690` — Općina Šolta: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B41584880694978` — Općina Milna: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B5058073366135` — Općina Cestica: baseline MultiPolygon, source Polygon.
* `gb:HRV:ADM2:41942358B51317462978185` — Općina Mljet: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B62948971523920` — Grad Hvar: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B81819772164255` — Općina Bol: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B84243302989703` — Općina Marina: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B85370902157409` — Općina Okrug: baseline Polygon, source MultiPolygon.
* `gb:HRV:ADM2:41942358B92131033251533` — Općina Seget: baseline Polygon, source MultiPolygon.

These are source-vintage differences that warrant geometry owner inspection against licensed, dated official boundary evidence. They do not prove that an Atlas feature omitted islands, nor that the newer source geometry is correct. Preserve stable IDs and old bytes; any accepted change belongs in an engineering-owned change with applicable source/license review, geometry validation and release/certificate revalidation. The geoBoundaries source geometry license remains unresolved in this packet.

Seven unmatched DZS names are tracked in source-restoration follow-up [#1028](https://github.com/ChengshuLi/WorldAtlas/issues/1028). The 17 name/geometry-lineage records above have a separate bounded source adjudication follow-up [#1029](https://github.com/ChengshuLi/WorldAtlas/issues/1029). Both are blocked and depend on this packet; no Atlas IDs should be invented. County parent membership here was inherited from the pinned baseline; this handoff does not independently certify those parent assignments.

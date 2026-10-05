# Area purpose and parent-label review (2026-10-05)

## Scope and result

This addendum examines the five existing area labels and all 39 parent IDs in the already pinned 215-location issue scope. It does not replace the original packet, alter a hierarchy ID, or validate polygon geometry. The reproducible comparison is `area-source-crosswalk.csv`; its source tables are restoration-only and its method is `reproduce-area-source-crosswalk.py`. The hierarchy input is pinned to PR1 baseline commit `7995cfb8cc9f1f282e1419bdddf13de1f8107e21`, file SHA-256 `568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b`.

The Atlas hierarchy explicitly describes Chile Central, Chile North, Chile South, Juan Fernández Is. and Paraguay as WGSRPD Level 3 geographic areas and notes that WGSRPD calls Level 3 units “botanical countries.” At the pinned TDWG repository commit `52da7828aba9d461dd133c27b3bd7a4407161f54`, its Level 3 source table places all five labels/codes (CLC, CLN, CLS, JNF, PAR) under Level 2 `85,00` (Southern South America). The source abstract explains its use for plant-distribution records and states Level 3 may disregard political considerations; Level 4 is the basic recording-unit tier. Kew's Plants of the World Online describes using WGSRPD for biodiversity distribution and likewise warns that Level 3 botanical-country borders can differ from political boundaries. This supports the labels' botanical/distribution purpose. It does not establish that these groupings are the best fit for every Atlas purpose.

The pinned Level 4 table lists 7 CLC, 3 CLN, 3 CLS, 1 JNF and 1 PAR basic units. Atlas hierarchy child counts are respectively 31, 10, 14, 1 and 18. These tiers therefore are not a one-to-one crosswalk. The larger Atlas counts do not establish a defect: WGSRPD Level 4 is a historical plant-recording framework and its units are not necessarily current administrative units. They do show that Atlas scale/semantics need an explicit product-level decision, especially for Chile Central (31 provinces versus the source's seven historical recording units). The source tables do not provide current legal parenthood or boundary validation.

Other published Chile zonations use different purposes. SUBDERE's 2007 evaluation describes six traditional geographic/economic zones and explicitly says these were not administrative divisions. SUBDERE's DPA 2023 notice describes administrative polygon maintenance using SUBDERE, DIFROL and IGM source responsibilities. The existence of distinct schemes is a reason to document the Atlas grouping purpose, not evidence that one scheme supersedes the others.

## Scoped parent identity handoff

The pinned hierarchy has two distinct province IDs with the same display name, `Provincia de Valparaíso`: `framework:province:provincia-de-valparaiso:0a08296fc889` is under Chile Central with `child_count: 6`; `framework:province:provincia-de-valparaiso:1556db69a421` is under Juan Fernández Is. with `child_count: 1`. Only the Juan Fernández parent ID appears among this packet’s 39 scoped parent rows; the six-child Chile Central parent is outside that row scope. SUBDERE's official region/province page identifies Juan Fernández as a commune in Valparaíso Province and describes its island territory. INE's 2014 DPA table also lists commune 5104 Juan Fernández under Province 51 Valparaíso. The current split may be intentional geographic partitioning for area membership; this evidence does not prove it is an identity error. It requires an integration-level decision about whether one legal province may be represented by two Atlas parent IDs to support area partitioning. Record the broader-tree question for #441; this packet does not assert that the six Chile Central children are in scope and does not consolidate or reparent either ID.

The official Chile administrative DPA contains other distinct islands (including Easter Island Province), but this issue's five areas do not include an Easter Island area. This review did not test the broader macro-region inventory and makes no omission claim. Existing source vintage, roster completeness, boundary, and neighboring-seam gaps remain as recorded in `source-review.md`, `semantic-screen.md`, and follow-ups #932/#933.

## Reproduction and source custody

`reproduce-area-source-crosswalk.py` verifies the raw SHA-256 of both pinned TDWG source tables, decodes their Windows-1252 bytes, checks the five exact Level 3 records and L2 parent code, verifies expected Level 4 row counts, and emits the five area plus 39 parent rows. Example:

```sh
python3 data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/reproduce-area-source-crosswalk.py \
  --level3 /path/to/tblLevel3.txt --level4 /path/to/tblLevel4.txt \
  --hierarchy /path/to/baseline-hierarchy.json --output data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-source-crosswalk.csv
```

The exact source commit, raw URLs, hashes, retrieval date, and restoration path are in `source/source-register.json`. No source table or polygon is retained because the repository did not state reuse terms. This is a text/name and hierarchy-count crosswalk only; no geometry operation, legal conclusion, completeness claim, regional approval, import or release authorization is made.

## Primary sources consulted

- TDWG, [World Geographical Scheme for Recording Plant Distributions](https://github.com/tdwg/wgsrpd), pinned commit above; `tblLevel3.txt` and `tblLevel4.txt`.
- Royal Botanic Gardens, Kew, [Plants of the World Online: About](https://powo.science.kew.org/about), WGSRPD use and Level 3 meaning.
- SUBDERE, [DPA 2023 publication notice](https://www.subdere.gov.cl/sala-de-prensa/subdere-publica-nueva-versi%C3%B3n-de-los-l%C3%ADmites-de-la-divisi%C3%B3n-pol%C3%ADtico-administrativa), published 2023-11-10.
- SUBDERE, [Valparaíso Province / Juan Fernández entry](https://www.subdere.gov.cl/divisi%C3%B3n-administrativa-de-chile/gobierno-regional-de-valpara%C3%ADso/provincia-de-valpara%C3%ADso/juan-fern%C3%A1n).
- Chile National Statistics Institute, [Vital statistics yearbook 2014, DPA table](https://www.ine.gob.cl/docs/default-source/nacimientos-matrimonios-y-defunciones/publicaciones-y-anuarios/anuarios-de-estad%C3%ADsticas-vitales/ine_anuario_de_estad%C3%ADsticas-vitales_2014.pdf?sfvrsn=1da57318_3), codes for Province 51 / commune 5104.
- SUBDERE, [Evaluation of the current Political-Administrative Division (2007)](https://www.subdere.gov.cl/sites/default/files/documentos/informe_final_2007_0808181.pdf), traditional geographic/economic macrozones.

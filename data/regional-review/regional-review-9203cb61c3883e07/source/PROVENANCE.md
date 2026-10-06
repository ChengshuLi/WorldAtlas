# Source provenance and restoration ledger

Retrieved 2026-10-05 UTC using command-line HTTPS/GitHub API. GitHub contents and LFS data were accessed through API/media endpoints; no GitHub browser was used. Source payload SHA-256 values below identify exact bytes. Official statistical PDFs are not retained because their inspected pages do not state an open redistribution license; their exact download URL and observed response hash are restoration references. All geometries and metadata in `geoboundaries/` and `natural-earth-admin1/` are retained as listed, except the oversized full-resolution Zambia GeoJSON, whose immutable Git LFS restoration locator is recorded.

## Frozen Atlas baseline and scope

Reproduction is evaluated against fresh `origin/main` commit `90f04d30cf773b5be538bc3d85d4d9051768deef` (2026-10-05), the issue's immutable reservation baseline. Whole-file SHA-256 pins are:

| Baseline input | SHA-256 |
|---|---|
| `data/geography/part-28.json` | `2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d` |
| `data/hierarchy.json` | `568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b` |
| `data/administrative-sources.json` | `ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633` |

The 102-location membership is frozen in `source/issue-scope.json`. The issue's saved API body and this parsed scope contain the same ID list and declared digest. The recorded `member_location_ids_sha256` is `79c12258faed667954b6041a32594eb855a72d80f8764b54d7b5421e755a747f`; `reproduce.py` computes `5a578f9df7d0b932d14922f47ce7afc490a845a6aa9cf7f9809de47259f10d23` from the sorted compact-JSON ID array. These do not match. The saved ID list is unique, has 102 members, and each member resolves in the pinned baseline file; the issue-body/scope equality and digest mismatch are both reproduced. The mismatch is preserved as unresolved rather than silently repaired. `source/issue-snapshot.json` preserves the issue's declared scope and acceptance context, while `source/claim-receipt.json` records the serialized worker reservation. These frozen inputs are an evaluation baseline, not a claim that their polygons or lineage are correct.

## Retained geoBoundaries inputs

Pinned repository commit: [`9469f09592ced973a3448cf66b6100b741b64c0d`](https://github.com/wmgeolab/geoBoundaries/tree/9469f09592ced973a3448cf66b6100b741b64c0d). Data-build metadata date: 2023-12-12; metadata refresh field: 2023-01-19; represented boundary year: 2020. The refresh/build dates are not represented as boundary survey dates.

| Item | Source vintage/role | License / source | Retained path | SHA-256 |
|---|---|---|---|---|
| ZMB ADM2 simplified GeoJSON | 2020; 116 named districts | geoBoundaries `gbOpen`; CC BY 4.0; source contributors GRID3 and Office of Surveyor General | `source/geoboundaries/geoBoundaries-ZMB-ADM2_simplified.geojson` | `58e9df3f95bb4c7539e5fb48839b246b2bfb12694cf5db3ed595240156016c60` |
| ZMB ADM2 metadata | 2020; boundary year, source, license, count | same | `source/geoboundaries/geoBoundaries-ZMB-ADM2-metaData.json` | `a2deeb0dc00bc1f8b7b1a5be7668be1f4139ccaf65b2acd0efc0783237a9011b` |
| ZWE ADM2 full-resolution GeoJSON | 2020; 91 named districts | geoBoundaries `gbOpen`; CC BY 3.0 IGO; source contributors ZIMSTAT/CSO and OCHA ROSEA | `source/geoboundaries/geoBoundaries-ZWE-ADM2.geojson` | `074a3632634b9448bb4043580fe7199e0b2f64ec68bd2f98932a2c68b3795b88` |
| ZWE ADM2 simplified GeoJSON | same represented roster | same | `source/geoboundaries/geoBoundaries-ZWE-ADM2_simplified.geojson` | `3486ef2803574e63db97e2a35b6688bb327cb8d6ff5e439691c1cc3068ddb424` |
| ZWE ADM2 metadata | 2020; boundary year, source, license, count | same | `source/geoboundaries/geoBoundaries-ZWE-ADM2-metaData.json` | `6adc8672208814d255f3e2224e804c30be49a48ee4afae03e94f001aa75eb5a4` |

The `sha256` in Atlas `data/administrative-sources.json` matches the **simplified** GeoJSON for each country, byte-for-byte; it is not the full-resolution LFS GeoJSON hash. The retrieved full-resolution objects have hashes/OIDs `ZMB ff4a4c8a92f7416b8457f423b339f2623b10f59410339911a0427fcee8434f17` and `ZWE 074a3632634b9448bb4043580fe7199e0b2f64ec68bd2f98932a2c68b3795b88`. The complete ZMB object was 35,998,492 bytes, above the repository's 32 MiB evidence-file limit, so it is not committed. Restore it from:

`https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/ZMB/ADM2/geoBoundaries-ZMB-ADM2.geojson`

The exact GitHub API content blob is `c50c7463d76efa131f8b03febfee6a21b84fb4e9`; its Git LFS pointer states SHA-256 `ff4a4c8a92f7416b8457f423b339f2623b10f59410339911a0427fcee8434f17` and size `35998492`. For ZWE full resolution, the GitHub API blob is `3a912e3b55dc20e3042e28fffbf3faf4ecbf0063`, LFS OID is the retained payload SHA above, and size is 17,379,177 bytes. Original media restoration pattern for both is the immutable GitHub commit URL and relative file path under `releaseData/gbOpen/<ISO>/ADM2/`.

The ZWE metadata JSON's Git LFS pointer is retained at `source/geoboundaries-9469f09/ZWE/ADM2/geoBoundaries-ZWE-ADM2-metaData.json` (LFS OID equals the separately retained metadata payload hash `6adc8672208814d255f3e2224e804c30be49a48ee4afae03e94f001aa75eb5a4`, size 1,008 bytes). The payload itself is at the regular organized `source/geoboundaries/` path; do not parse the pointer as metadata.

Attribution for downstream use must preserve the geoBoundaries release citation and its source-specific license: Zambia `GRID3, Office of the Surveyor General` under CC BY 4.0; Zimbabwe `Zimbabwe National Statistics Agency (ZIMSTAT) Central Statistics Office, OCHA ROSEA` under CC BY 3.0 IGO. Attribution/license fields are source metadata, not independent proof that the current Atlas display polygon matches those lineworks.

## Retained Natural Earth identity reference

The five 10m admin-1 shapefile components were retrieved from the immutable Natural Earth commit [`ca96624a56bd078437bca8184e78163e5039ad19`](https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19/10m_cultural):

| File | SHA-256 |
|---|---|
| `ne_10m_admin_1_states_provinces.cpg` | `3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824` |
| `ne_10m_admin_1_states_provinces.dbf` | `7b3244333680d6aec58cc49bde9484177a0baa44c974ec9d371a8f7f1cdb5359` |
| `ne_10m_admin_1_states_provinces.prj` | `a02a27b1d1982c8516d83398e85a3c8b1aef1713c13ef4d84d7bde17430c07c4` |
| `ne_10m_admin_1_states_provinces.shp` | `c6f5c8b4b1320d9417033762419c6df1eb423989cd880fba78ea0b1e3522cbe4` |
| `ne_10m_admin_1_states_provinces.shx` | `37a9e2bc79ed31d3bdea3cb62d928f77281a1c88d645cd33430231c75dbcf350` |

Natural Earth describes its data as public domain. The inspected feature has Natural Earth `adm1_code=ZWE-525`, `name=Harare`, `type=City`, `type_en=City`, `admin=Zimbabwe`, `iso_3166_2=ZW-HA`, `gn_name=Harare Province`, and `ne_id=1159307819`. Natural Earth is a generalized 1:10m map source; these attributes establish identity/label provenance, not a municipal legal boundary or contemporary territory.

## Official sources inspected; explicit restoration instructions

These original official works are not included in the packet. Their URLs, observed hashes when downloaded, and use limits are retained here so they can be restored and independently reviewed.

| Source and exact locator | Date/portion inspected | Observed SHA-256 | Rights/access and relevance |
|---|---|---|---|
| ZamStats, *2022 Census of Population and Housing Preliminary Report*, https://www.zamstats.gov.zm/wp-content/uploads/2023/12/2022-Census-of-Population-and-Housing-Preliminary.pdf | 2022 census; Appendix 3.3, PDF p. 34 | `fa43febbfbde94884d6bdbe82765a43f2e6e882fc90bb3a35cc6eab45fd18dfd` | Official district roster. Eastern Province table lists 15 units, including Chama. No open redistribution license located; not retained. |
| ZamStats, *Eastern Province Census Projections 2023–2047*, https://www.zamstats.gov.zm/wp-content/uploads/2026/04/Eastern-Province-Census-Projections-2023-2047.pdf | 2026 publication based on 2022 census; Table A4, PDF p. 14 | `2473f8a57535413f0012356196ebde06868215dbe620e9ed18903b02f3237ca1` | Independent current roster and projected district tables include Chama in Eastern Province. No open redistribution license located; not retained. |
| ZIMSTAT, *2022 Population Distribution by District, Ward, Sex and Households*, https://www.zimstat.co.zw/wp-content/uploads/Census/2022_Population_Distribution_by_District_Ward_SexandHouseholds_23012023.pdf | 2022; Table of Contents PDF pp. 4–5 and Harare Province map/section PDF pp. 98–101 | `8c941b3c126b2c4f36c4581620867e3ad22613cf2c0b3ff3f392bce8bf5f2d0c` | Official Zimbabwe province/district roster and map; current Harare section names Harare Urban, Chitungwiza Urban, and Epworth. No open redistribution license located; not retained. |
| Chama District Council, *District Integrated Development Plan*, https://www.chamacouncil.gov.zm/wp-content/uploads/2025/02/CHAMA-DISTRICT-INTEGRATED-DEVELOPMENT-PLAN-28_02_2025.pdf | 2025; Governance and General Administration section (PDF p. 9 per indexed document) | Not obtained: TLS certificate validation failed from this host on 2026-10-05; use the linked official locator and verify response bytes before relying on it as a retained original. | Search-indexed text says Chama was realigned to Muchinga in 2012 and returned to Eastern in 2021. The current Eastern Administration and ZamStats sources independently corroborate the current parent. |
| Eastern Province Provincial Administration, “About Us,” https://www.eas.gov.zm/?page_id=118 | Retrieved 2026-10-05; “Our Districts” list | Not retained; page restoration URL supplied. | Government provincial administration lists 15 districts, including Chama. |
| ZIMSTAT, *Harare Province*, https://www.zimstat.co.zw/wp-content/uploads/publications/Population/population/Harare.pdf | 2012 census; district distribution table (search-indexed source excerpt) | Not obtained: the listed URL returned 404 on 2026-10-05; the 2022 report above is the primary current evidence. | The indexed 2012 report lists Harare Rural, Harare Urban, Chitungwiza, and Epworth. It contextualizes the older four-unit composition, not current boundaries. |
| Zimbabwe National Geoportal, “Zimbabwe Administrative Boundaries,” https://zimgeoportal.org.zw/datasets/zimbabwe-administrative-boundaries/ | Retrieved 2026-10-05; resource `zwe_adm_zimstat_ocha_itos_20180911.gdb` | Not downloaded; portal requires account sign-in. | Listing identifies ZIMSTAT/OCHA/ITOS and ADM1 province, ADM2 district, ADM3 ward roles; ODC-BY 1.0 is shown. Potential exact-vector restoration path, vintage indicated by resource date 2018-09-11; current validity remains unverified. |
| Zambia NSDI / ArcGIS, “Zambia Administrative Boundaries Districts 2020,” https://services3.arcgis.com/BU6Aadhn6tbBEdyk/arcgis/rest/services/Zambia_Administrative_Boundaries_Districts_2020/FeatureServer/0 | Retrieved 2026-10-05; layer metadata | Not downloaded or redistributed. | Metadata attributes preparation to OSG, Local Government and Housing, ECZ, CSO, UNZA Geography, and GRID3 and says boundaries were checked against official narratives. The service page did not state a reuse license; geometry not retained. |
| UN SALB Zimbabwe, https://salb.un.org/en/data/zwe and terms https://salb.un.org/sites/default/files/wysiwyg_uploads/docs_uploads/TermsOfUseSALB2021.pdf | Retrieved 2026-10-05 | Not downloaded. | Dataset describes validated national-authority polygon data; terms are noncommercial. Not used or redistributed because project-use compatibility is unestablished. |

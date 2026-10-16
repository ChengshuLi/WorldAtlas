# Independent bounded Vanuatu source-scope review

Reviewed 2026-10-16 against WorldAtlas main `a5f0214a899db981c5e5c0a6974aa8d3a76e1b41`; no repository edits, claims, or source substitutions. Package: `gb-VUT-ADM1--repair-evaluation`, exact 4,366 candidate land cells in blocks 34/35.

## Actionable outcome

For a **retained 2017 geographic-reference repair**, recommend advancing 3,163 numerically qualified cells on separate corroborated islands, while recording 1,203 exact municipal-host-island candidates as conservative unresolved exclusions in this batch. This is a bounded source-use recommendation, not approval of current provincial legal boundaries, complete islands, precise municipal boundaries, or an administrative import.

| Owner | Province | Advance under bounded reference scope | Municipal-host-island review hold |
|---|---|---:|---:|
| 48791 | Shefa | 777 | 615 on Efate, source component 1 |
| 48792 | Malampa | 669 | 0 |
| 48793 | Tafea | 174 | 226 on Tanna, component 2 |
| 48794 | Sanma | 260 | 362 on Santo, component 11 |
| 48795 | Penama | 586 | 0 |
| 48796 | Torba | 697 | 0 |
| Total | | 3,163 | 1,203 |

These holds are a conservative observed component scope, not a finding that 1,203 cells lie in municipalities. A narrower release is possible if the author independently establishes applicable municipal exclusions. No arbitrary distance, buffer, closest island, or source-overlap threshold should substitute for that evidence.

## Independent checks

- Read the exact original simplified source from the retained corpus: 133,712 decoded bytes; SHA-256 `63e1878b1a484787aafa029e3f2a8cb063d9d720b38e9d17884a999d28cd10f8`. Original metadata identifies geoBoundaries/OSM/Wambacher, represented year 2017, ODbL 1.0.
- Read the immutable native latitude table and grid size 262166. A separate even-odd component-centre check places every one of the 4,366 selected cells in its recorded source polygon component, accounting for the full six-feature/57-component source family. Source feature order differs from owner order; joins used exact shapeIDs.
- The package author's independent stock native raster check agreed on all 4,366 cells, all six owner counts, and zero membership mismatches; the author also reported zero current-target coverage and zero rival memberships among the complete six-feature family. These author findings are not represented as independently rerun stock checks here.
- Original #912 full-product research and #1250 simplified/full identity correction remain valid within their limits. Neither grants universal source suitability or current legal-boundary approval. This recommendation does not alter their classifications.

## Corroborating primary evidence

All six NDMO province overview maps were downloaded from the linked provincial-map index, rendered, and visually inspected. They identify the relevant island groups and province separators, and carry creation date **25 April 2017** with sources OCHA, GAUL, Vanuatu National Statistics Office and Ministry of Health. They are small-scale corroboration of island membership, not a legal survey or a replacement raster shoreline.

Index: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps

- Torba: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=48:torba-province-overview-map ; 439445 bytes; SHA-256 `487753ecc5efd4bed5a70a838f6a9ed49997a843baea4fc4673fc36ebcace6d0`
- Malampa: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=49:malampa-province-overview-map ; 853050 bytes; SHA-256 `4f970b035e3c21958dd8dd8a4fb0723614bd790e38231e678eec4d304c806a76`
- Sanma: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=50:sanma-province-overview-map ; 1069476 bytes; SHA-256 `681ccd43d1e8088859cebc57a295a64fa54dbe7825774e8c6e69ef6cf94c8911`
- Shefa: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=51:shefa-province-overview-map ; 585839 bytes; SHA-256 `6056a06458706c1f46f7590ebaf93583c40d336733d9c6862eb7b42bc606bd8d`
- Tafea: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=52:tafea-province-overview-map ; 566782 bytes; SHA-256 `e9eeefa0590ffb5831b761c1d6ad7b3f47bd53c596362201bdedd3f6fcab4c49`
- Penama: https://ndmo.gov.vu/resources/downloads/15-maps/23-provincial-maps?download=53:penama-province-overview-map ; 745613 bytes; SHA-256 `512c779cc2447899c2dd5f2d467c26dac01829508c1ea71ba66e591349195b86`

The fresh DLA province table and profiles corroborate the main island groupings: https://dla.gov.vu/index.php/about-us/provinces and https://dla.gov.vu/index.php/resources/provincial-profiles . Profiles' population figures include urban centres; they therefore cannot themselves be interpreted as municipal exclusion masks.

Component names are in `component-island-crosswalk.json`. Sanma non-Santo components correspond to Lathu, Lataro, Thion, Lathi/Sakao, Malo, Aore, Tutuba and Mavea. Malampa includes Tomman, the Maskelyne group, Paama and Lopevi as well as Ambrym/Malekula. Shefa non-Efate components match Lelepa, Moso, Mataso, Pele, Emau, Nguna, Makira, Emae, Buninga, Tongariki, Tongoa and Epi. Tafea separate-island cells are Aneityum 50, Futuna 21 and Erromango 103. Penama cells are Ambae 96, Maewo 263 and Pentecost 227. Torba includes the Banks/Torres groups; the 21-cell Kwakea component is unlabelled on the small-scale NDMO map but remains within the displayed Torba group; the government 2024 electoral schedule explicitly names Kwakea in the northern constituency context: https://gov.vu/images/publications/Official_Gazette_No_95_of_2024.pdf . Electoral constituencies are not substituted for provincial legal geometry.

## Concrete municipal conflict and limits

The government's consolidated Decentralization Act 2025, section 34, excludes municipalities from Provincial Government Regions. Section 3 puts exact provincial limits in Orders. https://dla.gov.vu/images/legislation/Decentralization%20Act%20CAP%20230.pdf

DUAP's municipality page identifies Port Vila, Luganville and Lenakel: https://duap.gov.vu/index.php/what-we-do/municipalities . Its homepage also mentions Lakatoro/Saratamata/Sola under municipal responsibilities, but that broad web wording does not establish new declared municipalities. Its specific 6 October 2026 Sola launch describes a provincial urban centre and distinguishes municipal/provincial planning jurisdiction: https://duap.gov.vu/index.php/news-2/197-sola-zoning-planning-framework-launched-to-support-sustainable-development . Do not convert a planning-area designation into a municipal exclusion.

A contextual adverse probe against all 66 SPC/OCHA ADM2 features in `vut_admbnda_adm2_spc_20180824` found **85 exact candidate centres inside Port Vila and 2 inside Luganville**. Both sets belong to the held Efate/Santo components. This is concrete evidence against unqualified whole-family approval. Layer dates are 2017-10-31 and validOn 2018-08-24. There is no Lenakel feature; absence is not proof that Lenakel has no exclusion. Service metadata copyright/description are blank, so this is restoration-only contextual evidence, not a licensed authoritative replacement boundary.

Service: https://services.arcgis.com/Zoi8xtp32kQcxoKu/arcgis/rest/services/vut_admbnda_adm2_spc_20180824/FeatureServer/0

The 87 observed cells, contextual polygon bounds, and bbox probes are in `municipal-context-probe.json`. Bboxes are diagnostic only; they are not approved exclusion boundaries. No current provincial Orders or exact Lenakel municipal polygon was authenticated in this bounded review. Full legal-source research is not required before advancing the separately corroborated 2017 reference components, but those sources are needed before claiming complete current administrative coverage.


Public reference PDFs and unlicensed contextual ADM2 payloads were inspected locally and are not redistributed. This packet retains URLs, hashes and bounded derived observations only.

# Official source comparison for two Portugal–Spain gap families

This packet answers the bounded research question in WorldAtlas issue #1299. It preserves the immutable Atlas baseline at `fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7`, the complete earlier source-family and component evidence by reference, direct official provider responses, and reproducible geometry comparisons. It makes no change to Atlas production geography.

## Scope

The analysis covers exactly the two families and four full component geometries listed in `inputs/scope.json`, their four Atlas contact subjects, and five family-contact incidences (Moura is in both families). Complete source shards and the exact consumed Spain 2018 and Portugal 2020 products are retained in the predecessor packets referenced by `inputs/frozen-execution-closure.json`; this packet records their immutable commit/path/byte/hash descriptors rather than copying them again. The 28-member Atlas `ESP-2101` district is treated as an aggregate. Encinasola is checked as one of its source members, never as an alias for the district.

## Official evidence and limits

The direct response bodies and headers are in `sources/official/` and `sources/http-headers/`; `sources/official-capture-index.json` binds the URLs, retrieval times, status, byte counts, and SHA-256 values. The capture script preserves existing receipts on rerun. DGT municipal items are direct OGC API Features responses from the CAOP2025 municipality collection. IGN municipal polygons and the two Spain–Portugal boundary line records are direct OGC API Features items. The linked CNIG resource URLs returned generic landing pages, not item-specific records; the captured responses are preserved as such.

The DGT [CAOP page](https://www.dgterritorio.gov.pt/atividades/cartografia/cartografia-tematica/caop?language=pt) describes CAOP2025 as approved by the Director-General on 2026-01-28 and published in Aviso 3502/2026/2 on 2026-02-18, with changes through 2025-12-31. The directly captured collection metadata is titled CAOP2025 but declares a 2000–2007 temporal extent, and selected items have no effective date. This conflict remains unresolved; retrieval does not establish item validity. The DGT [open-data terms](https://www.dgterritorio.gov.pt/dados-abertos) state CC BY 4.0 attribution.

The IGN [data policy](https://www.ign.es/web/ign/portal/politica-datos), [license conditions](https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf), and [legal notice](https://www.ign.es/web/ign/portal/info-aviso-legal) state CC BY 4.0 terms and attribution to IGN/CNIG. IGN selected administrative polygons have no validity date. The two line items report `date_boundary=2022-04-04` and `legalstatus=agreed`; those Spanish registry attributes do not by themselves establish a bilateral treaty, a matching Portuguese line, or legal ownership. DGT itself states that the Assembly of the Republic has competence to fix administrative boundaries; the DGT map is maintained for cadastral/cartographic purposes. Neither provider response is treated as a legal adjudication.

The official API item bodies declare `Content-Crs` OGC:CRS84, so their coordinates are longitude, latitude. DGT's collection storage CRS is EPSG:3763, but the provider has already transformed returned items. The method compares returned coordinates directly and calculates area with the repository's WGS84 ellipsoidal helper (`scripts/evidence/geometry.py`). It applies no projection, snapping, rounding, buffering, MakeValid, or proximity repair. All original geometries are preserved and checked for validity before overlay.

## Reproduction

`scripts/run-analysis.py` reads the pinned baseline blobs, whole source products and component custody payloads, checks source and identity receipts, and emits full polygon and line overlays under `runs/`. Run it twice in the documented order after committing the producer and frozen input closure. Each run has a separate execution receipt. `scripts/run-controls.py` creates format-bound positive and negative controls and compares every scientific output from the two runs byte-for-byte. `controls/` records those outcomes. Exact runtime, dependency, command, producer revision, and immutable input descriptors are written into the closure and run receipts.

The analyses report administrative polygon intersections, residuals, boundary-line contacts, and whole feature identities. These measurements do not establish physical land/water class, ownership, historical authority, why the original gaps occurred, or that an older source has been replaced legally or operationally. All four component classifications remain unknown. This packet does not certify geography, change source registries, or authorize publication.

## Results

Both paired runs completed with the same producer revision and their 13 scientific output files match byte-for-byte. The six negative controls rejected their perturbed cases; the positive checks preserved known polygon, line, point, and uncovered-residual outcomes.

| Family | Components | Component area | Covered by union of the four whole official municipality items | Uncovered residual |
| --- | ---: | ---: | ---: | ---: |
| `509d6812e22b584f960be362` | 2 | 463,562.09 m² | 462,147.29 m² (99.6948%) | 1,414.80 m² |
| `4c43b39b2038f22dfdedebce` | 2 | 4,668,822.17 m² | 4,667,764.92 m² (99.9774%) | 1,057.25 m² |

By component, the first family has one completely covered member (134,556.05 m²) and one with 1,414.80 m² uncovered (329,006.03 m²). The second family has residuals of 135.78 m² and 921.47 m² against component areas 608,927.88 m² and 4,059,894.29 m². These are planar topological overlay results measured with WGS84 ellipsoidal areas, not a classification of the residuals.

The consumed-source polygons and current Atlas contacts do not exactly match the candidate official polygons. Their old-to-official symmetric-difference areas are approximately 2.29 km² for Rosal, 1.60 km² for Encinasola, 72.84 km² for Barrancos, and 153.67 km² for Moura. Different native identifier schemes and unresolved effective dates remain visible in the records. The Atlas `ESP-2101` aggregate is not an Encinasola alias: the 28 source-member union differs from the Atlas district and remains an aggregate lineage check only. The two IGN line items are analyzed separately against each polygon/component; no Portuguese-side line was captured to establish matched bilateral geometry.

The official item comparisons therefore support a limited answer: the four source families/contact records can be examined against complete current provider features, but the retained metadata does not establish a shared effective vintage or legal equivalence. The small component residuals and larger polygon differences remain unresolved measurements. No cause, owner, physical class, or certification is inferred.

## Engineering handoff by family

| Family | Exact current/original contacts | Official comparison records | Supported geometry and unresolved prerequisites |
| --- | --- | --- | --- |
| `509d6812e22b584f960be362` | Components `physical-component:137a1e1873ef3c0d140480618abd24f8b0125182e0e2c5fbe92242c64ed0cc1a` and `physical-component:a1ad449c3035d6ee93d8c07ac3eef6292300891765e6ba3a7debe76135dc1b2c`; Atlas aggregate `atlas:district:ESP-2101:def08fa9`; consumed source IDs `gb:PRT:ADM2:2272694B13078000098594` (Barrancos) and `gb:PRT:ADM2:2272694B82300393258858` (Moura). | DGT CAOP2025 items 0204 Barrancos and 0210 Moura; IGN Encinasola item 1166667 and Encinasola#Portugal line 5679963. | The two components total 463,562.09 m²; 1,414.80 m² remains outside the four-item union, all in component `a1ad449c3035d6ee93d8c07ac3eef6292300891765e6ba3a7debe76135dc1b2c`. The Spanish registered line intersects the full components for 634.63 m and 542.59 m, but has zero length on either component boundary. It lies on the IGN Encinasola polygon boundary for 18,978.09 m; portions are interior to DGT Barrancos and Moura polygons. A matched Portuguese-side national line, effective CAOP item dates, registration accuracy and legal seam authority remain prerequisites before any boundary conclusion or correction. |
| `4c43b39b2038f22dfdedebce` | Components `physical-component:188a372fefa2333a034123c6a2bb6134f649e44b5be92367725902ea2d568c70` and `physical-component:3d26d33457b023a510afc6d77bbd5441ddca5cc9ea597be323c9c1d6b728616e`; consumed source IDs `gb:ESP:ADM3:28895703B56784737193540` (Rosal de la Frontera) and `gb:PRT:ADM2:2272694B82300393258858` (Moura). | IGN Rosal item 1166698 and Rosal de la Frontera#Portugal line 5671403; DGT CAOP2025 item 0210 Moura. | The two components total 4,668,822.17 m²; 1,057.25 m² remains outside the four-item union (135.78 m² and 921.47 m² by component). The Spanish registered line intersects the components for 790.18 m and 7,068.10 m, but has zero length on either component boundary. It lies on the IGN Rosal polygon boundary for 45,598.46 m and inside the DGT Moura polygon for 22,411.92 m. The matching Portuguese-side national line, effective CAOP item dates, registration accuracy and bilateral legal authority remain unverified prerequisites. |

For both families, the polygon evidence includes full current Atlas contacts, complete consumed-native feature geometries and complete direct official feature geometries. All line/polygon intersections and component residuals are retained in `boundary-line-overlays.json` and the component files. These contacts do not establish that the Spanish line and Portuguese boundaries are mutually authoritative or at the same effective date. The two DGT candidate polygons and the four old-to-official pairs have substantial measured differences; any engineering correction requires the missing dated, registration and bilateral evidence, plus a separate review of the complete exact geometries. The aggregate `ESP-2101` district has 28 members including exact Encinasola; it differs from the union of those 28 source members and remains a district aggregate, not a municipality alias.

## Capture source links

- DGT CAOP2025 page and Aviso 3502/2026/2; direct captured PDF and linked change list are indexed in the capture index.
- DGT open-data terms, CC BY 4.0.
- IGN data policy, license conditions, and legal notice; CC BY 4.0, attribution IGN/CNIG.
- IGN OGC API Features OpenAPI document, captured as part of the source registry.

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

## Capture source links

- DGT CAOP2025 page and Aviso 3502/2026/2; direct captured PDF and linked change list are indexed in the capture index.
- DGT open-data terms, CC BY 4.0.
- IGN data policy, license conditions, and legal notice; CC BY 4.0, attribution IGN/CNIG.
- IGN OGC API Features OpenAPI document, captured as part of the source registry.

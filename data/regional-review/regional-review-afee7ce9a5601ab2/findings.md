# Findings and engineering handoffs

Research date: 2026-10-05. Baseline: `702a55f8e03a2442a153eb1176919feaf84eb115`. See `source-inventory.json` for exact retrieved-byte SHA-256 values and restoration details and `unit-review.csv` for the complete 215-row ledger.

## Scope and completeness

The issue machine block pins 215 unique member IDs in 32 distinct parent IDs. Every scoped ID resolves exactly once in the baseline parts and remains within the declared owned path. The scope split is:

| Area | Scoped rows / full area rows | Coverage |
|---|---:|---|
| Argentina South | 1 / 54 | Partial |
| Paraguay | 195 / 243 | Partial |
| Uruguay | 19 / 19 | Full |

The source tiers are not equivalent across the three places. The Paraguay rows use `gb:PRY:ADM2` (2012, District); Uruguay uses `gb:URY:ADM1` (2017, named local administrative territory); the single `country-SPI` row is a Natural Earth public-domain, undated physical ice-field feature with no administrative role established. The full issue scope has 194 native Paraguay IDs and one Atlas multipart ID. Its two source-member records mean those 195 Atlas rows correspond to 196 2012 source features.

## Paraguay

The pinned 2012 geoBoundaries file has 247 distinct source IDs. A complete ID crosswalk finds 241 one-to-one native locations and six source records represented by two Atlas aggregates: four records (`Asunción`, `Fernando De La Mora`, `Lambaré`, `Villa Elisa`) under `atlas:city:PRY-4837`, and two San Juan del Paraná records under the issue-owned `atlas:multipart:eab6ecd59520b6841455`. No source record is unrepresented in the current country-wide crosswalk. This does not prove current legal or geometric completeness.

For the scoped 194 native rows, the 2012 source `shapeID` and source name match each atlas feature. The issue-owned San Juan multipart row references two source records with variant names. Its metadata states “Disconnected components of the same named source district,” records one topology conflict, and claims reconciliation, while the delivered geometry is `Polygon` with two rings. That is a focused topology/encoding question: in GeoJSON `Polygon`, rings describe one shell and holes; disconnected components ordinarily need a `MultiPolygon`. The packet does not silently change geometry; the downstream reviewer/engineer should verify the two original shapes and intended hole/component relationship before any correction.

The neighboring Asunción aggregate consolidates four distinct ADM2 source rows into a city object. That may be a useful urban-region abstraction, but it is not the same granularity as an individual district. Keep its city identity explicit; do not count that aggregate as four independently addressable districts.

The [Paraguay INE Cartografía Digital 2022](https://www.ine.gov.py/microdatos/cartografia-digital-2022.php) page offers current department and district layers but explicitly says the administrative division boundaries were drawn for statistical operations and are “merely referential.” The [INE 2022 management report](https://www.ine.gov.py/pdfjs/web/Memoria%20de%20gestion%20INE%202022.pdf) reports 263 districts. Those are material current-vintage/completeness signals, not proof of exact current legal boundaries or a direct 16-district change: the 2012 source and later statistical scope have not been crosswalked by statute. Do not promote the 2012 source to present-day legal boundaries without that research.

The geoBoundaries source is CC BY 4.0 according to the pinned subject metadata. Its exact 45,589,273-byte response is above the 32 MiB evidence ceiling, so it is not retained; `source-inventory.json` records its full resolved commit URL, exact hash, retrieval date and restoration instructions. This is not a request to increase the evidence cap.

## Uruguay

The 19 scoped 2017 geoBoundaries ADM1 names match the 19 distinct department names in the current [IGM administrative layer](https://sit.mvot.gub.uy/arcgis/rest/services/07_EXTERNO/LIMITES_ADMINISTRATIVOS/MapServer/3). The current layer says it is based on mapping produced and validated by IGM; its query returns 21 features: the 19 departments plus separate `Isla Brasileña` and `Rincón de Maneco` features assigned to Artigas, with attributes marked “Contestado/a.” The supplemental features are a territorial-meaning and border-parent warning. They must not be silently absorbed into or used to certify the ordinary Artigas unit. The 2017-to-current check here is a name and role crosswalk, not a polygon overlay or boundary approval.

The source metadata for [Uruguay’s Departamentos layer](https://www.ambiente.gub.uy/metadatos/index.php/metadata/md_iframe/55) dates the data to 2024-09-18 and metadata to 2026-07-15 and permits free use with citation to IGM, AGESIC and IDE. The old geoBoundaries source carries ODbL 1.0. Both exact source payloads are retained byte-for-byte; preserve their separate terms if engineering evaluates a replacement. Three scoped departments are MultiPolygon geometries; this confirms multipart cases exist but does not validate their component completeness.

## Southern Patagonian Ice Field

The sole Argentina South row is `country-SPI`, named Southern Patagonian Ice Field. Its source label is Natural Earth, undated modern reference, public domain. The retained baseline feature records `original_geometry_sha256=285e80dadd61de9903bf3070b7a594e4009034d8b67adc304111328da53468ce`, but supplies no direct Natural Earth dataset release or source feature ID, so the original source bytes cannot be independently restored from current metadata; its current Atlas parent is a `framework:province:southern-patagonian-ice-field`. A glaciological area is not an administrative district or country. The [1998 Argentina–Chile boundary agreement](https://tratados.cancilleria.gob.ar/tratado_archivo.php?caso=pdf&id=kqSrmw%3D%3D&tipo=kg%3D%3D&tratados_id=kqOkmJo%3D) specifies a boundary route from Monte Fitz Roy to Cerro Daudet. Argentina’s [2018 Cancillería statement](https://cancilleria.gob.ar/es/actualidad/noticias/inventario-nacional-de-glaciares-en-la-zona-de-hielos-continentales) says the glacier inventory used pre-agreement cartography and that binational demarcation remains pending; inventory inclusion does not prejudge that work. The packet therefore does not infer sovereign ownership or an administrative parent from the glacier outline.

## Explicit handoffs

1. **Engineering / identity and topology:** tracked in [#929](https://github.com/ChengshuLi/WorldAtlas/issues/929); investigate `atlas:multipart:eab6ecd59520b6841455` from both retained source-member IDs. Confirm whether the second ring is a hole, a separate component, or a source overlap before selecting the correct geometry type; preserve the stable atlas ID unless contrary identifier evidence is found.
2. **Geography research / Paraguay current vintage:** tracked in [#926](https://github.com/ChengshuLi/WorldAtlas/issues/926); reconcile the 2012 247-feature source against current legal district instruments and the INE 2022 263-district inventory. Determine row-level successor, merger, creation, naming and boundary changes, and which current geometry is legally suitable. The 2022 INE statistical polygons alone are expressly not legal boundaries.
3. **Engineering / Paraguay granularity:** tracked in [#930](https://github.com/ChengshuLi/WorldAtlas/issues/930); review `atlas:city:PRY-4837` as a city aggregation of four districts and ensure that interfaces or future district-level analysis do not mistake it for a district.
4. **Geography research / Uruguay border meaning:** tracked in [#927](https://github.com/ChengshuLi/WorldAtlas/issues/927); compare the separately flagged contested Artigas features with treaty/official territory evidence and resolve whether they belong in the administrative department shape, a separate contested-territory concept, or neither. No unilateral boundary edit is supported here.
5. **Geography source restoration / type and parent handoff:** tracked in [#928](https://github.com/ChengshuLi/WorldAtlas/issues/928); reassess `country-SPI` as a physical feature and its `province` parent using a geophysical source and the bilateral boundary context; keep boundary uncertainty explicit. Do not change the core hierarchy in this packet.

The five linked child items are deliberately blocked on #446; none changes the current packet’s ownership or claims completion of an engineering/geography correction.

## Limits

The reproduction verifies the pinned roster, source identifiers, exact names where stated, scope counts, licenses/metadata as supplied, and positive/negative controls. It does not calculate a cross-border overlay, validate the 215 geometries against legal survey boundaries, settle disputed territories, or certify a region. The review states above are evidence dispositions, not geography approval.

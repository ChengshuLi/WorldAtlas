# Sourced engineering handoffs for issue #944

These are review and correction candidates, not approvals to change shared geography. Follow repository review and serialized queue controls if an owner decides to modify production/source-release data.

## 1. Reconcile current administrative source register to exact upstream artifacts

The #443 packet’s `source-register.json` records the exact raw upstream objects, while the current `data/administrative-sources.json` expects different bytes for the same source family. The 2026-10-05 upstream GitHub Contents API responses at `wmgeolab/geoBoundaries@9469f09` carry LFS pointers and metadata; #443 retained full raw bytes and exact restoration hashes.

| Source | Current register expected raw SHA-256 | Upstream LFS/raw SHA-256 | Count evidence |
|---|---|---|---|
| Argentina ADM1 | `7cc9b00ba139e57f59611993d96d07eb84d955ed5bd6bd6f1dcb864e1baf549c` | `b5d13177b09ad3347b617a83252cc77bc985f3c70802d4d7a8b50d3fbe5adba6` | 23 features and unique IDs; metadata count 23; current official province list 24 |
| Argentina ADM2 | `cedee8710e49d9017327fc1d4b2dc536e95a82317dc94c3bac8d9404af6bf771` | `f35dae5a257302dea5bd1549ae135baf82e7ee7491918854c3db9bbdec890177` | 525 features and unique IDs; metadata declares 526 |

Confirm intended source vintage and lineage before deciding whether any register hash, count, alias, or source role should change. Do not replace the retained originals or update source pins by assumption.

## 2. Verify twelve parentage candidates from independent current/legal evidence

The Atlas exact 2020 geoBoundaries IDs and labels are in `data/regional-review/regional-review-7cf674a63057d43f/findings/scoped-location-review.csv` and the full per-ID 2020/current overlay is in `findings/scoped-2020-to-current-georef-overlay.csv`. Current official Georef category/province attributes and the equal-area overlay disagree with Atlas parentage for these exact IDs:

| Atlas location ID | Name | Atlas parent | Current Georef top parent/category | Top area share |
|---|---|---|---|---:|
| `gb:ARG:ADM2:61730980B14767108287685` | Vicente López | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 85.28% |
| `gb:ARG:ADM2:61730980B21366789082443` | La Matanza | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 97.98% |
| `gb:ARG:ADM2:61730980B30318397352263` | Morón | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 94.98% |
| `gb:ARG:ADM2:61730980B5073290621442` | San Miguel | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 98.83% |
| `gb:ARG:ADM2:61730980B51340579014160` | General San Martín | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 99.53% |
| `gb:ARG:ADM2:61730980B42310570317073` | Ituzaingó | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 98.28% |
| `gb:ARG:ADM2:61730980B58255414710643` | San Isidro | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 96.89% |
| `gb:ARG:ADM2:61730980B46018574851610` | Lomas de Zamora | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 98.31% |
| `gb:ARG:ADM2:61730980B67082136706980` | Hurlingham | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 90.57% |
| `gb:ARG:ADM2:61730980B88678124443771` | Tres de Febrero | Ciudad Autónoma de Buenos Aires | Buenos Aires / Partido | 93.58% |
| `gb:ARG:ADM2:61730980B13889034691247` | Tafí del Valle | Catamarca | Tucumán / Departamento | 99.01% |
| `gb:ARG:ADM2:61730980B38664240857483` | Juan B. Alberdi | Catamarca | Tucumán / Departamento | 97.37% |

The source layer contains material intersections and vintage differences; do not auto-apply the Georef winners as hierarchy corrections. Reconcile parent meaning and exact boundary lineage against current official/legal records first. #941 treats the separate 17-member CABA city aggregate; it is related but does not adjudicate the ten direct location IDs above.

## 3. Validate current Georef topology before any boundary reuse

The retained official current Georef departments layer has 529 features in three current categories. Within the 214 reviewed 2020 subject footprints, 484 distinct current feature pairs have positive-area intersections above 1 m², of which 446 are at least one hectare. All pairs and subject IDs are retained in `findings/scoped-current-georef-positive-area-overlaps.csv`. The shared equal-area computation found no positive-area pair overlap among the 214 scoped 2020 features themselves above 1 m². Review the current-source overlaps, determine whether they arise from its category mix, source lineage or geometry defects, and locate an alternative lawful dated source if a clean authoritative outline is required.

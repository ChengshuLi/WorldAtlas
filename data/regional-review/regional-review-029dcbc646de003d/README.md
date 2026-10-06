# Southern African interior batch 1 evidence packet

Issue #411 · reviewed 2026-10-06 UTC · read-only geography evidence. This is not regional approval, a boundary edit, an import authorization, or a claim that structurally valid data are geographically correct.

## Reproduce the exact work scope

Run from the repository root with Node 24:

```sh
node data/regional-review/regional-review-029dcbc646de003d/reproduce-scope.mjs --output /tmp/worldatlas-411-scope-run1.json
node data/regional-review/regional-review-029dcbc646de003d/reproduce-scope.mjs --output /tmp/worldatlas-411-scope-run2.json
cmp /tmp/worldatlas-411-scope-run1.json /tmp/worldatlas-411-scope-run2.json
node data/regional-review/regional-review-029dcbc646de003d/build-row-assessments.mjs --output /tmp/worldatlas-411-assessment-run1.json
node data/regional-review/regional-review-029dcbc646de003d/build-row-assessments.mjs --output /tmp/worldatlas-411-assessment-run2.json
cmp /tmp/worldatlas-411-assessment-run1.json /tmp/worldatlas-411-assessment-run2.json
node data/regional-review/regional-review-029dcbc646de003d/validate-evidence.mjs
```

The first program obtains issue #411 through `gh api`, verifies the exact issue body and sorted member-ID digest, crosswalks all 223 IDs to native source `shapeID`s, name-joins them, and compares source geometry JSON structure with the pinned atlas members. It records source and baseline file hashes. The second assigns one `justified`, `correction-needed`, or `insufficient-evidence` outcome per exact ID and stores the evidence dimension and limits on each row.

- `scope.json`: immutable issue/scope snapshot and body hash.
- `scope-reproduction.json`: complete crosswalk, source collection accounting, geometry structure diagnostics and baseline pins.
- `row-assessments.json`: every scoped ID, one issue-required classification, parent, source role/vintage, evidence rationale, dimensions that remain open and bounded handoffs.
- `source-review.json`: source URLs, exact hashes where original bytes were retained, retrieval/vintage/license metadata, supported findings, limits and restoration instructions.
- `evidence-validation.json`: byte pin/scope receipts plus positive and negative source-identity/hash controls. It does not validate geography.
- `sources/`: lawful retained geoBoundaries originals, source metadata, LFS pointers and citation/use notice. The upstream citation/use notice is stored as a deterministic gzip archive because its original text has trailing whitespace; `source-review.json` records both the archive hash and original raw-file hash/length, and `validate-evidence.mjs` gunzips it and verifies exact byte restoration. The boundary GeoJSON and metadata bytes are unmodified.

## Results by area

| Area | Scoped features | Evidence supported | Remaining geographic decision | Row dispositions |
| --- | ---: | --- | --- | --- |
| Angola | 157 municipalities | The source identity/name join matches the 2018 geoBoundaries layer. The 2024 INE census says the old 18-province DPA was replaced by a 21-province/326-municipality DPA under Law 14/24, with actual municipality territory changes. | Map each old municipality and province parent to the current DPA from authoritative current boundaries. The old names/parent nodes cannot be assumed current. Pango-Aluquém is assigned to one of two same-named Cuanza Norte nodes. | 157 insufficient-evidence |
| Malawi | 28 districts | The 28 source names and three region groups correspond to NSO’s 2018 census table. The census separately lists four city rows; OCHA records the 28/32 ADM2 convention ambiguity; NSO/OCHA COD-AB v02 documentation identifies a 32-feature 2023 model with the four city districts. | Establish the administrative/statistical relationship of the four city districts and whether the atlas should use the 28 or 32 unit model; acquire and compare the exact NSO/OCHA 2023 boundary bytes, license and geometry. | 28 insufficient-evidence |
| Mozambique, Gaza and Tete | 29 (14 Gaza, 15 Tete) | INE’s 2024 province yearbooks support the scoped names and province rosters. | 2019 source polygons have not been compared to authoritative current boundaries. Mozambique’s full 159/161 district roster and source lineage belongs to #1042; 121 other source rows are in disjoint #412. | 29 insufficient-evidence |
| Mozambique, Maputo Province | 9 | INE’s 2024 Maputo Province yearbook table lists eight units, including Cidade da Matola. INE separately publishes Cidade de Maputo and its seven municipal districts; the provincial yearbook map distinguishes the City from the Province in its national view. | The atlas parent for the whole Cidade De Maputo feature is the distinct Maputo Province. Recommend a separate Maputo City parent in the combined Mozambique integration; identify/create its canonical parent there and compare boundaries. The province map inset’s “Maputo” label does not exactly match the table’s “Cidade da Matola”; resolve that cartographic label crosswalk. The other eight source polygons are not independently validated. | 1 correction-needed (`Cidade De Maputo` parent); 8 insufficient-evidence |

The exact source/atlas coordinates are not byte-identical for any of the 223 rows. That means the files encode different coordinate structures; it does **not** establish whether they are equivalent, more accurate, topologically valid, complete, or territorially correct. The packet records component counts, ring closure and finite coordinates solely as structural diagnostics. No geometry repair or approval is implied.

The individual screen marks 14 multipolygon rows for follow-up comparison against authoritative geography: eight Angola units, Marracuene and Cidade de Maputo in Mozambique, and Salima, Likoma, Nkhotakota and Mangochi in Malawi. Likoma is an explicit island-coverage candidate; the other components may be islands, detached parts, or source encodings, so the packet does not label them as errors. `Cidade De Maputo`, `Cidade De Tete`, and `Cidade De Xai-Xai` require special treatment as city-named units. `structural_and_granularity_screen` lists exact IDs, component counts, city-named rows and duplicate parent nodes. No source-to-source topology/overlap comparison or authoritative geometry was available, so province-sized footprints, anonymous geometric remainders, full island coverage and neighboring boundary granularity remain open.

## Explicit cross-packet handoffs

- #896 already owns the four 2018 geoBoundaries Cabinda features outside this packet and the current-ten-municipality source problem. They are absent from all pinned atlas partitions; this packet does not absorb or recast them.
- #1042 already owns all 159 Mozambique district IDs, the 161-versus-159 roster and Pemba–Metuge source lineage. Do not create a duplicate. The Maputo City parent finding must be included in that combined roster integration.
- #412 owns the other 121 Mozambique source features from this 159-feature geoBoundaries collection and is ID-disjoint from #411.
- #1045 is the bounded Malawi 28/32 ADM2 and 2023 COD-AB source/geometry follow-up; it depends on this packet. It must not silently add the four out-of-scope city features to #411.
- #1046 is the bounded Angola 2018-to-2024 DPA municipality and parent crosswalk follow-up; it depends on this packet and excludes Cabinda, already owned by #896.

## Source and reuse limits

The three exact geoBoundaries GeoJSON originals, metadata and citation statement were retained with their complete-byte SHA-256 values. The dataset metadata names upstream sources and license; preserve geoBoundaries and underlying-source attribution. The exact official Angola INE 2024 report and Malawi NSO 2018 census report were downloaded temporarily to `/tmp`, hashed, and kept out of the repository because no redistribution grant was verified; `source-review.json` has exact URLs, lengths, hashes and response metadata to restore/verify them. Direct retrieval of the Mozambique INE catalog and 2024 yearbook PDFs timed out from this environment. Their exact official URLs and page-level findings are recorded as restoration instructions, but the binary hashes remain explicitly unavailable. No silent hash or permission inference is made; recover those exact bytes and record hashes before a later geometry/correction decision.

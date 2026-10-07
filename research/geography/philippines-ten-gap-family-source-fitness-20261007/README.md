# Philippines ten-family source-fitness assessment

**Issue:** [#1328](https://github.com/ChengshuLi/WorldAtlas/issues/1328)
**Scope:** 10 complete gap families, all 22 whole components, and all 22 full current contact subjects.
**Disposition:** source research only. No boundary edits, replacements, imports, geographic approval, publishing, or deployment are proposed.

## Result

The retained evidence supports the identity and complete membership of the ten families, and supports a source-relative description of each whole component using the already committed comparison record. It does not support a legal boundary decision or establish why the present geometry differs from the consumed geoBoundaries feature. All 22 present contact geometries differ byte-for-byte at the canonical JSON geometry level from their corresponding consumed 2020 source geometries. That difference is a reproducible observation, not proof of a processing defect or of which geometry is authoritative.

The complete 22 component records retain the original comparison’s current classification. The assessment candidate categories are:

- 11 land observations with a uniquely compatible recorded original administrative subject; candidate for source-processing reproduction after provenance is recovered.
- 4 land observations with partial or unbound administrative source evidence; require source-fitness review.
- 2 mixed-support observations; retain the whole components for source-fitness review.
- 5 outside mapped GSHHG L1 context; exterior is unclassified and is not evidence of water, dry land, or a sovereign boundary.

These counts come from the pinned routing proposal. They are not newly measured by this assessment. The 22 archived physical comparison rows independently carry `unknown-source-fitness-and-observation-date`, `physical_authority: unapproved`, and explicit limits for shoreline/channel registration, river width, seasonal wetness, observation-date mismatch, and source precision. The source comparison is GSHHG 2.3.7, released 2017-06-15; its shoreline observations are heterogeneous in date and scale. It cannot settle narrow channels, intertidal position, municipal jurisdiction, or legal ownership.

Every candidate is assessed in [component-assessments.json](records/component-assessments.json); whole-family closure and family-level member associations are in [family-reconciliation.json](records/family-reconciliation.json); all 22 complete contact subjects and the identity crosswalk are in [contact-assessments.json](records/contact-assessments.json). The family-level contact list does not imply a one-to-one component/contact pairing.

## Complete family coverage

| Family | Whole components | Contact subjects |
|---|---:|---|
| `2b763da6d6517190290ab5f0` | 2 | Labangan, Lapuyan |
| `311ea8b4d8aa38b2c4452d93` | 2 | Maigo, Kolambugan, Bacolod |
| `77a05f82d3c0e198a31dece6` | 3 | Aroroy, Balud |
| `99ec3c89d4f3492d0c7920f9` | 5 | Pandami, Tongkil, Hadji Panglima Tahil, Pangutaran |
| `a1a36c3a6ab6ee299d18af6a` | 1 | Cavite City |
| `a6aa29a8a9c5f3b294c449fe` | 2 | Tabuan-Lasa, Lantawan, Maluso |
| `a99f14273c9f337422360ac1` | 1 | Nueva Valencia |
| `adc55101cf538a9ac41cd48c` | 4 | San Jose, Lavezares, Rosario, Laoang |
| `b51c9336b243857845989544` | 1 | Catarman |
| `eadfeb578c3d20950962f38a` | 1 | Limasawa |

The contact associations above are family-scoped as represented by the pinned original proposal. Components have their own stable IDs and complete candidate pointsets in that proposal and their 22 complete source-relative rows in the preserved physical comparison record.

## Source fitness and authority

The consumed source is the simplified geoBoundaries Philippines ADM3 file, retrieved and preserved in the original corpus capture on 2026-10-06. The exact retained bytes are `inputs/gb-PHL-ADM3.original` (7,071,267 bytes; SHA-256 `2ece3d44a5c6a2afb385ffbf3a6b88d83e4d3a3e7eed9a52cb3be1bc59e289fc`). The source capture has 1,647 features. The matched 22 original features are separately retained without simplification in `records/original-source-features-22.json`; all 22 current complete contact features are in `records/current-contact-features-22.json`. The original corpus catalogue records the consumed simplified URL and represented year 2020. The upstream metadata also has a distinct unsimplified download URL: it must not be mistaken for the actual consumed simplified bytes. The source is GeoJSON without an explicit `crs` member; RFC 7946 specifies WGS 84/CRS84 decimal degrees, longitude first and latitude second. This standard-based parsing does not authenticate the historic producer’s full CRS processing chain.

The upstream source metadata reports origin credits to NAMRIA, the Philippine Statistics Authority (PSA), and OCHA Philippines, and records an underlying CC BY 3.0 IGO license. The geoBoundaries gbOpen material is described under CC BY 4.0 in its current API documentation. Preserve both source and derivative attribution; the retained upstream metadata does not resolve every downstream license question for derivative source materials. Do not broaden redistribution beyond the repository’s existing use without reviewing those terms.

The source’s generic `ADM3` tier identifies administrative level, not a uniform legal unit type. Its current WorldAtlas metadata calls this source `Municipalities` for all 22 contact features. The PSA 2026 PSGC lists 21 as municipalities; Cavite City is classified as a city and appears as “City of Cavite” (PSGC 0402105000). The other subjects’ municipality PSGC codes are retained in the contact assessment. This is a present-day identity/role crosswalk only. It neither proves the 2020 legal boundary nor supplies a date-appropriate boundary crosswalk. This is a supported metadata-role quality finding: downstream classification should use an independently reviewed, vintage-specific PSGC crosswalk rather than infer that all ADM3 units are municipalities.

The Philippine Local Government Code (Republic Act 7160) provides the legal framework for creation and boundary alteration of local government units, including by law or ordinance, and boundary-dispute processes. For each of these named units, a legal boundary finding still requires the operative statute/ordinance, effective date and any required plebiscite evidence, tied to an official survey or cadastral plan. This packet does not contain or authenticate those unit-specific legal instruments or plans.

NAMRIA is the national mapping and hydrographic authority and publishes administrative maps, nautical charts, topographic maps and hydrographic survey standards. The current NAMRIA download catalogue lists the 2025 third edition of its hydrographic standards. Product availability, scale, chart datum, shoreline tidal datum, source date, and reuse terms vary. NAMRIA materials reviewed for this handoff do not establish complete suitable coverage for these 22 components. Obtain and document the specific sheet/survey and permission before relying on it. For intertidal shorelines, preserve the survey date and tidal datum; chart shoreline reference and land mapping references are not interchangeable.

The physical comparison input is the existing GSHHG 2.3.7 release (2017-06-15). Its L1 class is an ocean/land shoreline context, not an administrative boundary. GSHHG is built from heterogeneous shoreline sources; no single observation date is established for these Philippines segments. Its archived result rows state that mapped support cannot resolve registration-sensitive shoreline/channel truth and that river widths, seasonal wetness, date mismatch, and source precision are unmeasured. The comparison archive’s README contains an internal license wording conflict (LGPL “v3 or later” versus “v3 or earlier”); that issue remains unresolved. The source package was not recopied here; selected original rows are retained with their original Git commit and complete row digests in `records/physical-comparison-rows-22.json`.

No independent satellite scene, raster, orthophoto, bathymetry, or survey was queried in this assessment. Therefore there is no image `NoData`, cloud mask, pixel size, affine transform, or scene date that can be used to claim support. If imagery is later used, preserve those fields and its actual coverage for every scene.

## Engineering handoff

1. Keep all 22 components and all 22 contact subjects in scope; do not infer one-to-one associations from family membership.
2. Before processing reproduction, retrieve the exact geoBoundaries 2020 release/source recipe and identify which original inputs and generalization/simplification steps produced the consumed simplified bytes. Preserve code, software/runtime, parameters, CRS, datum, and all intermediate/source hashes.
3. Retrieve date-appropriate legal instruments and authoritative survey/cadastral plans for each local government unit. Tie each plan’s coverage, CRS/datum, survey date, scale, accuracy and approvals to the whole component. Obtain reuse terms.
4. Obtain suitable NAMRIA chart/map/survey, orthophoto or other independent imagery only with coverage and date metadata. Record tidal/chart datum for shoreline evidence and source accuracy/registration for narrow channels. Compare multiple sources only after their dates, scales and dependence are understood.
5. Treat a compatible original administrative subject as a candidate for exact source-processing reproduction, not as authority to copy or repair a boundary. Treat partial/unbound, mixed, and exterior cases by their exact categories in `component-assessments.json`.
6. Keep Cavite’s city/municipality role distinct in any current metadata crosswalk. Apply a dated PSGC/administrative classification review before changing metadata.
7. Submit any eventual geometry or metadata implementation under its own scope, source packet, and independent geographic approval. This packet does not authorize one.

## Preserved evidence and reproduction

- `inputs/root-philippines-ten-full-family-source-fit-proposal.json`: full immutable upstream preparation; recorded SHA-256 `5582eeb86f274c2a1d3939f2e8dcaaaeb29473c8d7f58427d6f84ae92f2dab1e`.
- `inputs/root-philippines-ten-original-source-handoff.json`: full original-source handoff and 22 source subjects; recorded SHA-256 `e743bcc7287a0d45ff88033aa737f66f6209c8a7f604329aae7544d1916bf1b1`.
- `inputs/source-register.json`: cited source roles, vintages, license disposition, and limitations.
- `records/extraction-runs.json`: two-run exact-byte reproduction receipt.
- `records/physical-comparison-rows-22.json`: complete 22 selected records. Each canonical JSON+newline SHA-256 matches the proposal’s `whole_physical_row_sha256`; raw source-line digest is also separately kept. The exact archived source commit and all 18 containing result paths are listed in this file.
- `inputs/claim-receipt.json` and `inputs/readiness-receipt.json`: exact reservation and complete readiness receipts.
- `evidence-quality.json`: pinned baseline/contact file closure, source licensing and temporal status, source limitations, and exact output inventory.
- `inputs/evidence-validator-constraint.json`: exact checker failure for binding the issue-pinned whole-source SHA to the compressed baseline capture. The issue pin is preserved as given.

The evidence-quality checker currently rejects the authoritative source pin because the exact raw source is an uncompressed retained extraction while the immutable Git baseline stores it compressed. The catalogue authenticates the uncompressed SHA, but the checker binds a pin only to a whole baseline file SHA. A temporary diagnostic with only this issue pin omitted passed all other byte and contact-containment checks; the authoritative manifest retains the issue pin and the validation failure. This repository-wide validation contract is outside the owned research folder and needs maintainer resolution before this packet can pass the required premerge gate.

The original proposal’s whole routing closure refers to the actually merged routing commit `0198938719a5666b6726fb6a1e45779926eefeb2`. The current base commit for this packet is pinned separately in `scope.json` and `evidence-quality.json`. These are separate vintages and should not be substituted for one another.

### Primary references

- [Philippine Republic Act No. 7160, Local Government Code](https://officialgazette.gov.ph/1991/10/10/republic-act-no-7160/)
- [PSA PSGC municipalities](https://psa.gov.ph/classification/psgc/municipalities), [PSA PSGC cities](https://psa.gov.ph/classification/psgc/cities), and [PSGC summary](https://psa.gov.ph/classification/psgc/summary)
- [geoBoundaries API and licensing/source metadata](https://www.geoboundaries.org/api.html) and [the archived geoBoundaries 3.0.0 release (2020)](https://github.com/wmgeolab/geoBoundaries/tree/7c8dbc5)
- [RFC 7946 GeoJSON coordinate reference and axis order](https://www.rfc-editor.org/rfc/rfc7946.html)
- [NAMRIA Administrative Map of the Philippines](https://www.namria.gov.ph/home.aspx/Downloads/Downloads/AdminMap/Administrative_Map_of_the_Philippines.pdf), [NAMRIA map/chart products](https://namria.gov.ph/products.aspx), and [NAMRIA Downloads listing the 2025 third edition of the National Standards for Hydrographic Surveys](https://namria.gov.ph/downloads.aspx)
- [GSHHG official data and documentation](https://www.soest.hawaii.edu/pwessel/gshhg/)

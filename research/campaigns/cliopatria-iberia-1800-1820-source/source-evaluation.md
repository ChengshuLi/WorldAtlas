# Cliopatria Iberian ownership evidence, 1800–1820

Issue #62; source-only review retrieved 2026-10-03 UTC. This examines ten source records and up to four region-level citations connected to the exact pinned Cliopatria version. It does not rerun spatial-majority preparation, resolve borders, or modify ownership records.

## Pinned source and date model

The retained source inventory points to Bennett et al. (2025), *Cliopatria: a dataset of world-wide polities from 3400 BCE to 2024 CE*, DOI [10.1038/s41597-025-04516-9](https://doi.org/10.1038/s41597-025-04516-9). The exact app-pinned release is GitHub tag `v0.2.0-duplicate`, commit `ad28a691b7c07c1fca89d0e0636d324667d2a258`; its public `cliopatria.geojson.zip` was downloaded and its SHA-256 exactly matches the retained index value `d01ae3a20d358cc5d54f69d9d725d390767d9c8759ac89ad6f90c58d106f3370`. The upstream tag LICENSE.md and article license state CC BY 4.0. This licenses the dataset with attribution/change notice; it does not replace the separate rights of cited books/maps or grant reuse of those source works.

The released source uses integer `FromYear`/`ToYear` values inclusive. The atlas-local derived copy stores `source_from`/`source_to` alongside half-open `valid_from`/`valid_to`; those normalized intervals are not new annual observations. Cliopatria’s article describes 508 dated map images with irregular intervals. It says maps were copied forward and incrementally edited, with more frequent snapshots near the present. It does not supply a continuous annual Iberian history or a citation key connecting each GeoJSON row to a specific reference/page.

## Ten source records

The selected records are the first ten in the source archive’s feature order whose record geometry intersects a broad retrieval rectangle around Iberia (WGS84 −10° to 5°E, 35° to 44°N), whose inclusive source years intersect 1800–1820, and whose source `Name` is Kingdom of Spain or Kingdom of Portugal. The rectangle is only a record-selection window, not a proposed boundary. Source FIDs are the stable zero-based feature positions assigned by GDAL to this exact, hash-pinned GeoJSON; the source features do not themselves contain an explicit `id` property. Each identity should therefore be read as `(archive SHA, FID, Name, FromYear, ToYear, SeshatID)`, not as a durable ID across versions.

| GeoJSON FID | Name | Source interval (inclusive) | Wikidata | SeshatID | MemberOf |
|---:|---|---:|---|---|---|
| 9489 | Kingdom of Portugal | 1709–1808 | Q45670 | `pt_portuguese_emp_2` | (Portuguese Empire) |
| 10531 | Kingdom of Spain | 1800–1802 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |
| 10578 | Kingdom of Spain | 1803–1808 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |
| 10750 | Kingdom of Spain | 1809–1810 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |
| 10760 | Kingdom of Portugal | 1809–1810 | Q45670 | `pt_portuguese_emp_2` | (Portuguese Empire) |
| 10800 | Kingdom of Portugal | 1811 | Q45670 | `pt_portuguese_emp_2` | (Portuguese Empire) |
| 10811 | Kingdom of Spain | 1811 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |
| 10868 | Kingdom of Spain | 1812–1813 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |
| 10874 | Kingdom of Portugal | 1812–1823 | Q45670 | `pt_portuguese_emp_2` | (Portuguese Empire) |
| 10915 | Kingdom of Spain | 1814 | Q29 | `es_spanish_emp_2` | (Spanish Empire) |

The 1709–1808 and 1812–1823 source intervals are retained intact; their intersections with this issue’s window are only 1800–1808 and 1812–1820, respectively. These ten examples do not cover every image year in 1800–1820, and the sparse source intervals must not be expanded into annual claims. The raw data do not expose a per-feature citation list. The local generated record IDs are a separate normalized index and are not assumed to equal upstream GeoJSON FIDs.

## What “ownership” can and cannot mean here

The article defines a polity as a political unit independent of higher authority, but describes the dataset as one reconstructed version of territories held by polities, drawn on hand-created map images. It says changes can reflect occupation or treaties, and that polities may include component or composite relations. `MemberOf` associates the Kingdom records with Spanish/Portuguese Empire composites; it does not itself say whether the relationship is sovereignty, a personal union, colonial control, occupation, or a disputed claim at a particular place and date. A `POLITY` label and colored map area are evidence of the authors’ reconstruction, not direct local proof of de jure sovereignty, military control, or a competing claim.

The 2025 article warns that boundaries without explicit treaties are approximate, territorial disputes and border uncertainty are not encoded, and historical interpretations can differ. Source maps were hand-drawn from earlier images and sources, then raster-to-polygon digitized and smoothed; residual discrepancies and source-map scale matter. The exact ten records do not carry confidence or alternative-border fields. Their `Area` values are polygon area measurements, not a sovereignty denominator or a share of total Iberian territory; the product supplies no per-feature claimant or territorial-coverage denominator. This review did not rerun location overlays, check historical treaties, or infer a dominant claimant. The appropriate interpretation remains “Cliopatria reconstructed polity-territory support for its stated interval, with unresolved local sovereignty/control/claim semantics.”

## Four cited Spain-region references reviewed

The article’s Table 1 groups citations 89–92 under the modern-region label “Spain”; it does not say which of these sources supports which feature, map year, or boundary segment. It also does not list a separate Portugal citation group. This region-level bibliography therefore cannot serve as per-feature provenance for the ten rows.

- **89.** García de Cortázar Ruiz de Aguirre, *Atlas de historia de España* (Planeta; bibliography shows “2005., 2009”). This is a secondary historical atlas citation. The book/pages were not accessible in the bounded check, the two dates are ambiguous in the article citation, and no page/map reference is tied to a selected feature.
- **90.** Campo Arqueológico de Tavira, “Cidades pré-romanas, indígenas e coloniais, que emitiram moeda até 45 a.C.” The cited JPEG was retrieved; the image itself describes pre-Roman groups/cities and coinage through 45 BCE, far outside 1800–1820. It bears a “reserved rights / reproduction prohibited” notice. Its access does not permit reuse, and it does not support the selected modern-era records.
- **91.** Wikimedia Commons, “Expansión peninsular de la Corona de Aragón.svg,” attributed to HansenBCN, CC BY-SA 3.0. It concerns the Crown of Aragon’s historical expansion, not the 1800–1820 interval. Its license and attribution apply to that image, not Cliopatria generally; this review does not reproduce it.
- **92.** de Abreu Galindo, *Historia de la conquista de las siete islas Canarias* (Goya, Santa Cruz de Tenerife, 1977). Only the article’s bibliographic citation was available; the book text/pages and any reuse terms were not inspected. The citation title concerns conquest history and is not mapped to a selected feature or 1800–1820 snapshot.

The first two inspected linked items are temporally or semantically outside this review window; the two cited books remain unverified at page level. The four references are regional construction references, not four confirmed direct sources for each selected row. Exact URLs, file hashes, access dates and restoration details are in `source-manifest.json`.

## Snapshot checks and verdict

The exact upstream tag contains map images for 1800, 1803, 1809, 1811, 1812, 1814 and 1820 CE, all with attribution/hash pins in the manifest. The numeric suffix alone is ambiguous: `B011-1800.PNG` depicts an 1800 BCE map (its legend names ancient polities), whereas `C304-1800.PNG` depicts an 1800 CE map (its legend includes the Kingdom of Spain and Portuguese Empire). Do not infer era from “1800” alone. These map images are input reconstructions, not primary local documents, and do not expose a row-to-pixel provenance key.

**Suitability:** The data is suitable for a clearly attributed, versioned and uncertain reconstructed polity-territory reference, subject to CC BY 4.0 and separate third-party source rights. It is not sufficient by itself to adjudicate an Iberian location’s sovereignty versus occupation, control or competing claim during 1800–1820. The key gap is absent row-level source citations/page numbers and unencoded border/claim uncertainty. Retain the current source IDs, version, half-open conversion receipts and unresolved/disputed results; do not silently make direct local claims. Any correction to preparation/overlays is a separate engineering child. No location assignments or imports were made. Later content still requires the complete published regional certificate, exact permitted subjects and matching release pins.

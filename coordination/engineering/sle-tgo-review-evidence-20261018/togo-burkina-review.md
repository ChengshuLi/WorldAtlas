# TGO historical bounds follow-up: Burkina Faso source families

Read-only review of retained records for TGO frozen discovery result `80cf469d70a68b3ea475ff861d611f297cfcce56`. The exact result path, size, and SHA-256 are confirmed in `worker6-tgo-crossfamily/result-pin-reconciliation.md`: 457,291 bytes; `d0ede54cec455302cf50dce6bd593ff1920cfedf289c1c4eba3c7842e2c81e7d`. The run reports complete families BFA ADM1 13 / 2 candidates, ADM2 45 / 2, ADM3 351 / 4; candidates are conservative whole-source bounds overlaps. This review did not inspect coordinates or run GIS.

## Exact executed candidate-family pin join

The newly retrieved frozen JSON reconciliation identifies each BFA family from the executed result itself, rather than inferring candidates from the previous Burkina screen. All three source parts are pinned at corpus commit `cddcde8786f038568137d915c8ee8436475f1688`; the result declares method `721dac0bf4722ab2a7e0092746bbf3e17e9daa61` and 374 actual input pins.

| Result family | Whole product SHA-256 | Executed source-part blob OID | Compressed payload bytes / SHA-256 | Candidate source IDs in executed result |
|---|---|---|---|---|
| `gb:BFA:ADM1` | `651c170ce5570e020448e9ba29c69a749a40d663f06ba4114ddee561bfdce670` | `44af49a9ad8db7205ec0207cf1bcdce7a3e304dc` | 113,500 / `1ab92de8d476665fa930d9f6f3544bb76e6ecada54ee49665986709bb54183f9` | `gb:BFA:ADM1:92566538B37033565003987`; `gb:BFA:ADM1:92566538B57532963969301` |
| `gb:BFA:ADM2` | `b9882ee6269fd2b45276e420cafffb544c87519ab478024f7080712a52cd50a9` | `1730fffbbdf27d4d0ff873c0a2fa73495c0ceef3` | 196,160 / `6bf8cfb7404982e6d2a11546b7076b8ee6c861018e490282e680b46b47a21ab6` | `gb:BFA:ADM2:67063806B79770817740465`; `gb:BFA:ADM2:67063806B92956545078683` |
| `gb:BFA:ADM3` | `e6f8af518e7dffd7d2e7bb95fbba41f0ed3287ebb04b8f55762d2737c563d6c9` | `4e0d2b4854611ccf3a658147f3b7dcf545878d60` | 356,927 / `bc9643a304f60126e698bcd2f7f5d29845cdf4e0a24a5676593fb21b61180ca4` | `gb:BFA:ADM3:42667915B86323840923551`; `gb:BFA:ADM3:42667915B70270719794468`; `gb:BFA:ADM3:42667915B94917626590271`; `gb:BFA:ADM3:42667915B17660336171443` |

## Catalogue and native archive identity

TGO's consumed catalogue is `worker5-tgo-readiness/actual-discovery-001/original-extractor-inputs-21984/retained-source-catalogue.json`. Its three BFA entries bind the complete original raw metadata byte streams (partitioned contiguously, without JSON geometry reserialization):

| Family | TGO whole-family features | Consumed catalogue original SHA-256 | Consumed compressed part SHA-256 | Exact consumed URL / represented year / declared label |
|---|---:|---|---|---|
| `gb:BFA:ADM1` | 13 | `651c170ce5570e020448e9ba29c69a749a40d663f06ba4114ddee561bfdce670` | `1ab92de8d476665fa930d9f6f3544bb76e6ecada54ee49665986709bb54183f9` | `.../releaseData/gbOpen/BFA/ADM1/geoBoundaries-BFA-ADM1_simplified.geojson`; 2017; CC BY 4.0 |
| `gb:BFA:ADM2` | 45 | `b9882ee6269fd2b45276e420cafffb544c87519ab478024f7080712a52cd50a9` | `6bf8cfb7404982e6d2a11546b7076b8ee6c861018e490282e680b46b47a21ab6` | `.../releaseData/gbOpen/BFA/ADM2/geoBoundaries-BFA-ADM2_simplified.geojson`; 2017; CC BY 4.0 |
| `gb:BFA:ADM3` | 351 | `e6f8af518e7dffd7d2e7bb95fbba41f0ed3287ebb04b8f55762d2737c563d6c9` | `bc9643a304f60126e698bcd2f7f5d29845cdf4e0a24a5676593fb21b61180ca4` | `.../releaseData/gbOpen/BFA/ADM3/geoBoundaries-BFA-ADM3_simplified.geojson`; 2007; Public Domain |

For all three families, the source catalogue full-byte hashes and feature counts exactly match `worker2-next-source/all11-actual-foreign-archive-custody.json`'s `census_complete_original_sha256` and complete native feature counts. That separate retained archive manifest binds the native packages to immutable geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d`, `sourceData/gbOpen/BFA_ADM{1,2,3}.zip`, and LFS OIDs equal to the native archive SHA-256s below. I independently rehashed the retained ZIPs; all matched the manifest. This is a positive source-family/version identity join, not a claim that releaseData simplified GeoJSON bytes equal sourceData ZIP bytes or geometries.

| Native archive family | Bytes / SHA-256 | Retained immutable LFS OID | Key native member pins |
|---|---|---|---|
| ADM1 | 857,130 / `4ec91d9a6f83b6ddc697bb7b6f81d26c9c81daa0f136897053c16804d213f90a` | same | `meta.txt` 429 / `f8ac1a8edcc8086a0f53e46ebae85184852115f05314c6752a19a11ad0fd2421`; `license.png` 588,876 / `4c495639f9ce0ee8b174fcf7d8ec03376b0c7ae10337c38ceee2e5c252801934`; PRJ 143 / `98aaf3d1c0ecadf1a424a4536de261c3daf4e373697cb86c40c43b989daf52eb` |
| ADM2 | 1,116,358 / `f9098548d0a9c4545e8988afd4acc1e99135052c253884cffe06f95eadc5b2fe` | same | `meta.txt` 431 / `ee413309c949d10c8f9949753733d8f61888224db1e6fca2f291cc6a43f68bb0`; `license.png` same ADM1 image/hash; PRJ same ADM1 hash |
| ADM3 | 1,211,396 / `f11fd8438c5bdbe638cb58f13c07b150539845b46e1c0d0cd4a8165de5ae9f8b` | same | `meta.txt` 469 / `fb8cc660eb771cf0d39487b17c69c0368da5778f19d0698c5de00027a224fd3a`; `BFA_ADM3.shp.xml` 351,657 / `0bb21e424dd0e48d7536cedde29d72b5c5bfddaa1f3d043fa27adfa0db446e18`; PRJ 145 / `a02a27b1d1982c8516d83398e85a3c8b1aef1713c13ef4d84d7bde17430c07c4` |

TGO's retained `archive-evidence/BFA_ADM1/` independently matches ADM1 sidecar metadata, license-image, and CRS hashes. TGO packet does not contain ADM2/ADM3 sidecars; those exact pins above are from the retained full-archive manifest and extracted metadata package in `worker2-next-source`.

## Vintage, provenance, terms, and source-role limits

- **ADM1:** Native metadata says representative year 2017, Regions, World Bank, CC BY 4.0. The actual embedded image is a generic World Bank public-license explanation, not a screenshot of a product-specific grant. Preserve attribution and the cited underlying-source limit; do not overstate the image as a tailored provenance proof. Native fields are Name/Level/ISO_Code and the archive census confirms all 13 records.
- **ADM2:** Native metadata says representative year 2017, Provinces, World Bank, CC BY 4.0. Its image is byte-identical to ADM1's generic World Bank license image. It is a separate complete level-2 layer, not a substitute/equivalence claim for ADM1 or ADM3. Native fields are Name/Level; 45 records retained.
- **ADM3:** Native metadata and XML identify January 2007 commune boundaries, Map Maker Ltd., surfaced through Stanford/NYU; declared Public Domain, with XML terms stating no access/use restrictions. There is no embedded license image in this archive. XML credits Map Maker (2007), describes the layer as an amalgamation of public-domain data and edge matching, and cautions that older subdivisions were retained and all-capital names may be unverified or obsolete. Treat that as historical compilation provenance and a material vintage/semantic limitation, not current administrative truth.
- **CRS:** ADM1/ADM2 PRJs declare geographic WGS 84 in degrees (143-byte records); ADM3 declares the same geographic WGS 84 degree frame (145 bytes). This confirms only native frame declarations, not candidate fit or a geometry operation.

## Disposition and limits

Pin-level identity is adequately supported for these three complete families: TGO's immutable source parts agree with the retained full-source metadata hashes/counts, and each `sourceData` archive/member record is tied to the immutable upstream commit and matched LFS pointer. There is no evidence here that these pins prove a current Burkina boundary, historical Togo relevance, source authority, native-source preference, or repair permission. The bounds candidates only retain conservative overlaps in TGO's frozen historical screening scope. No role is established for using Burkina polygons as Togo administrative units.

The other Burkina screening review's selection counts (ADM1 2, ADM2 4, ADM3 12) use a different target/source scope; they are not interchangeable with TGO's 2/2/4 result, nor evidence about the same candidate set. No cross-run feature or geometry equivalence was inferred. No additional phase, source query, geometry processing, or clearance is recommended from this evidence alone.

## Evidence paths

- Executed result IDs and exact corpus-part OIDs/payload pins: `worker6-tgo-crossfamily/result-pin-reconciliation.md` (which identifies the frozen JSON, commit bindings, and readback hash). Catalogue and run summary cross-check: `worker5-tgo-readiness/actual-discovery-001/original-extractor-inputs-21984/retained-source-catalogue.json`; `worker5-tgo-readiness/actual-discovery-001/first-discovery-summary.json`.
- Archive hashes, immutable pointers, all member pins, metadata/CRS literals, native record counts: `worker2-next-source/all11-actual-foreign-archive-custody.json`.
- Extracted ADM1/ADM2/ADM3 metadata and CRS bytes: `worker2-next-source/actual-foreign-native-metadata/BFA_ADM{1,2,3}/`.
- ADM3 XML provenance/terms: `worker2-next-source/actual-foreign-xml-qmd-observations.json` and `worker2-next-source/actual-foreign-native-metadata/BFA_ADM3/BFA_ADM3.shp.xml`.
- Concise prior archive/license limits: `worker2-next-source/complete-foreign-source-rights-review.md`.

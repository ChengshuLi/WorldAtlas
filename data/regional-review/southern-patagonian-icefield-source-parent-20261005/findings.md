# Findings: `country-SPI`

Research date: 2026-10-08. Issue contract baseline: `27be77596f23304de6a720735538427e6d23e242`. See `baseline-files.json`, `source-inventory.json`, and the deterministic `reproduction-results.json` for exact pins and hashes.

## Atlas identity and present parent

The issue pins `data/geography/part-28.json` at SHA-256 `2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d`. The pinned file contains exactly one feature with `properties.id=country-SPI`; its name is `Southern Patagonian Ice Field`. The feature records Natural Earth as its source, an undated modern reference, public domain, and `administrative_level=ADM0 fallback`. It has no source dataset release or source feature ID. Its `original_geometry_sha256` is `285e80dadd61de9903bf3070b7a594e4009034d8b67adc304111328da53468ce`.

The pinned hierarchy puts this feature under `framework:province:southern-patagonian-ice-field:7fa95a3f233f`. That parent is named for the same physical feature, has one child, uses `kind=geographic`, retains a Natural Earth reference, and has open semantic review. Its own parent is `framework:area:argentina-south:240c9829681f`. The member and parent labels therefore do not establish that the ice field is an administrative province or belongs to Argentina as a sovereign territory.

## Dated Natural Earth source candidate

The retained candidate is the Natural Earth 1:10m `ne_10m_admin_0_map_units` GeoJSON at the immutable v5.1.0 packaging commit `117488dc884bad03366ff727eca013e434615127` (2022-05-05). Its whole-file SHA-256 is `57da82be755f4afccd8f3b14251bb2752f5df1395f47d2d86f817470c4a48862` (13,526,439 bytes). One row has `ADM0_A3=SPI`, `NE_ID=1729635141`, and the exact name. The source marks `TYPE=Indeterminate`, `NOTE_ADM0=Disputed`, `NOTE_BRK=Claimed by Chile and Argentina; under survey`, and ISO codes `-99`. Natural Earth's official terms page states its vector and raster data are public domain. The retrieved terms-page bytes are not retained; their exact hash and restoration instructions are recorded in `source-inventory.json`.

This dated source resolves the identity and intended map meaning behind the old undated Natural Earth label. It does not verify the Atlas feature's exact input geometry: the candidate feature geometry SHA-256 is `08e44b0ec89bdfd84be2a604c01396778ac0130923676c67bd313ba0553f61f4`, which differs from the Atlas feature's recorded original geometry hash above. The candidate has 40 exterior-ring coordinates; the currently retained Atlas display feature has 59. No coordinate normalization or matching method was found that establishes the original source bytes. Do not silently replace the feature with the candidate.

Natural Earth is a cartographic reference generalized for a 1:10m world map. The source's map-unit classification and dispute note are useful evidence about the label and boundary representation; the file is not a dated glaciological inventory or an authoritative bilateral boundary record. Its scale/generalization is not suitable to certify present ice margins or administrative limits.

## Physical geography, completeness, and neighboring granularity

The Argentine IANIGLA/CONICET National Glacier Inventory describes the Andes of Southern Patagonia as 45–54°S and states that the Southern Patagonian Ice Field covers about 12,100 km², with 2,662 km² in Argentina. It also describes multiple outlet glaciers and distinguishes glacier fields from valley and mountain glaciers. This supports the named feature's physical-geography role at an aggregate ice-field scale. It does not authenticate the Atlas perimeter or settle the border.

Chile's DGA says its 2022 Public Glacier Inventory catalogs glaciers across continental Chile; the official page currently reports 26,180 glaciers and links to the downloadable shape set. A 2024 DGA report says the Magallanes and Chilean Antarctic Region contains 7,056 glaciers covering about 10,426.6 km², mainly in Campos de Hielo Sur. This is glacier-body granularity and Chile-only scope. We did not retrieve the very large DGA shape set in this packet, so we did not check individual source IDs, the ice-field boundary, or neighboring-feature completeness from its polygons. No open reuse license for the linked shape file was located on the inventory page; use its official download/restoration route and inspect the package terms before retaining or redistributing it.

Argentina's IANIGLA material is organized by watershed/subwatershed and individual glacier or periglacial landform. The 2018 official map for the Ríos de las Vueltas and Túnel subbasins covers only a portion of Santa Cruz and includes the express legal disclaimer that glacier inclusion in the Hielos Continentales zone does not prejudge pending demarcation. The page describing the 2024 update says Resolution 142/2024 published the first updated inventory results for 22 subbasins in the Desert Andes provinces, not this southern region. Thus the reviewed official sources offer different levels and territorial coverage: Natural Earth's single 1:10m map unit, Chile's 2022 individual-glacier inventory, and Argentina's watershed-organized inventory with local published 2018 material. They do not supply a common, current, cross-border source vintage from which to verify the Atlas outline or full neighboring coverage.

The useful adjacent physical granularity is one ice field containing numerous outlet glaciers and glacier bodies. The Atlas's single-child province tier duplicates the feature's name and is not supported as an administrative tier by these source descriptions. The evidence supports engineering review of that tier and role annotation while preserving `country-SPI`; it does not decide which replacement hierarchy tier the repository should use.

## Territorial meaning and boundary evidence

The bilateral 1998 agreement describes the boundary route from Monte Fitz Roy to Cerro Daudet through listed vertices and says the annexed charts form part of the agreement. It is boundary evidence, not a polygon definition for the ice field. The 1996 additional protocol refers demarcation to the Argentina–Chile Joint Boundary Commission after ratification.

Argentina's Foreign Ministry stated in 2018 that its glacier-inventory representation in Hielos Continentales used Argentine official cartography that predated the 1998 agreement and that inclusion did not prejudge pending demarcation. Chile's Foreign Ministry likewise said in 2018 that the inventory used pre-agreement cartography, was not the basis for joint work, and described Section A as fully determined/georeferenced while Section B still required tracing and common cartography. These are primary statements of each government's position and the inventory's limitations. We found no official source specific to the Fitz Roy–Daudet section after 2018 in this review; the 2018 status must not be treated as an up-to-date operational status.

No political parent is inferred. Neither the ice-field boundary nor a glacier inventory is a sovereign-country boundary. The only defensible territorial status in the dated Natural Earth candidate is its explicit indeterminate/disputed map-unit note, subject to the source's cartographic limitations.

## Outcome and uncertainty

Supported: the Atlas subject has a dated Natural Earth identity candidate; the physical role “ice field” is supported at aggregate physical-feature scale; the Atlas's province-tier semantics are not established by source evidence; official glacier inventory boundaries cannot settle sovereignty; and the Atlas original-geometry source hash does not match the dated candidate geometry hash.

Unresolved: exact Natural Earth release/source bytes used for the Atlas original geometry, lawful source restoration matching the stored original hash, date and method of the Atlas outline, full current DGA and IANIGLA source polygons and terms, current status of all treaty-section demarcation, and the repository's proper hierarchy tier for physical features. No core correction is established by this packet.

No geometry, stable IDs, release pins, historical records, or production data were modified.

# Georgia county coastal-water and invalid-reference follow-up

**Issue:** [#980](https://github.com/ChengshuLi/WorldAtlas/issues/980), parent [#428](https://github.com/ChengshuLi/WorldAtlas/issues/428)
**Research/retrieval date:** 2026-10-05 UTC
**Baseline:** `c42f4b7465964245ecbcd8eed4961eb76af3106b` (current `origin/main` used for reproduction after upstream advances from the reserved `8a6a74d194bcde786c03b9acfa4c3b3a92ffc75e` through `f81f77eae61c9e537e7f160fef85b65925359c70`; all 14 issue evidence-quality pins remained byte-identical after the later unrelated #981 source-lineage packet was merged)
**Scope:** the exact eight `gb:USA:ADM2` IDs in `scope.json`; no other county or geography edited.

## Finding

The five coastal comparison flags are predominantly consistent with a source-convention difference in how much Census TIGERweb polygon includes water. The original Atlas geometries are valid, stable and closely match the retained 2018 GeoBoundaries polygons; the five Census polygons are also valid. In an equal-area comparison, Atlas-to-Census IoU stays roughly 0.77–0.88 across 2018, 2025 and the 2026 current TIGERweb layer. The extra area in the Census polygons is hundreds of square kilometres and corresponds to roughly 66–77% of each 2026 `AREAWATER` attribute. TIGERweb's area attributes and polygon difference are not a strict accounting identity, so this supports a water-extent explanation but does not prove the exact cause or settle the legal coastal boundary, island completeness, or whether Atlas should encode water.

The three inland Census references (Schley, Pike, Terrell) are self-intersecting in the original 2018, 2025 and 2026 TIGERweb bytes at the same respective coordinates. Each Atlas geometry is valid. The defects therefore belong to the Census comparison reference; they do not establish Atlas errors. Temporary `make_valid` clones were used only to compute repeatable IoU triage. No retained source geometry was repaired or rewritten. The repaired-reference IoUs are 0.982 for Schley, 0.982 for Pike and 0.989 for Terrell; these numbers cannot certify correctness.

No geometry correction is supported by this packet. **Engineering handoff:** keep the five coastal rows and three comparator-invalid rows as unresolved source-convention/quality cases in future geometry work; do not turn these measurements into a county correction or release change. If a future correction is proposed, obtain an authoritative county boundary or state/county survey source that states offshore-water and island treatment, and use a corrected/valid source for the three inland cases. The exact legal coastline convention and completeness are unresolved.

## Subject-by-subject evidence

All eight Atlas records remain Georgia `ADM2` county rows under the same Georgia state parent as Census `STATE=13`. The 2026 Census TIGERweb County and Equivalent Entities layer returns each requested GEOID once, with `LSADC=06` (County suffix), `FUNCSTAT=A` (active), and the expected county name. The 2025 Census LSAD list defines code 06 for county or equivalent; the county layer is the county/equivalent tier, not a county-subdivision or place layer. The source crosswalk retains the original GeoBoundaries 2018 shape ID and compares using exact Census GEOIDs. This supports identity, parent, and neighboring-granularity checks only.

| County (GEOID) | 2018 / 2025 / 2026 TIGERweb geometry | Atlas ↔ TIGERweb IoU (2018 / 2025 / 2026) | 2025 ↔ 2026 IoU | Specific finding |
|---|---|---:|---:|---|
| Chatham (13051) | valid / valid / valid | 0.770336 / 0.770336 / 0.770336 | 1.000000 | `AREAWATER` 510.7 km²; Census-minus-Atlas polygon 366.8 km² (71.8% of that attribute). |
| Glynn (13127) | valid / valid / valid | 0.787632 / 0.787637 / 0.787637 | 1.000000 | `AREAWATER` 429.1 km²; Census-minus-Atlas 311.8 km² (72.7%). |
| McIntosh (13191) | valid / valid / valid | 0.834333 / 0.834335 / 0.834335 | 1.000000 | `AREAWATER` 369.2 km²; Census-minus-Atlas 242.0 km² (65.6%). |
| Camden (13039) | valid / valid / valid | 0.864183 / 0.864183 / 0.864183 | 1.000000 | `AREAWATER` 392.7 km²; Census-minus-Atlas 265.3 km² (67.6%). |
| Liberty (13179) | valid / valid / valid | 0.883335 / 0.883319 / 0.883319 | 1.000000 | `AREAWATER` 222.9 km²; Census-minus-Atlas 171.6 km² (77.0%). |
| Schley (13249) | self-intersection / same / same | 0.981945 / 0.981945 / 0.981945* | 1.000000* | All Census vintages self-intersect at `[-84.3632159999735, 32.3976489999987]`; Atlas valid. |
| Pike (13231) | self-intersection / same / same | 0.982323 / 0.982323 / 0.982323* | 1.000000* | All Census vintages self-intersect at `[-84.2986650004244, 32.9996709997893]`; Atlas valid. |
| Terrell (13273) | self-intersection / same / same | 0.988875 / 0.988875 / 0.988875* | 1.000000* | All Census vintages self-intersect at `[-84.3052039999726, 31.6910580002751]`; Atlas valid. |

`*` For rows whose Census input is invalid, equal-area overlap comparisons used only a temporary in-memory `make_valid` clone. The table preserves the original validity finding; it does not imply that Census published valid geometry.

The retained current-layer attributes also preserve the state/county code split (`STATE=13`, `COUNTY=039`, `051`, `127`, `179`, `191`, `231`, `249`, `273`) and names. County names, parent, code, and county-equivalent tier are stable across the compared 2018/2025/2026 records. The Census functional-status value `A` means the county government is active, but says nothing about offshore jurisdiction or shoreline completeness.

## Vintage, boundary meaning, source coverage, and reuse

- **2018:** The inherited #428 evidence retains the exact 2018 Census TIGERweb Georgia/Kentucky county query, its service metadata and retrieval receipt. The source is a statistical county/equivalent comparator; original bytes and hashes remain unchanged in the parent evidence packet.
- **2025:** The inherited #428 evidence retains the exact 2025 Census TIGERweb Georgia/Kentucky county query, metadata and receipt. Census's 2025 TIGER/Line documentation says most county/equivalent boundaries generally reflect boundaries legally in effect January 1, 2025, collected through the Boundary and Annexation Survey. It also says TIGER/Line boundaries are for statistical tabulation, do not decide jurisdiction or ownership, are not legal land descriptions, and may be no more complete than the underlying source documents and their vintage/translation. Its units for entity areas are square metres. Cartographic Boundary Files are simplified small-scale products and are only a visual comparator.
- **2026 current service:** We retained the exact 8-feature layer 82 response and layer metadata on 2026-10-05. Metadata describes “Counties (or statistically equivalent entities); January 1, 2026 vintage.” The response is 873,257 bytes, SHA-256 `c09e62479268b4ee8b986a66768d5dea821b4e667d9d446a78d5304076c2e717`; metadata is 7,489 bytes, SHA-256 `56df6e7d6cff8fe1e082bbdc10109cc2c7c22a134f5dfca1899f93d9bd98337d`. This is the current TIGERweb service response, not a legal boundary survey. Census identifies itself as source. Census federal data are reusable with source citation; the retained 2025 documentation also requests a visible statistical-use/no-warranty disclaimer when repackaging TIGER/Line material.
- **Boundary-change notes:** Original Georgia files covering 2011–2013, 2014–2020, and each year 2021–2025 are retained and hashed. None has a change record naming any of the eight counties as an entity. The 2014–2020 file does record 2020 Census CDP placement for Jekyll Island in Glynn County and Crescent/Eulonia in McIntosh County, but those are subcounty statistical placements, not legal offshore boundary descriptions. Census describes this change-note collection as selected changes, not exhaustive, and cautions that effective/submittal dates do not reliably identify the first yearly product reflecting a change. Absence of a county change record is not proof that a boundary or shoreline did not change.
- **Territorial meaning:** “County and Equivalent Entity” is Census's statistical layer label; LSADC 06 corroborates the county suffix/tier. The source and Atlas do not settle what water, marsh, tidal flats, submerged lands, or every barrier/island component a legal Georgia county comprises. No state/county boundary description or cadastral survey dispositive of those coastal areas was found in this bounded review. This is the principal unresolved issue.
- **Source vintage and granularity:** The Atlas source in #428 is a GeoBoundaries USA ADM2 extract labelled Counties, reference year 2018; its original national source, metadata, restoration receipt, and the source's public-domain declaration remain in the read-only parent packet. It is not independent legal boundary authority. The eight source IDs join one-to-one to eight 2026 Census county records. No unit is aggregated or split by this follow-up.
- **Completeness and licensing:** Census change notes and TIGER/Line documentation both state important limits on completeness; the service polygon, county counts, and valid geometry alone cannot show every offshore component. The parent packet's restoration instructions and source hashes for GeoBoundaries remain applicable. The direct 2026 Census source is retained as exact raw response bytes; the Census technical documentation and official change-note page are also retained with retrieval sidecars. The four Georgia county-law source URLs and exact response hashes with restoration instructions are retained under `source/georgia-law/`; the short CC0 statutory excerpts, transcription status, and reuse limits are explicit. Source-specific licenses and limitations are in `evidence-quality.json`.

## Reproduction and controls

Run from the repository root with Python 3.12 and the exact versions in `requirements.txt`:

```sh
python3.12 -m venv /tmp/worldatlas-geo980
/tmp/worldatlas-geo980/bin/python -m pip install -r data/regional-review/regional-review-528e53393a4376b4/source/reproduction-requirements.txt
/tmp/worldatlas-geo980/bin/python data/regional-review/coastal-reference-check-428/reproduce.py
node data/regional-review/coastal-reference-check-428/source/fetch-eight.mjs
node data/regional-review/coastal-reference-check-428/source/fetch-change-notes.mjs
node data/regional-review/coastal-reference-check-428/source/fetch-authority.mjs
node scripts/evidence-quality.mjs data/regional-review/coastal-reference-check-428/evidence-quality.json
```

Network commands are for recreating receipts in an empty output location; retained original files are immutable and the fetch scripts use exclusive creation. Geometry reproduction uses EPSG:6933 equal-area overlay, longitude/latitude GeoJSON inputs, and the same temporary-repair-only policy as #428. The shared helper `worldatlas-evidence-geometry-v1` longitude/latitude control is executed and recorded. The raw Census source files are never rewritten. Results are in `runs/eight-county-comparison.json`; hashes, source records, exact baseline pins, and issue subjects are bound by `evidence-quality.json`. Structural checks are not geographic certification.

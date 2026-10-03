# Southern Indian Ocean Islands, review packet #439

Review-only evidence for the four exact issue subjects, based on published v5/current main commit `ff171e1dd1998684d9b3549943d5725817a7aef4`. The packet makes no hierarchy, geometry, canonical-grid, schema, certificate, claim or live-data changes. Its entire issue scope is accounted for in `assessment.json`, including source-qualified dispositions, all complete parent chains (`baseline-extract.json`), singleton area/province repetition, current land components, settlement evidence, omitted-island leads, cross-region routing concern and unresolved source/tier questions. Scope IDs and actual issue acceptance metadata are preserved in `issue-metadata.json`.

## Primary outcome

- Crozet, Kerguelen and Heard/McDonald have concrete completeness concerns. TAAF inventories five named Crozet islands/groups and Grande Terre plus >300 Kerguelen satellites; present Natural Earth-derived components and reported areas do not establish complete inventories. Australian Antarctic sources distinguish Heard, McDonald and minor rocks while the existing Natural Earth footprint is Heard-only. The GSHHG scan finds many candidates but is only a screen; none is silently promoted to authoritative island identity.
- Amsterdam–Saint-Paul is supported as a deliberate two-island physical group (~85 km apart). The remaining tiny shoreline record and exact source-to-island crosswalk remain unresolved. TAAF’s station population is a research-station fact, not proof of a conventional settlement hierarchy.
- Four matching singleton province wrappers and four singleton area wrappers repeat their children. Natural Earth’s admin-1 feature class does not demonstrate separate province and area semantics. Leave identity-preserving tier treatment to engineering after source evidence and policy review.
- Marion and Prince Edward are named by TAAF but absent from the current part scan and outside current envelopes. Their cross-region route is deliberately not decided here; coordinated follow-up #636 lists affected neighboring regions.
- Source restoration/crosswalk follow-up #635 handles named islands and omitted-land candidates for Crozet, Kerguelen and HMD. Both follow-ups are open without `status:ready` pending review.

## Sources, dates, licenses, bytes

All pages below were retrieved 2026-10-03 UTC; the unchanged published URLs are restoration instructions. HTML pages lacking a verified reuse license were not copied into the repository; only facts, citation, retrieval date and content hash are recorded here. UNESCO page text is CC BY-SA IGO 3.0 and is attributed by title/URL. Natural Earth files are Public Domain. GSHHG 2.3.7 distributed release states GNU LGPL 3.0. TAAF and Australian Antarctic Program page-level reuse licenses were not identified; no page bytes are redistributed.

| Source | Source date / role | License | Captured bytes / SHA-256 |
|---|---|---|---|
| TAAF, Les îles australes, <https://taaf.fr/collectivites/presentation-des-territoires/les-iles-australes/> | modified 2025-02-19; fetched 2026-10-03; official TAAF district/island narrative | Page-level reuse license not identified; citation/hash only | 149,490 / `87d0d46a34cd487b084373e12595bb0f80e542be805c76b228475fc02813158f` |
| UNESCO, French Austral Lands and Seas, <https://whc.unesco.org/en/list/1603/> | inscribed 2019; fetched 2026-10-03 | CC BY-SA IGO 3.0 | 172,003 / `ce93a09ebdb235d899b290ee58f52e576ff62b7f2f49b497d5c58a2b3f8ca144` |
| Australian Antarctic Program, Territory of Heard Island and McDonald Islands, <https://www.antarctica.gov.au/about-antarctica/australia-in-antarctica/the-territory-of-heard-island-and-mcdonald-islands/> | metadata modified 2026-06-26; fetched 2026-10-03 | Page-level reuse license not identified; citation/hash only | 59,202 / `af0b72d6f2e5b0dde51e2a08bd249d6a55470ee54d8d4fbbb720be62822a7349` |
| Australian Antarctic Program, Heard Island operations page, <https://www.antarctica.gov.au/antarctic-operations/stations-and-field-locations/heard-island/> | modified 2026-09-28; fetched 2026-10-03 | Page-level reuse license not identified; citation/hash only | 71,264 / `8b59bb3bedd1bf7be279c482008158e0c26c76ffb5a90faab293ee47857ada42` |
| UNESCO, Heard and McDonald Islands, <https://whc.unesco.org/en/list/577/> | inscribed 1997; fetched 2026-10-03 | CC BY-SA IGO 3.0 | 170,142 / `3fa57968c1c4b27505c57173ac2095f2c1ae067d50bef307b33e9f0ae60baf07` |
| Australian Antarctic Division, HIMI A4 map, <https://www.antarctica.gov.au/site/assets/files/116632/heard_and_mcdonald_islands_region_a4_16159.pdf> | retrieved 2026-10-03; source extent locator only | Reuse license not identified; not retained | 2,799,761 / `5edc9e97b5ebaa4eeb4964fc9860d12bba4dddf388fdc2e59a6911dfacba32c1` |

### Natural Earth source bytes

Natural Earth 10m cultural vectors `ne_10m_admin_1_states_provinces`, release v5.1.1, source repository commit `ca96624a56bd078437bca8184e78163e5039ad19` (2022-06-02), Public Domain. Original feature attributes, geometry hashes, exact source records and file hashes are preserved in `natural-earth-source.json`. Restore from that commit/file name from Natural Earth’s public repository or official download. Source components:

| File | Bytes | SHA-256 |
|---|---:|---|
| `.shp` | 20,998,780 | `c6f5c8b4b1320d9417033762419c6df1eb423989cd880fba78ea0b1e3522cbe4` |
| `.dbf` | 15,161,514 | `7b3244333680d6aec58cc49bde9484177a0baa44c974ec9d371a8f7f1cdb5359` |
| `.shx` | 36,868 | `37a9e2bc79ed31d3bdea3cb62d928f77281a1c88d645cd33430231c75dbcf350` |
| `.prj` | 145 | `a02a27b1d1982c8516d83398e85a3c8b1aef1713c13ef4d84d7bde17430c07c4` |
| `.cpg` | 5 | `3ad3031f5503a4404af825262ee8232cc04d4ea6683d42c5dd0a2f2a27ac9824` |
| `VERSION.txt` | 6 | `f9893302cd3158f3b5aea394dcd2a91574869e9e6ff69e9235b10a3bf8c983fb` |

Natural Earth attributes identify Admin-1 references and owner codes; they do not prove legal maritime extents or natural island inventories.

### GSHHG screening source

GSHHG/GSHHS high-resolution level-1 shapefile, release 2.3.7, distributed at <https://www.soest.hawaii.edu/pwessel/gshhg/> and archive <https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-2.3.7.zip>, LGPL 3.0. Archive bytes were recovered from a prior local source cache and not retained in this packet. Restoration: download the named release archive, extract `GSHHS_shp/f/GSHHS_f_L1.{shp,dbf,shx,prj}`, and verify:

| File | Bytes | SHA-256 |
|---|---:|---|
| `.shp` | 161,320,396 | `121435427911ea80624802e0f352d777eaf6ba6966ca5f07e687650e95329fd9` |
| `.dbf` | 38,125,670 | `5f23e1e441810feddf95b59b222c5bba466635644f928150496f872c1aaaf742` |
| `.shx` | 1,438,796 | `9eeb611d9f7a8de8e647e39130791f96059e3b83a29fc4b9c6b19d1b61c24ac3` |
| `.prj` | 143 | `98aaf3d1c0ecadf1a424a4536de261c3daf4e373697cb86c40c43b989daf52eb` |

The GSHHG release has mixed underlying source lineage. Every L1 polygon intersecting the documented fixed windows was screened in EPSG:6933 against current v5 footprints. The 500m coast tolerance and 1km² reporting threshold are diagnostics only; counts/areas are neither island definitions nor administrative evidence. `shoreline-records.jsonl` retains all 400 rows with record IDs, WGS84 bounds, area, distances and overlap measurements; `shoreline-screen.json` fixes the window/method, input hash, totals, summary and output hash. `build_shoreline_screen.py --check` reproducibly checks the derived outputs when the source path used for the build is provided.

## Methods and reproducibility

- `baseline-extract.json`: exact v5 frozen region membership, location component hashes/bounds, current parent chains and direct projection rows. Built/check with `python build_baseline_extract.py --check` against the current repository release. Baseline files were read only.
- `natural-earth-source.json`: exact source-record attributes and source-to-atlas geometry comparison. Rebuild with `python build_natural_earth_source.py --shapefile /path/to/ne_10m_admin_1_states_provinces.shp`; `--check` verifies derived content. EPSG:6933 area, symmetric difference and Hausdorff metrics are comparisons, not a proposed boundary.
- `shoreline-screen.json` and `shoreline-records.jsonl`: full enumerated candidate screen. `build_shoreline_screen.py` uses PyShp 2.3.1, Shapely 2.1.2 and pyproj 3.7.2 from a private venv; no repository dependency or runtime code was changed. Restore GSHHG as above, then supply the extracted shapefile path and `--check` verifies outputs without rewriting them.
- `grid-representation.json`: a separate Node read-only full pass across all 55 ownership run chunks; validates each compressed and decoded part SHA against `data/canonical-grid/manifest.json`, decodes via `src/ownership-codec.js`, and counts intervals at the four exact owner indexes. This confirms current representation counts, not whether the assigned footprints are geographically complete.
- `neighbor-routing-check.json`: scans current part geometries in the Marion/Prince Edward candidate window, then compares to all frozen v5 region envelopes. Distances are diagnostics for follow-up scope; nearest envelope is not an assignment rule.
- Source material that lacked a verified reuse license is not included; hashes/restoration instructions let another worker recover and recheck it. Measurements and candidate names retain uncertainty rather than forcing source identities.

## Status

All 4 locations, all 4 areas, all 4 provinces and each complete parent chain have individual evidence/status. Issue #439 initial review is not a regional approval and does not unlock historical imports. Correction/source follow-up #635 and coordinated neighbor follow-up #636 remain unready until reviewed and bounded.
- `build_grid_representation.mjs --check` verifies all 55 run chunks against the pinned current grid manifest and requires exact reproducibility of the per-location cell ledger.

The pinned `data/macro-foundation/current-membership-projection.json.gz` file is 5,005,075 compressed bytes and decompresses to 51,660,405 bytes (SHA-256 `e84b2e4f3d8300a2b4e4d36b35a66157ec305f9127e1e6c6403832796b156ddc`). Its decompressed output exceeds the new evidence validator's 32 MiB per-file limit, so the manifest validates its immutable compressed whole-file hash only; it intentionally does not ask the validator to inflate beyond that limit. The compressed hash and the actual v5 projection output generated from it are both separately retained.

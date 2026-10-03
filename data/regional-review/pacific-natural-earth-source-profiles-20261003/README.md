# American Samoa and Wallis–Futuna Natural Earth source profiles

**Issue:** [#616](https://github.com/ChengshuLi/WorldAtlas/issues/616)
**As of:** 2026-10-03
**Baseline:** `f592b3d8b72f40036218803d2c70c733112e4d37` (published partition snapshot)
**Purpose:** source and semantic evidence for engineering review. This packet does not change shared hierarchy, footprints, certificates, canonical grid, or live data. A completed packet is not regional approval or authorization for historical imports.

## Scope and accounting

The issue assigns five American Samoa units and three Wallis–Futuna units, their eight one-to-one province wrappers, and three full geographic-area memberships. `location-assessments.json` accounts for all eight exact IDs, each with its complete five-level parent chain, source code match, role disposition, geometry comparison and limits. `province-assessments.json` accounts for all eight wrappers. `area-assessments.json` enumerates every published member of all three areas, including members outside the eight-location research scope. `verify_packet.py` checks these counts, exact identities and inventory relations.

Known subordinate records are inventoried exhaustively for the inspected source vintages: 16 American Samoa TIGER county-subdivision records (14 statutory counties plus Swains Island; Rose is a county-equivalent group but has no TIGER county-subdivision polygon), all 77 TIGER place records, and 36 INSEE 2018 Wallis/Futuna villages. The Wallis tally is 21 Uvea/Wallis villages, split into Hihifo 5, Hahake 6 and Mua 10; Futuna comprises Alo 9 and Sigave 6. The territorial Assembly also lists these counts. These are statistical/local administrative name inventories, not geocoded exhaustive settlement footprints. The `Malaefoon` / `Mala’efo’ou` name for Mua remains unresolved pending a current local register.

## Natural Earth record restoration and roles

The unmodified source layer is Natural Earth 10m `ne_10m_admin_1_states_provinces` from pinned upstream commit `ca96624a56bd078437bca8184e78163e5039ad19` (Natural Earth 5.1.1, 2022-06-02). Original `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`, version and README files are retained with SHA-256 and byte lengths in `evidence-quality.json`. Natural Earth states that its vector products are public domain. All eight scoped records match exactly by `adm1_code`; all have feature class `Admin-1 states provinces`, `scalerank=10`, and blank `type` and `type_en`. Thus its tier label is a cartographic feature class and cannot alone establish each unit’s legal role. Natural Earth linework is not authoritative legal boundary or title evidence.

American Samoa’s Code §§5.0101–5.0102 says Tutuila and Aunu’u are in Eastern and Western Districts, the three Manu’a islands form Manu’a District, and Swains Island is outside those three districts and administered directly under the Governor. The Census 2020 GARM separately maps the Census county-equivalent areas and cautions that Census designations/boundaries are for collection and tabulation, not jurisdiction or ownership. The fourteen statutory counties match the TIGER 2020 county-subdivision names after punctuation normalization. Rose Island appears as a Census county-equivalent map unit, but not in the fourteen-county list or three districts; its exact current statutory/management role remains unresolved. Rose has no TIGER county-subdivision or place polygon. The AS Code host returned HTTP 403; text was inspected through a proxy and is marked restoration-only and unverified against the local original.

The Natural Earth Swains `region_sub=Tokelau` value is a geographic grouping attribute. It does not override the source’s distinct American Samoa administration or imply sovereignty. Its membership in the published Tokelau-Manihiki geographic area is recorded with every neighbor member in `area-assessments.json`; request coordinated review before any shared footprint proposal. No conflict or boundary change is asserted here.

For Wallis and Futuna, the Territorial Assembly describes current circonscriptions corresponding to customary kingdoms Uvéa, Alo and Sigave, with Wallis’s three districts Hihifo, Hahake and Mua and the listed villages. INSEE 2018 independently provides statistical village/district tables. Its “Districts” worksheet includes Alo/Sigave as statistical rows; that does not establish that they are the same legal tier as the three Wallis districts. Natural Earth’s `WLF-4996` `Uvea` record has an alternate Wallis name; WOE’s `Hahake` value names a child district, not the whole circonscription. Alo’s two disconnected Natural Earth polygons plausibly correspond to Futuna and Alofi but are not a legal demarcation. No authoritative digital boundary geometry was found.

## Physical and footprint screens

`natural-earth-current-geometry-comparison.json` compares the exact Natural Earth records with the published baseline in EPSG:6933. The geometry differences are material—especially the American Samoa shapes—but are only source-screening leads. `american-samoa-census-geometry-comparison.json` explicitly excludes whole-polygon match interpretation because Census polygons include statistical water extents and are not comparable with land-only features.

`screen_gshhg.py` scans all 188,612 GSHHG 2.3.7 records, including all 179,832 level-1 records, with longitude/latitude coordinates. It extracts 99 level-1 records in the two broad windows into `sources/gshhg-local-records.bin.gz`, with compression and uncompressed hashes. Natural Earth shape intersections are Eastern 2, Manu’a 3, Rose 0, Swains 1, Western 1, Sigave 1, Uvea 4 and Alo 3. Counts can include one physical record crossing multiple units. Zero intersection for Rose is not proof of missing land. GSHHG is physical shoreline evidence, not administrative or ownership evidence. Restore the original 92 MB `gshhs_f.b` member from the pinned 2.3.7 archive, verify member hash `af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6`, and run the command listed in the manifest. The LGPL notice is retained.

## Findings and follow-ups

- Eastern, Manu’a and Western roles are supported by the local Code and Census crosswalks for their stated administrative/statistical purposes; boundary completeness remains open.
- Swains is a distinct Governor-administered island under the cited Code and is a Census county-equivalent. Do not interpret a generic Natural Earth Admin-1 class as statutory district or its Tokelau grouping as political status.
- Rose Atoll’s exact current administrative/management status and authoritative land/reef inventory are unresolved. Census inclusion and GSHHG non-detection do not settle either point.
- All three Wallis–Futuna Natural Earth IDs match the current Assembly’s three circonscriptions/customary kingdoms. The statistical and official village rosters agree in counts; one Uvea/Mua spelling is unresolved. Legal polygon boundaries and exhaustive island/lagoon semantics remain unsourced.
- `followups.json` proposes bounded research for Rose, a local Wallis village register/boundary source, and Natural Earth source-history/detached-land validation. It asks for coordinated neighboring review of Swains’ published geographic area relation without claiming an inconsistency.

## Reproduction and source records

From the repository root:

```sh
python3 data/regional-review/pacific-natural-earth-source-profiles-20261003/build_audit.py
python3 data/regional-review/pacific-natural-earth-source-profiles-20261003/screen_gshhg.py /path/to/restored/gshhs_f.b
python3 data/regional-review/pacific-natural-earth-source-profiles-20261003/verify_packet.py
node scripts/evidence-quality.mjs data/regional-review/pacific-natural-earth-source-profiles-20261003/evidence-quality.json
node --test test/evidence-quality.test.mjs
```

`sources.json` records canonical links, vintages, retrieval dates, source roles, licenses, retained-file hashes, restoration instructions and source limits. Natural Earth, Census and INSEE originals are retained. Territorial Assembly and AS Code pages are not retained because use/fidelity terms or access are unresolved; the Legifrance 1961 statute page returned a CAPTCHA/403 and is not used to establish legal conclusions. Do not substitute an access failure for evidence.

This packet documents a source-backed assessment and unresolved follow-ups only. Engineering must integrate accepted findings and validate/publish the complete regional branch before location-attribute research imports become eligible.

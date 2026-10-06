# Texas retained-source and Census record interpretation erratum (2026-10-06)

This packet corrects only source interpretation for the exact 254 Texas county IDs in issue #1138, carried forward from PR #969. It preserves the original #431 packet and its measurements byte-for-byte. `county-interpretation-erratum.jsonl` reproduces a per-subject correction from the frozen 254-row run. It does not recompute geometry, alter IDs/parentage, certify boundary completeness, or approve the Texas region.

## Finding 1: constitutional source is not retained

The old inventory describes `source/authorities/texas-constitution-article-v-section-18.html.gz` as verified Article V §18. The retained gzip decompresses to a 250,874-byte Texas Constitution and Statutes web navigation/code selector, not the provision text. Its recorded request (`?artSec=5&chapter=CN.5&code=CN&tab=2`) and HTTP 200 do not establish that the cited provision was retained. A new GET to the official consolidated constitution PDF URL `https://statutes.capitol.texas.gov/docs/sdocs/thetexasconstitution.pdf` on 2026-10-06 also returned `Content-Type: text/html`, 250,874 bytes, the same navigation shell (SHA-256 `dbfba8a96dc3cd584157ca66aaafdf67e0ed15dd5a0c8a58f3d4bd0f109fc646`). Those bytes are retained as `sources/texas-capitol-navigation-shell.html`; they are explicitly not represented as a PDF or as Article V §18.

**Restoration instructions:** the official Texas site identifies the chapter PDF endpoint as `https://statutes.capitol.texas.gov/Docs/CN/pdf/CN.5.pdf` (Article 5, “Judicial Department”). Retrieve that document from the site's actual PDF download control or a response that returns the source bytes. The direct network request in this work returned HTML instead of PDF, so no Article V text is claimed retained here. Alternatively, retrieve Article V §18 using the Texas Legislature's official Constitution selector at `https://statutes.capitol.texas.gov/` (Code = Texas Constitution, Article = 5, Section = 18; verify the resulting page visibly contains the heading “DIVISION OF COUNTIES INTO PRECINCTS…” and subsection (b)'s commissioners court language). Save response bytes unchanged; require a PDF signature for a PDF response or verify the complete HTML body contains the section; record final URL, retrieval UTC time, status, content type, byte count, SHA-256, displayed/source vintage, and reuse terms. If the official server continues to return the shell, leave the constitutional source unverified and carry this checkpoint forward. Do not treat this citation gap as evidence that the provision or county tier is false.

The old retained Census Texas government guide (Census publication; original PDF SHA-256 `be4e06a13621503702b8c0d5cbbfa664c8f6959434b122d18ff48e48d067a168`) independently states that Texas has 254 functioning county governments, each governed by a Commissioners Court (printed p. 161 in the retained guide). That is the packet's direct source for count and county-government role. Article V §18, once restored, may support the constitutional structure of precincts and commissioners courts; it is not the evidence for a 254-county count or any boundary line. The existing Census source reports no explicit license statement; it is a U.S. government publication and is retained unchanged under the original packet's U.S.-government-work/public-access rationale.

## Finding 2: a county record is not one polygon component

The retained Census 2018 and 2025 TIGERweb Texas query responses each contain 254 county records, all `Polygon` geometries with one polygon component. For these inputs the old per-county statement is supported. The frozen Census 2018 Cartographic Boundary File (CBF) Texas assessment rows also contain 254 county feature records, but their geometries comprise 243 `Polygon` records (one polygon component each) and 11 `MultiPolygon` records. Those 11 have 70 components total: five records with 3 components, one with 4, one with 5, one with 6, two with 7, and one with 26. The complete CBF roster therefore contains 313 polygon components in 254 records. The corrected interpretation is source-specific: one county record is not necessarily one polygon component. It says nothing about omitted islands or whether every offshore or tidal feature is represented. The 2018 CBF is a generalized statistical comparator at 1:500,000. Census TIGER/Line/CBF depictions are statistical products and do not adjudicate legal jurisdiction or property rights.

The JSONL erratum binds each corrected CBF record and component count to its Atlas subject, source ID, parent ID, 2018 and 2025 Census GEOIDs, and the exact historical classification. It uses the original row results without changing the 24 unresolved geometry assessments. Those comparisons remain unresolved and are owned separately by #966; source-hash lineage remains with #967.

## Finding 3: CBF source coordinates are NAD83

The `.prj` member inside the retained 2018 CBF ZIP declares `GCS_North_American_1983`, datum `D_North_American_1983`, GRS 1980 ellipsoid, geographic angular coordinates in degrees. The GeoJSON inputs have different source declarations and must not be used to relabel this Shapefile CRS:

* GeoBoundaries ADM2 explicitly declares `urn:ogc:def:crs:OGC:1.3:CRS84` in its GeoJSON `crs` member (longitude/latitude axis order on WGS 84).
* The retained 2018 and 2025 Census TIGERweb query URLs explicitly request `outSR=4326`; those query response coordinates are WGS 84 longitude/latitude. The respective service layer metadata reports native/latest spatial reference 102100/3857 for service display. Do not confuse the service layer's native projection with the explicitly requested query response CRS.
* The 2018 CBF Shapefile coordinates are NAD83 as declared by its `.prj`, not WGS 84.
* The Texas government guide and constitutional text are not coordinate datasets.

The old script read CBF coordinates without CRS metadata and sent them through the same EPSG:4326 to EPSG:6933 transform used for longitude/latitude GeoJSON; its “WGS84” description is therefore inaccurate for CBF. This is an undocumented NAD83-as-WGS84 coordinate approximation (coordinates treated as if WGS 84); the old packet records no explicit datum transformation. The projection destination is WGS 84 / NSIDC EASE-Grid 2.0 Global (EPSG:6933). No datum-operation accuracy was stated, no coordinate displacement was calculated here, and no numerical error or changed classification is claimed. No new geometry metrics were produced, so no approximation has been adopted for fresh measurements.

## Scope, authority, and neighboring granularity

The 254 IDs remain the county-level administrative/government units under the Texas state unit. The retained Census guide distinguishes Census statistical county subdivisions from county governments; a statistical subdivision must not be promoted to another governmental tier. Census TIGER county records and the 2018 CBF are statistical boundary representations, while official legal authorities define governmental roles. Parentage and geometry remain as they were at the pinned baseline; no legal jurisdiction or line is inferred from a statistical feature.

## Reproduction and controls

From the repository root run:

```sh
python3 data/regional-review/texas-source-interpretation-followup-431/reproduce.py
```

The script checks that the issue's sorted subject list exactly equals the 254 historical county rows, tallies geometry records/components, reads the ZIP `.prj` without extracting or altering the source archive, and writes the exact per-subject erratum plus a compact summary. It fails closed if the roster or expected observed counts change. Run it twice and compare both outputs byte-for-byte. A positive control is the observed 254 records/313 components and exact component distribution. A negative control is the invalid one-record/one-component assertion: it must fail because 11 rows are MultiPolygon and the component total exceeds the record count. No geometric overlay or legal-boundary conclusion is a control in this packet.

## Unresolved work

1. Restore and hash actual Article V §18 text by the instructions above. Until then, that constitutional citation remains unverified.
2. Resolve the separate 24 geometry assessments and state outline under #966 with suitable dated authoritative geometry and method.
3. Resolve source-hash lineage under #967. This erratum makes no source-catalog or source-ID mutation.
4. No global scan, island completeness analysis, or numeric NAD83/WGS84 displacement analysis was conducted. Keep these limits attached to any downstream use.

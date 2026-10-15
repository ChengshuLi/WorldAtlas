# Primary named-island correspondence for the twenty centres

**Two actual NGA GeoNames island records identify the two depicted locations:** northern **Hòn Câu**, with recorded variant **Hon Ho**; southern **Hòn Dung**, with recorded variant **Hon Dun**. These are primary gazetteer name-coordinate facts, not names guessed from image appearance. Vietnamese official documentary context is consistent with these leads, while an exact historical ADM2 component/legal crosswalk remains unproved.

## Actual authoritative gazetteer records

The public [NGA geographic-name application](https://geonames.nga.mil/geonames/GeographicNamesSearch/) advertises its `RESEARCH/GIS_OUTPUT/MapServer/0` GeoNames service in its actual configuration. I obtained that configuration, its field schema, then one attribute-only query for latitude 12.25–12.30 and longitude 109.34–109.39, with `returnGeometry=false`, maximum 50 records and a 256 KiB response cap. It returned seven name rows representing the following two unique features, all with designation `ISL`, country `VNM` and ADM1 `VN-34`:

| Depicted body | NGA UFI | Literal main name / UNI | Recorded coordinate | Literal variant names |
| --- | ---: | --- | --- | --- |
|Smaller northeastern island, labels 1–6|−3710100|Hòn Câu / −4930808|12.282581 N, 109.369454 E|Hon Ho / UNI −4937987|
|Larger southwestern island, labels 7–20|−3713869|Hòn Dung / −4935940|12.271175 N, 109.360678 E|Hon Dun, Hon Yen, Île Pyramide, Île Pyrmide|

The northern gazetteer coordinate lies between the retained latitude rows 122068/122069 and longitude columns 210729/210730. The southern coordinate lies between rows 122077/122078 and columns 210723/210724. This scalar ordering places the authoritative name locations among the respective existing six-centre and fourteen-centre clusters. Combined with the already viewed dated image and existing overlay, it supplies a concrete source-specific correspondence to the depicted northern/southern island bodies. No new transformation, polygon containment, raster sampling or geometry algorithm was run.

The records' `nt` codes are retained literally (`N` for Hòn Câu/Hòn Dung; `V` for variants); I do not invent a legal meaning for those codes. `efctv_dt` and source notes are null. Name/feature edit timestamps are not 2020 sensing dates or Vietnamese administrative effective dates. The gazetteer has ADM1 but no ADM2/ward field in the returned schema, and it supplies point name locations rather than island boundaries.

Actual response: [`nga-nhatrang-island-name-records.json`](nga-nhatrang-island-name-records.json), 5,100 bytes, SHA256 `7ce9d0c93084a70f2fa0872fdd1f66eaffcadf132a9c97a5ad53460bc86fcc85`. [`nga-nhatrang-island-name-observation.json`](nga-nhatrang-island-name-observation.json) preserves the exact public query, retrieval time and successful HTTP 200 receipt. The app/schema responses and observations are retained beside it. This was a coordinate-attribute lookup with no returned geometry, not a fresh spatial predicate or country inventory.

## Vietnamese primary documentary correspondence and its limit

The provincial tourism portal's [“Giới thiệu tổng quan Nha Trang”](https://nhatrang-travel.com/gioi-thieu/don-vi-hanh-chinh/gioi-thieu-tong-quan-nha-trang.html), displaying publication **3 July 2020**, lists **Hòn Hố and Hòn Đụn** among Nha Trang bay's islands. Its administrative history attributes **444-BNV/HCĐP/26.X, 3 September 1974**, to attaching Hòn Một, Hòn Cậu, Hòn Đụn, Hòn Chóp Vung and Hòn Đỏ to **Vĩnh Hải ward, Nha Trang**. It attributes its text to the [municipal history page](https://nhatrang.khanhhoa.gov.vn/vi/gioi-thieu/lich-su-hinh-thanh); that exact municipal URL was inaccessible through the web reader in this pass. The decree itself was not obtained.

This is a specific named administrative-history object to reconcile, rather than another generic map: **the original 1974 decree and any successor ward-boundary schedule/map for its named island components**. The article gives no coordinates. Its Hòn Cậu/Hòn Đụn spellings must not silently become the gazetteer's Hòn Câu/Hòn Dung, nor does a recorded historical attachment prove unchanged 2020 ward membership. The gazetteer's Hon Ho/Hon Dun variants and the provincial Hòn Hố/Hòn Đụn names are useful documentary correspondence leads, not a completed legal identity chain.

## Original-provider boundary

The existing complete nominal-2020 parent result already places all 20 original keys inside Khánh Hòa. The retained parent metadata exposes only `shapeName`, `shapeISO`, `shapeID`, `shapeGroup`, `shapeType`; it does not name its individual island components. Its positive numerical membership therefore cannot supply the missing named-component purpose by itself. Likewise the existing original Nha Trang owner/target and VN51101 linkage remain administrative evidence, distinct from NGA's point-name records.

The reusable new fact is now **named island-location correspondence backed by two specific primary gazetteer feature IDs**, alongside the dated island-surface reading. The remaining exact fact is documentary identity/continuity from those named bodies to the original nominal-2020 Nha Trang member and its component schedule. No claim of intentional district-water inclusion, exact shore, unchanged ward assignment, accepted ownership, hold clearance or repair credit follows. No new imagery, geometry, native or GSHHG operation was performed.

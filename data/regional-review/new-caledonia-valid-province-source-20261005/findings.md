# Findings and engineering handoff — retrieved 2026-10-06

## Scope and source vintage

This packet covers the three IDs in issue #911 only. The immutable baseline is `1f971fef3ed24f4ddc3e3c41caac00db567caea5`; the actual subject container is `data/geography/part-28.json`, pinned at SHA-256 `2aab2f36aeeb651ee8e6cc656e9541ad14e2ced2ea8160e8700ad4dc950c379d`. All three Atlas rows currently identify Natural Earth ADM1 fallback geometry and share geography parent area `framework:area:new-caledonia:42bf5323d811` through their respective province hierarchy nodes. Those hierarchy nodes still have open semantic and boundary review.

I obtained the official BDADMIN-NC geodatabase from the Government of New Caledonia / DITTT download endpoint. The exact 25,287,153-byte response has SHA-256 `66363268e37d5f58c9e49864ea29ef11ecf518f4d24b09b31daa98bcc6c6e59d`, HTTP Last-Modified `2022-05-23T02:26:46Z`, and passed ZIP integrity. Archive members and the OpenFileGDB database timestamps place the source package at 2022-03-02; the Open Data NC lineage also records that date for a group of commune boundary updates. Earlier lineage entries are 2020-01-21, 2019-07-16 and 2017-11-28. The DITTT product read-me identifies a 1:10,000 reference scale and says the province/commune boundaries are positioned according to applicable regulations, with coastal and natural limits revised during BDTOPO-NC updates.

The source is **restoration-only** in this packet because its reuse terms conflict. The ArcGIS item metadata and current DITTT download catalogue claim Open License 2.0. The downloaded archive contains a 2020 read-me specifying CC BY-NC-SA 4.0 and a 2017 terms PDF excluding commercial use; DITTT's database summary from September 2019 also specifies CC BY-NC-SA. The current DITTT product page links a separate Creative Commons document without saying it supersedes the package documents. I did not infer that these terms have been replaced. I removed the downloaded ZIP and all extracted geometry from the packet; `source-acquisition.json` records byte count, exact archive SHA, source chain, document-member hashes and the exact restoration/check instructions. Ask DITTT which release-specific license governs and whether derivative province geometries may be distributed before an engineering import.

## Administrative meaning and neighboring granularity

Organic Law 99-209 Article 1 defines the three provinces through named commune territories: Nord includes 16 listed communes, Sud includes 13, and Îles Loyauté includes Maré, Lifou and Ouvéa. It separately states that Poya is divided between Nord and Sud by decree in Council of State. The named 26 April 1989 decree is the specific Poya split instrument. Its scanned annex was not downloaded or georeferenced here, so the decree title and the law do not independently verify the exact Poya line.

The 2025 population decree reports 33 communes in New Caledonia and province membership as 3 for Îles Loyauté, 16 plus the northern part of Poya for Nord, and 13 plus the southern part for Sud. This corroborates the current administrative tier/count and the Poya split label only; counts are not boundary evidence.

The 2022 BDADMIN-NC geodatabase has a `PROVINCES` layer with exactly `PROVINCE_NORD`, `PROVINCE_SUD` and `PROVINCE_DES_ILES`, plus a finer `COMMUNES` layer with 33 names matching the legal municipality set. The province feature identities match the exact three Atlas subjects. All three province geometries inspected from `PROVINCES` are nonempty valid multipolygons. The DITTT database uses EPSG:3163. Its adjacent commune tier is more detailed than this issue's province subjects; no commune shapes are imported into the packet.

The DITTT CGU also cautions that, absent specific notice, the dataset has not received strict topological structuring or systematic completion and warns against using data above its designed scale. Individual polygon validity therefore does not demonstrate no inter-province overlap/gap, exact commune-to-province fit, or complete offshore/islet representation. Those checks remain engineering/source-owner follow-ups.

## Three-subject geometry review

The preserved GeoReP source is the generalized FeatureServer query recorded in parent packet #454. It requested `maxAllowableOffset=0.00005`, `geometryPrecision=6` and `outSR=4326`; the response declares 2024-10-28 source currency and spans different display scales. All three original feature geometries remain byte-for-byte unchanged and invalid with `Nested shells` reasons. I created a disposable GEOS MakeValid diagnostic clone solely to compare footprints; no clone was saved as candidate geometry.

The BDADMIN-NC `PROVINCES` features are very close to that diagnostic clone. They do not behave like a boundary redraw. In contrast, they differ materially from each current Natural Earth fallback. This suggests the nesting defect is associated with the GeoJSON/serialization path or generalized query, while the underlying official source provides valid geometry. It does not establish that a MakeValid output is legally correct, and does not by itself settle the fallback discrepancy.

| Subject | Source feature | Valid multipart pieces | BDADMIN area (km², local LAEA) | BDADMIN vs Atlas fallback Jaccard | Symmetric difference (km²) | BDADMIN vs GeoReP diagnostic Jaccard | Symmetric difference (km²) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nord (`NCL-559`) | `PROVINCE_NORD` | 822 | 9,419.441 | 0.917411 | 815.686 | 0.999951 | 0.465 |
| Sud (`NCL-1259`) | `PROVINCE_SUD` | 666 | 6,982.832 | 0.911026 | 665.088 | 0.999755 | 1.714 |
| Îles Loyauté (`NCL-1258`) | `PROVINCE_DES_ILES` | 386 | 1,948.606 | 0.819125 | 394.075 | 1.000000 | 0.000038 |

The local-area comparison uses planar polygon overlays after transforming EPSG:3163/WGS84 vertices without densification into WGS84 Lambert azimuthal equal-area (`lat_0=-21.5`, `lon_0=165`). The input edges remain straight coordinate segments; these are diagnostic measurements over a local footprint, not a survey accuracy estimate. Jaccard is intersection/union area. Symmetric difference is the area of the two exclusive footprints. The shared geometry helper separately measured BDADMIN source land area using its WGS84 straight-source-edge ellipsoidal method: Nord 9,419,440,821 m², Sud 6,982,832,520 m², Îles Loyauté 1,948,606,352 m². The two area approaches are different metrics and are not conflated.

The GeoReP diagnostic comparisons are equally revealing: BDADMIN vs MakeValid-clone Jaccard is 0.999951 / 0.999755 / 0.999999981, with symmetric differences 0.465 / 1.714 / 0.000038 km². Thus an official valid version of virtually the same generalized geometry exists, but the higher-detail BDADMIN archive's redistribution terms must be clarified before copying its bytes or derived polygons into the Atlas.

## Subject dispositions

- **NCL-559 Nord — correction needed, source adoption unresolved.** The official 2022 `PROVINCE_NORD` polygon is valid, has 822 multipart pieces, and matches the subject's legal province name. Its large difference from Natural Earth is not explained by any evidence that the public-domain fallback is current legal geometry. Candidate to replace the existing fallback only after the license and topology/completeness questions are answered.
- **NCL-1259 Sud — correction needed, source adoption unresolved.** The official 2022 `PROVINCE_SUD` polygon is valid, has 666 multipart pieces, and matches the subject's legal province name. Its boundary is close to the disposable GeoReP diagnostic but differs substantially from Natural Earth. Candidate to replace the fallback only after license clarification and Poya/commune seam review.
- **NCL-1258 Îles Loyauté — correction needed, source adoption unresolved.** The official `PROVINCE_DES_ILES` polygon is valid, has 386 multipart pieces, and matches the legal Maré/Lifou/Ouvéa province. It is nearly identical to the GeoReP diagnostic, while its overlap with Natural Earth is lower than for the two mainland provinces. Confirm outer-island coverage and source permissions before adoption.

No region or province is certified by this packet. The 1:10,000 official source, individually valid geometries, member counts and overlap scores do not certify boundary completeness, legal accuracy at every segment, parent-area semantics, publication readiness or suitability for the Atlas's overview scale.

## Reproduction and controls

`reproduce.py` verifies the restored archive SHA/size and ZIP CRC before extraction; checks exact province layer identities, the 33-name commune set, source validity, GeoReP source hashes and all three Atlas IDs; runs positive and negative scope controls; and writes `comparison-results.json`. The negative controls swap Nord/Sud source labels and request an absent out-of-scope ID. The original GeoReP inputs are preserved and reported invalid. Temporary exports are hash-checked before `measure-geodesic-area.py` uses `worldatlas-evidence-geometry-v1` (`Shapely 2.1.2`, `GEOS 3.13.1`, `pyproj 3.7.2`, `PROJ 9.5.1`). The extraction/overlay run used `Fiona 1.8.21`, GDAL 3.4.1, `Shapely 2.0.7`, GEOS 3.11.4. Reproduction commands and source limitations are listed in `README.md` and `evidence-quality.json`.

The evidence-quality manifest binds the exact issue scope, current baseline commit, containing geography file, source registry, hierarchy, macro publication envelope, handoff/membership files and retained parent source partitions. Geography approval remains `unapproved`; implementation remains proposed only.

## Bounded engineering handoff

1. Obtain a written, release-specific license clarification from DITTT; until then, restore the archive only for authorized research and keep it out of distributable branches.
2. If the license permits, evaluate the three official `PROVINCES` features as the new source bytes for the existing IDs. Keep Natural Earth public-domain bytes and all original GeoReP query partitions and invalidity evidence for lineage.
3. Independently inspect inter-province topology, legal Poya split evidence, province/commune seams and offshore/islet completeness. Choose a representation appropriate to the product scale; do not change IDs or parents as part of this work item.
4. If the licence does not permit use, ask DITTT for a compatible official geometry export or use a permitted valid GeoReP service representation. Do not silently MakeValid the preserved feature or certify the region from this packet.

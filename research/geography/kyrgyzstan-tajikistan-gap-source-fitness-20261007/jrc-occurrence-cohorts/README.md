# JRC Occurrence block-support cohorts

This is a metadata and vector-support supplement to the source-fitness packet. It partitions all 15 original physical-component geometries and all 9 complete administrative contact geometries into bounded JRC Occurrence tile cohorts. It does not classify water pixels or assign a boundary.

## Contract and source

The current #1431 contract SHA-256 is `2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3`. The selected families remain `gap-source-batch:74be953b1fb31c15200742da` (12 components) and `gap-source-batch:65911e15791d12ebb2ccacf5` (3 components), preserving each family’s existing status: cause unknown, physical authority unapproved, source fitness unapproved for all components. The candidate records retain `water_status=unverified` and `administrative_assignment=null`; all 9 contacts remain context only.

Source: JRC Global Surface Water v1.5 Occurrence, aggregate 1984–2024. The [JRC catalogue](https://global-surface-water.appspot.com/download) describes the data as freely available under Copernicus terms with attribution, and says 1984–2021 uses Landsat Collection 1 and 2022–2024 uses Collection 2. JRC documents a spatially variable cross-collection offset, typically subpixel but at or above one nominal 30 m pixel in some WRS-2 path/rows. The [published Occurrence legend](https://data.fao.org/catalog/iso/f1b1d45a-e360-44bd-95a9-d628c468a7f6) is 0=no detected water, 1–100=occurrence percentage, and 255=NoData.

`source-capture.json` binds conditional byte-range responses to the object ETags and Last-Modified values. ETags are validators, not SHA-256 hashes. Each current retained range is only bytes 0–81,327 (81,328 bytes), has HTTP 206 and matching `If-Match`, and is pinned by SHA-256. The four current metadata ranges total 325,312 bytes. Parsing all IFDs shows all metadata arrays end by byte 81,324, while the earliest TIFF image block begins at byte 81,328; the retained current ranges therefore exclude image-block bytes. The full TIFF objects themselves were not downloaded; no pixel blocks occur in these current retained prefixes.

A prior acquisition mistakenly retained 512 KiB prefixes that include small overview-image blocks beginning at byte 81,328. Their original bytes and HTTP acquisition details are preserved in the quarantined recovery at `.cache/kgt-independent-water-source-review-20261007/recovery/previous-512k-prefixes/`; they are excluded from these current inputs and from every calculation here. The four prior known SHA-256 hashes were recovered and verified; the two exploratory tile hashes are recorded in that quarantine manifest. No pixel values were decoded or classified.

## Grid and exact support method

All four TIFFs are 40,000×40,000, single-band unsigned 8-bit, EPSG:4326/WGS84, PixelIsArea, 0.00025° cells, with 512×512 tiled blocks (79×79 blocks). The tiepoint is the west/north corner; the suffix names the north edge. Thus `60E_40N` and `70E_40N` cover 30–40°N, while `60E_50N` and `70E_50N` cover 40–50°N. The complete 15 candidate and 9 contact extents require exactly these four tiles.

`exact-block-intersections.py` maps the complete original source coordinates to exact rational pixel coordinates and computes closed-set intersections between every full Polygon/MultiPolygon (including holes and boundary touches) and the TIFF block squares. It performs no clip, repair, transform, or rewrite. It reads only the complete vector inputs plus IFD metadata arrays; it does not read any raster image block. The full geometry remains in its pinned source file and is referenced in each result.

The union is **256 exact blocks**: 60 in `60E_40N`, 138 in `70E_40N`, 28 in `60E_50N`, and 30 in `70E_50N`. Their `TileByteCounts` sum to **687,297 encoded bytes**. Decoding each touched 512×512 UInt8 block to a full block buffer is bounded by **67,108,864 bytes (64 MiB)** for the unique tile/block union. The 17 candidate-support blocks all occur in the full-contact block union. This is grid overlap only; it is not independent negative/control evidence or shared feature geometry.

## Typed bounded cohorts

`build-bounded-cohorts.py` partitions by subject type (`candidate` or full-feature `contact`) and tile, then greedily packs stable IDs under 64 unique blocks per cohort. Each cohort is bounded at 16 MiB of decoded full-block buffers. Cross-tile subjects appear in every applicable tile cohort while the global identity list remains deduplicated. No geometry is clipped to a tile or cohort.

| Cohort | Full members | Blocks | Encoded bytes | Decoded upper bound |
|---|---:|---:|---:|---:|
| candidate-60E_40N-01 | 5 | 3 | 6,941 | 0.75 MiB |
| contact-60E_40N-01 | 5 | 60 | 94,995 | 15 MiB |
| candidate-70E_40N-01 | 9 | 11 | 55,821 | 2.75 MiB |
| contact-70E_40N-01 | 2 | 50 | 93,225 | 12.5 MiB |
| contact-70E_40N-02 | 2 | 58 | 122,477 | 14.5 MiB |
| contact-70E_40N-03 | 2 | 63 | 248,166 | 15.75 MiB |
| candidate-60E_50N-01 | 1 | 2 | 5,016 | 0.5 MiB |
| contact-60E_50N-01 | 4 | 28 | 146,397 | 7 MiB |
| candidate-70E_50N-01 | 1 | 1 | 599 | 0.25 MiB |
| contact-70E_50N-01 | 3 | 30 | 81,933 | 7.5 MiB |

The 10 cohorts contain 16 candidate tile memberships and 18 contact tile memberships, covering all **15 unique candidate IDs** and **9 unique contact IDs**. Across cohorts, there are 306 unique-block memberships and 50 repeated memberships. The largest cohort is 63 blocks / 15.75 MiB decoded. Its conditional byte-range windows, block indices, full input references and hashes are in `jrc-bounded-cohorts.json`. If each typed cohort were read independently without sharing overlapping blocks, the sum is 855,570 encoded bytes and 80,216,064 decoded bytes; the deduplicated support union remains 687,297 encoded / 67,108,864 decoded bytes.

## Limits

The raster only provides aggregate occurrence frequency, not candidate-date observations or boundary placement. The TIFF tags and product page provide no candidate-level registration or positional accuracy. Pixel-cell spacing is angular, not a square metric grid. Land/water, effective date, authority, lineage/cause, registration accuracy, rights and ownership remain unknown or unapproved. No JRC pixel value was observed; none of the measured block footprints is an administrative-boundary approval.

## Reproduction

From any working directory, run:

```sh
python3 path/to/jrc-occurrence-cohorts/exact-block-intersections.py
python3 path/to/jrc-occurrence-cohorts/build-bounded-cohorts.py
```

Outputs are `jrc-exact-block-intersections.json` and `jrc-bounded-cohorts.json`. The second output binds the SHA-256 of the first. Exact manifest SHA-256: `0526129fd4a61dab4127dd6d675eef8249ba304f8a7926ae89303e70bacced61` (intersection code SHA-256 `7f3a9e9bf7e4d675163d98ce183089ab6ba2242d9ec516e6eef48a6e1d51c959`). Cohort manifest SHA-256: `188f4eaa88f6f6f90cef7acf5a1ca7131ffb6c397a219d2cb732dc9c97f971fe` (cohort builder code SHA-256 `d7d4fe6f87baef141315724c72102cd9b38fa49aab06fe9cc388d0f01441ad88`). Source-capture manifest SHA-256: `3f7884b3baec157112f1d660e6646fdbdc333db46b50c9b61eb85d7a9d4cdeea`.

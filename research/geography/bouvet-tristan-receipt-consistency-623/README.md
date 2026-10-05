# Bouvet–Tristan source and summary receipt (2026-10-04)

This is a superseding, bounded consistency receipt for issue #786. It preserves and does not edit the original `data/regional-review/regional-review-dbe207dead8603ae/` files. The immutable inputs are read from main commit `0c6232db2b2f9531a479f0c752f66c4d12013f3b`; the exact subject features are in `data/geography/part-28.json`. `evidence-quality.json` binds whole-file pins, actual subject-to-file mappings, sources, methods, metrics, controls and changed-file receipts. Reproduce from the repository root using its recorded commands.

## Corrected context counts

The pinned `shoreline-screen.json` declares 17 rows. Recounting the exact JSON bytes gives 17 unique `gshhg_id` values and these context totals. These are nearby screen records, including small offshore features; they do not establish coastline completeness or island-group coverage.

| Context | Records |
| --- | ---: |
| Tristan vicinity | 6 |
| Gough vicinity | 9 |
| Bouvet vicinity | 2 |
| Total source rows | 17 |
| Unique source IDs | 17 |

The superseded README values (5 Tristan, 8 Gough, 2 Bouvet) sum to 15 and conflict with the preserved 17-row inventory. The earlier GSHHG packet says it restored GSHHG 2.3.7 and found the same screen records; this follow-up does not download or re-extract its 149,157,845-byte archive. Its prior archive pin is SHA-256 `8dbbe7e071e77e9e75f2d639239099ebca8d5c16d6a07df8169729d49f15cf41`. Thus the new reproducible count claim is specifically an immutable-JSON recount, while independent archive corroboration remains predecessor evidence.

## Settlement response vintages

The predecessor's claimed restoration value `7a5940df57e7fe521e7714f195385f3eb6901a71e0102b43b571d5fa90ddeee` has 63 hexadecimal characters and is not a SHA-256 digest. It remains recorded as invalid; this packet does not invent a missing character or claim to recover the original response.

A distinct GET of the official [Tristan settlement page](https://www.tristandc.com/settlement.php) on 2026-10-04T23:48:59Z returned HTTP 200 and 15,516 response-body bytes. Its separately measured full SHA-256 is `7a5940df57e7fe521e771f4e195385f3eb6901a71e0102b43b571d5fa90ddeee`. See `source-retrieval.json` for exact metadata and a reproduction command. HTML reuse terms were not verified, so response bytes are not committed. This observation is a new, mutable page vintage and does not identify or repair the unavailable historical response.

## Natural Earth source and atlas geometries

All six Natural Earth 5.1.1 Admin-1 sidecars were retrieved from repository commit `ca96624a56bd078437bca8184e78163e5039ad19` (2022-06-02) and retained with exact byte counts and SHA-256 values in `sources/natural-earth-5.1.1/retrieval.json`. Natural Earth states its map data are public domain ([terms](https://www.naturalearthdata.com/about/terms-of-use/)). Its Admin-1 product describes generalized administrative mapping, not a legal boundary register or evidence of WorldAtlas tier purpose ([product description](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/)). The data feature vintage itself is undated.

The generator reads those retained source rows and the exact ancestor-main atlas features. Geometry hashes below are SHA-256 over sorted-key compact JSON geometry objects. Coordinates are WGS84 longitude/latitude. EPSG:6933 measurements transform with longitude-first axis order and `always_xy`; areas are projected planar areas. Shared-helper WGS84 ellipsoidal areas are also retained in `findings.json`. Rounded rows are bound to the numeric ledger in the manifest.

| Subject | Measurement | Value |
| --- | --- | ---: |
| SHN-4865 (Tristan da Cunha) | Natural Earth EPSG:6933 area (km²) | 152.820982 |
| SHN-4865 (Tristan da Cunha) | Atlas EPSG:6933 area (km²) | 151.837677 |
| SHN-4865 (Tristan da Cunha) | Source minus atlas area (km²) | 0.983305 |
| atlas:coverage:BVT+00? (Bouvet Island) | Natural Earth EPSG:6933 area (km²) | 55.209800 |
| atlas:coverage:BVT+00? (Bouvet Island) | Atlas EPSG:6933 area (km²) | 55.209996 |
| atlas:coverage:BVT+00? (Bouvet Island) | Source minus atlas area (km²) | -0.000196 |

| Subject | Natural Earth geometry SHA-256 | Atlas geometry SHA-256 | Equal? |
| --- | --- | --- | --- |
| SHN-4865 | `032f4993babc938401a8cd7992bd3291914c819b09a198a3e5ab40a523f241ea` | `0e388969279a44c0f5d218995e4322328b8aa01cfbb4e9e48d3e4e048cbf648d` | No |
| atlas:coverage:BVT+00? | `ded1296c63e9fba3c51d8b2119246794a2c69cbaa81c18d8e75d184182096e18` | `05b28c1c00f92211ef911cf384f97b7eacddb6c390697fe78c0e13a334d5804b` | No |

The old equality statement is unsupported: the source and atlas geometries differ. This says nothing by itself about whether the atlas generalization is appropriate. No geometry is corrected here. Natural Earth classifies both source rows as Admin-1; that source label does not prove a statutory province or the purpose of the Atlas province/area wrappers.

## Territorial meaning, parent context and open findings

The current six-tier parent chains are reproduced in `vintages/20261004-reviewed-2/findings.json`. Both locations descend through their existing province, area and the Eastern South Atlantic Islands region to the Central and Eastern South Atlantic Islands subcontinent and Africa. This is a structural observation, not approval of the chain's geographic meaning.

The official [Tristan government map group](https://www.tristandc.com/mapgroup.php), [government page](https://www.tristandc.com/government.php), and pages for [Gough](https://www.tristandc.com/gough.php), [Nightingale](https://www.tristandc.com/nightingale.php), and [Inaccessible](https://www.tristandc.com/inaccessible.php) describe island-group and administrative context. The site identifies four main groups (Tristan, Nightingale including Middle and Stoltenhoff, Inaccessible, and Gough); Gough has a separately described meteorological station. Its current [settlement page](https://www.tristandc.com/settlement.php) describes Edinburgh of the Seven Seas as the island's only settlement. These mutable pages are read-only restoration sources; no page HTML is retained because reuse terms were not established. They do not settle the legal boundary or purpose of the Natural Earth ADM1 row.

The current region inventory also includes the separately identified, unowned Inaccessible location `atlas:island:geonames:3370905`; do not edit or copy it. Current regional members contain no Nightingale or Gough location IDs. The Natural Earth Tristan row contains two components corresponding geographically to Tristan and Gough, while its generalized footprint does not prove complete island-group coverage. These gaps remain for broader Tristan source/crosswalk issue #620. Bouvet is a named, disconnected, volcanic island; the [Norsk Polar Institute](https://npolar.no/en/themes/bouvetoya/) reports about 89% ice cover and protected nature-reserve status. That physical description does not resolve whether the singleton Atlas province and area tiers have a useful, sourced purpose; this remains with #621. Source page reuse terms for Norsk Polar Institute HTML were not located, and no page bytes are retained.

The current macro foundation is approved at its recorded release, but publication verification is pending and `ready_for_location_attributes` is false. This receipt does not alter that gate, certify this region, authorize imports or make settlement-absence, boundary-correctness or historical claims.

## Evidence limits and restoration

- The pinned original README, shoreline JSON and containing GeoJSON retain their original bytes and hashes. Only this separate owned evidence directory is added.
- Natural Earth source sidecars are retained; `sources/natural-earth-5.1.1/retrieval.json` records each exact file hash, size, upstream path and immutable commit. Restore with `git fetch https://github.com/nvkelso/natural-earth-vector.git ca96624a56bd078437bca8184e78163e5039ad19`, then `git show ca96624a56bd078437bca8184e78163e5039ad19:10m_cultural/<sidecar>` for each listed file.
- The GSHHG archive was not re-extracted in this follow-up; use the predecessor packet's restoration instructions and verify its recorded 149,157,845-byte archive hash before reproducing that earlier source screen.
- Re-fetch the Tristan and Norsk Polar Institute canonical URLs to inspect current pages. The TDC settlement observation can be rechecked with the exact command in `source-retrieval.json`; later response bytes can change.
- Positive and negative controls cover wrong totals, duplicate IDs, missing contexts, count prose disagreement, coordinate-axis order and false source/atlas equality. Deterministic two-run reproduction is recorded. These checks validate this bounded computation; they do not independently prove all source facts.
- Original NPI HTML bytes were unavailable in predecessor research. Territorial purpose, lawful boundary coverage, neighboring island completeness, GSHHG source re-extraction and regional approval remain unresolved.

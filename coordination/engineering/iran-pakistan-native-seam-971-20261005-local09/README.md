# Saravan–Panjgur native border comparison

Refs #971. This is the source-comparison part of the joint repair investigation. The issue remains open.

The retained example point is absent from both original geoBoundaries country datasets. The full-component scan identifies only Saravan and Panjgur as native bounding-box candidates; their valid source shapes cover smaller portions of the stripe. Most of the diagnostic stripe therefore predates atlas rasterization. This establishes source coverage disagreement, while the geographic cause, authority, physical-water status and permitted correction remain unresolved.

The current OSM Panjgur relation covers the example point and most of the component. Its exact outer ways are assembled using original node identities, recording every coordinate member version/date. Subareas are retained as nongeometry members, never expanded into the district border. This is a newer candidate reference, not a replacement approved against the older Iran source.

## Full-component measurements

All values are WGS84 straight-source-edge areas in square metres. They measure intersection geometry, not confirmed dry land or administrative ownership. No positive-area cutoff is used.

| Diagnostic geometry | Area (m²) |
| --- | ---: |
| Full retained component | 17527564.637314 |
| Covered only by original IRN member | 264623.962684 |
| Covered only by original PAK member | 5157.294875 |
| Covered by both original members | 0.000000 |
| Covered by neither original member | 17257783.379757 |
| Covered by current OSM Panjgur candidate | 17262940.673516 |
| Outside current OSM Panjgur candidate | 264623.963795 |
| Outside OSM Panjgur plus older IRN member | 0.055626 |
| Overlap of OSM Panjgur and older IRN member | 0.054515 |

`results-v2/report.json` retains every partition geometry, the original full-component properties/fragment bindings, exact overlay coverage/excess remnants and source identity/hash records. The exact reconstructed partition union is not topologically identical to the original component: lower-dimensional/numerical remnants remain explicit even when their measured area is zero. The first comparison in `results-v1/` is preserved separately.

## Original sources and licence

Full original IRN and PAK ADM2 GeoJSONs are retained byte-for-byte from geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d`; their hashes match upstream Git LFS pointers. Original metadata states IRN boundary year 2017 (OpenStreetMap/Wambacher, ODbL 1.0) and PAK boundary year 2019 (GeoBoundaries/Wikipedia, Public Domain). Preserve the provider citation/use notices (derivative work/code attribution CC BY 4.0), country-specific terms and upstream attribution. Source build/update dates are not boundary observation dates.

Current OpenStreetMap originals retain ODbL 1.0/OpenStreetMap and contributors attribution. The point-area response and full relation response have separate original retrieval/date receipts. Overpass `osm_base` and `areas_base` dates differ. The direct API snapshot records every coordinate member timestamp; one relation timestamp cannot date all source coordinates. Earlier failed Overpass retrievals remain failed receipts, not retained original geometry.

## Reproduce offline

Install the committed pinned Python requirements (the comparison itself uses NumPy, Shapely and pyproj). Fetch `refs/pull/985/head` to restore input bootstrap `a10c45aceb27be8d35ec06419c25c5d7cbfa2632` if it is absent locally. All original sources are committed; reproduction needs no provider/browser/live connection.

Use a fresh output filename. Run the following from the repository root, replacing the output destination only:

```sh
python coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py --repo . --commit a10c45aceb27be8d35ec06419c25c5d7cbfa2632 --registry '{"path":"coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/inputs.json","bytes":10424,"sha256":"bae7688eea26ef7e96f129526ad1ee5b3a401d25bcf8dbb8a01a606fb2056247","hash_kind":"file-bytes"}' --registry-sha256 bae7688eea26ef7e96f129526ad1ee5b3a401d25bcf8dbb8a01a606fb2056247 --out .cache/your-unused-native-border-report.json
python coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/controls.py
python test/evidence-geography.py
```

Two full runs were byte-identical. Actual CLI controls reject a wrong registry hash and an existing output; an altered original source hash is refused before geometry work. Synthetic controls cover exact way orientation/closure, missing/duplicate geometry members, invalid coordinates/polygons, holes, bilateral gaps, overlapping sources and tiny positive geometry.

## Remaining repair work

Obtain a defensible mutually consistent source/date/identity basis for both neighbors and adjudicate the full-component physical-water/registration uncertainty. Preserve current/native originals, tiny uncovered/overlap residuals, stable identities and the original release. Any later core-footprint correction requires reviewed affected-neighbor regression and explicit release/certificate/content revalidation. None has been installed by this packet.

Existing source-review scopes #121 and #115 remain unchanged. Their frozen exact membership evidence comes from #970; source comparison does not approve either regional branch. No publisher chat, deployment, production database/provider changes or automatic proximity assignment occurs.

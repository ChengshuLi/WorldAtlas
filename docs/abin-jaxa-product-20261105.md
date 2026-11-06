# Abin: JAXA product drainage divide

The approved research route uses the longest connected interface between the two named-drainage seed groups in the N044E038 AW3D30 v4.1 product. The 63,096 m replacement joins the existing source boundary at its actual intersections near 38.317778 E, 44.595833 N and 38.653889 E, 44.504659 N. The cut and resulting whole boundary are simple. The combined Anapa and Abin geometry is selected in Neon research revision `v2-land-mainland-boundary-draft-1` and has been read back.

The AW3D30 product mask value 48 (0x30) denotes valid Copernicus GLO-30-filled elevations, according to JAXA's v4.1 product description. The earlier stricter screen excluded all nonzero mask values and consequently had two false gaps. The model now includes mask 48 plus unfilled mask 0 pixels with positive stacking count. This does not imply Copernicus is independent evidence where it is used to fill AW3D30.

At 200 m intervals, 100 m offsets, and a 100 m local-direction window, all 316 stations have the expected 1/2 JAXA-product basin labels. This is a consistency test against the model used to construct the line, not validation by a ground survey. It intersects none of 952 complete mapped OSM river/stream ways in the checked extract. Both the data and the waterways have finite resolution and coverage. Endpoint joins are intersections rather than proofs of the divide beyond the changed stretch.

Source pins and R2 objects:

- `sources/jaxa/alos-world-3d-30m/v4.1/original/N044E038.zip` SHA-256 `fed086debcce49e07ac9296d935eff0e1b2b6bde000a87ff19fd16585fe7ab73`.
- `sources/osm/caucasus-abin/20261105/broad-ada68ef47c11.osm` SHA-256 `ada68ef47c11ad4cfbdcd36cf369ca96e91072cfd406f2d28f2f16349dc4b72d`.
- `sources/osm/caucasus-abin/20261105/further-7152fe44f0da.osm` SHA-256 `7152fe44f0dae950965c06777e206a396f3b7938ee1fdc4d33dc0f96757e0033`.
- `sources/osm/caucasus-abin/20261105/ubin-2e2bbebd62e0.zip` SHA-256 `2e2bbebd62e0c5bbca7c2ca9ebc00bb263dec148d26c922db5cdc619764be216`.
- `sources/osm/caucasus-abin/20261105/khabl-42864b4776ee.zip` SHA-256 `42864b4776eecd500c639c72028ff2eec2b16f9454215d1c9a42acc194060e50`.

The four OSM objects were retrieved from R2 and checked against these SHA-256 values, and `west_abin_merge_raw_osm.py` reconstructed the exact combined OSM input hash `430a7eb2165a500c165ec752a7681ee81292b2d6ea0c6efdaf0292427e4dc1f9`. The JAXA archive was read back and verified as well.

The scripts `west_stream_seeded_jaxa_filled_abin.py`, `abin_filled_components.py` and `abin_jaxa_full_product_splice.py` reproduce the experimental computation using the pinned inputs and original selected line, in that order. `abin_jaxa_product_summary.py` and `abin_jaxa_product_streams.py` perform the screens described above. They are research scripts, not a fully integrated production pipeline. The Anapa closure and region were updated with the selected geometry and screened against the pinned historical physical mask. The source gate must support the approved v2 recipe and closure proofs must be regenerated against the physical generation used by the map. No map was rebuilt.

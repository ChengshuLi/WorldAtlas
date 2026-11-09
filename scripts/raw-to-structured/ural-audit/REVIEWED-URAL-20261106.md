# V8 Ural boundary

The editable `v8-mainland` revision in Neon holds the selected 46,430-point
boundary `ural_kara_coast_to_caspian`. Its construction recipe is
`v8-ural-construction-recipe` version `v8.0-1e485322c45a` in
`atlas.structured_documents`. The recipe names the exact raw catalog versions,
the HydroBASINS polygon vertices, and the four edges where the ArcticDEM
drainage paths join the basin boundaries. Reassembly of the three ArcticDEM
tiles uses the ordered raw chunks listed in the recipe.

Set `NEON_DATABASE_URL` and the boto3 credentials as described in the
[pipeline setup](../../map-build/pipeline/README.md). Use the R2 endpoint from the pipeline
configuration. Run the input preparation with Python 3.11 or later, boto3 and
psycopg.

```bash
python3 scripts/raw-to-structured/ural-audit/prepare_v8_boundary_inputs.py \
  --r2-endpoint "$R2_ENDPOINT" --work-dir "$URAL_WORK"
```

The verified native macOS geometry replay uses Python 3.9.6, NumPy 2.0.2,
rasterio 1.4.3 with GDAL 3.9.3, pyproj 3.6.1, Shapely 2.0.7, Numba 0.60.0 and
pyshp 2.3.1. Run the replay with that environment. Use a new output directory.

```bash
python3 scripts/raw-to-structured/ural-audit/reproduce_v8_boundary.py \
  --recipe "$URAL_WORK/recipe.json" \
  --recipe-sha256 1e485322c45a8b135e998845c5aa77d856a6d215cd420504d33a8635e8ebc429 \
  --inputs "$URAL_WORK/inputs" --workdir "$URAL_WORK/replay"
```

The replay intersects the basin edge with OSM coastline way 28592677 at
Kara. It models the spring connection from Copernicus GLO-30 and joins the
modeled flow to OSM relation 214415 version 122 at spring node 1385867869.
The last 15.36 m to the node use WGS84 geodesic stations spaced at most one
metre apart. The remainder follows the mapped main-stream graph to its
coastal endpoint. These selections describe the geographic rule used for
V8, with terrain-derived sections dependent on the drainage model.

The canonical compact GeoJSON SHA-256 is
`746e6a85b05e40994e451e49e7df6333b8816dfe1d6624d9c20f9c669e953b32`.
The final newline-terminated file has SHA-256
`904a5014d9ebad365c836dfa80bcabdc8fdac158b1ce0c06d277d657b5870d27`.

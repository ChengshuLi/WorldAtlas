# Approved Caucasus WGS84 source replay

This replay produces the selected Caucasus research boundary directly from pinned R2 raw-source readbacks and structured choices in Neon. It does not build a map. The source gate and new physical-generation closure proofs still need integration before a map run.

The boundary uses WGS84 ellipsoidal distances for drainage slopes, length ranking and geographic nearest-join choices. OSM and source line edges retain their coordinate-linear geometry. Exact source intersections and substring positions are topology operations; they do not choose a geographic nearest feature. Join decisions within 0.02 m are treated as one intersection only if their positions also lie within 0.02 m of each other; distinct competing joins fail closed.

## Inputs and Neon recipe

The selected row is `atlas.decision_mainland_boundaries` in research revision `v2-land-mainland-boundary-draft-1`, boundary `caucasus_blacksea_anapa_to_caspian`. Its `provenance.current_selection.source_assembly_wgs84_v2.recipe` holds the source pins, R2 keys, 1,893 baseline selectors, OSM merge groups, seed choices, approved join anchors and model settings. Its adjacent `recipe_sha256` pins the canonical JSON. Export the jsonb value as text, then canonicalize it with `caucasus_neon_wgs84_recipe_export.py --recipe-text <file> --sha256 <pinned-sha> --output <recipe.json>`.

The recipe names the exact R2 raw objects: HydroBASINS Europe level 12, the pinned author GeoJSON, Anapa OSM coastline, four Abin OSM responses/archives, the 41-response approved OSM bundle, and eight JAXA original tiles. The OSM bundle contains `SHA256-MANIFEST.json`; its response bytes and manifest were verified after a full R2 readback. Read back each R2 key to a local directory under the corresponding `sources_sha256` name in the recipe. No locally derived mosaics, merged OSM files, label arrays or candidate geometries are source inputs.

## Replay

Use the current PR4 versions of the scripts in `scripts/caucasus-audit` and a Python environment with NumPy, SciPy, Rasterio, Shapely, pyproj and pyshp. After exporting the Neon recipe and downloading the pinned R2 objects:

```
python caucasus_geodesic_replay.py \
  --recipe <recipe.json> --recipe-sha256 <pinned-sha> --r2-readbacks <directory> \
  --work-dir <new-work-directory> --output-dir <new-output-directory>
```

The preparer verifies each source hash, verifies the OSM bundle members, rejects conflicting OSM objects, and reconstructs local inputs. The replay expands the structured selector, reconstructs the baseline from HydroBASINS and the author file, constructs the Anapa opening using the OSM coast, reconstructs and models Abin, regenerates all nine JAXA drainage models, and splices their approved interfaces using WGS84 join selection. It verifies the final geometry hash in the recipe. No prior map or saved final geometry is an input.

`caucasus_prepare_neon_wgs84.py` prepares a guarded transaction to install a verified replay and its recipe in the draft Neon revision. It checks the current boundary, Ural and closure pins, reconstructs the Europe polygon and checks its witnesses, and links the eight JAXA tiles already referenced by the boundary as construction inputs. The generated SQL must be executed through the authorized Neon connection and its resulting geometry, recipe and region read back. The transaction accepts either the guarded prior selection or the identical current WGS84 selection, so a verified replay can be applied idempotently; mismatched boundary, region, recipe or source pins fail closed.

## Verification of this revision

The WGS84 source selector replay changed 142 of the 2,292 baseline guide coordinates by at most 0.000243 m. The raw-derived Abin drainage labels and cut matched the previously approved results exactly. All nine other source-derived model label arrays, seed arrays and transforms matched their earlier outputs exactly. The full line retains 10,084 vertices and has SHA-256 `3be87f6ec29be709a07c07c04ce62b6fb00e33f6b35020781a088be5b2d8e8b9`; 44 vertices differ from the previous selected line, by at most 0.000188 m. No native-grid center lay in the padded changed-edge envelopes. The regenerated Europe polygon is simple and valid, and all six stored witnesses pass.

The complete replay was repeated using the recipe exported and hash-checked from Neon; its resulting geometry matched the first replay byte for byte. The selected Neon recipe pins PR4 code commit `a1ec3746753bb19467ae730dc3ab6b0f3ad327e2`. All 16 raw inputs were read back from R2 and matched their recipe hashes; all 16 have corresponding catalog records and boundary-source links.

# Compact SeaVoX input

`extract_seavox_feature.py` selects one feature from a SHA-256-pinned SeaVoX shapefile ZIP. It verifies the archive and the selected decision's source, version, feature ID and geometry hash before it exclusively creates a new output directory. The output contains a single-feature GeoJSON and a manifest binding the archive, decision snapshot, selected geometry and extracted file hashes. Input bytes are never changed. The archive must remain available to downstream stages for independent hash validation.

Use `--inspect-feature ID --archive-sha256 HASH --input-root DIR --archive FILE` to print an unbound candidate geometry hash. Inspect mode does not approve a decision or write output. Persist a decision with that hash through the authorized decision workflow before running a production build. The selected-feature hash depends on the extracted representation and GDAL version; it need not match a previously saved lower-precision GeoJSON.

Build mode requires `--policy`, `--policy-sha256`, `--decision-id` and an `--out` directory outside the input root. The temporary `--allow-unverified-snapshot` flag enables local synthetic testing only. The snapshot parser does not authenticate Neon acceptance; no result produced under that flag is authorized for publication. `ogr2ogr` from GDAL must be installed. The tool extracts EPSG:4326 GeoJSON at 15 decimal places and records the GDAL version.

The adapter only extracts a geometry; it does not rasterize, create assignments, verify an authenticated revision, or publish a grid. Downstream code must verify both archive and feature file bytes, the manifest, and the same decision snapshot before using the geometry.

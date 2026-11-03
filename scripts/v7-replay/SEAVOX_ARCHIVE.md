# Compact SeaVoX input

`extract_seavox_feature.py` selects one feature from a SHA-256-pinned SeaVoX shapefile ZIP. It verifies the archive and the selected decision's source, version, feature ID and geometry hash before it exclusively creates a new output directory. The output contains a single-feature GeoJSON and a manifest binding the archive, decision snapshot, selected geometry and extracted file hashes. Input bytes are never changed. The archive must remain available to downstream stages for independent hash validation.

Use `--inspect-feature ID --archive-sha256 HASH --input-root DIR --archive FILE` to print an unbound candidate geometry hash. Inspect mode does not approve a decision or write output. Persist a decision with that hash through the authorized decision workflow before running a production build. The selected-feature hash depends on the extracted representation and GDAL version; it need not match a previously saved lower-precision GeoJSON.

Build mode requires `--policy`, `--policy-sha256`, `--decision-id` and an `--out` directory outside the input root. The temporary `--allow-unverified-snapshot` flag enables local synthetic testing only. The snapshot parser does not authenticate Neon acceptance; no result produced under that flag is authorized for publication. `ogr2ogr` from GDAL must be installed. The tool extracts EPSG:4326 GeoJSON at 15 decimal places and records the GDAL version.

The adapter only extracts a geometry; it does not rasterize, create assignments, verify an authenticated revision, or publish a grid. Downstream code must verify both archive and feature file bytes, the manifest, and the same decision snapshot before using the geometry.

## Selected archive and comparison evidence (2026-11-03)

A provisional local 92-feature SeaVoX v19 subset ZIP has SHA-256 `53a8209108721f9472b6e8f42c53cb5796f788570c8a315e26362b98f8a3cf97`. It is a derived selection, not a byte-for-byte copy of the provider's complete download. The candidate uses this archive pending investigation of the complete official v19 archive; do not substitute the earlier feature GeoJSON under the same source pin. Gulf feature `24063`, extracted with GDAL 3.10.3 at 15 decimal places, has canonical geometry SHA-256 `fd50f0dc4673c62d5f508681c6d49fa5994802f0bae8fadbaf037175fffc8e22`. Geometry hashes are representation-specific.

The 92 archive feature IDs matched the 92 selected source IDs. Relative to recovered historical source geometries, 49 matched exactly under the ring-normalized comparison; another 40 matched the tested ring sequences within 1.1e-7 degrees. Three (`24019`, `24030`, `24022`) did not pass that comparison. The comparison did not independently verify hole-to-shell grouping. These results do not establish historical geometry identity, and selecting this archive does not make it an equivalent historical source.

A test-only Gulf rasterization over the retained physical-water grid selected 3,582,504 cells in 6,150 spans. The earlier separately fetched Gulf GeoJSON selected 3,582,499 cells. The difference is **nine archive-only cells and four earlier-GeoJSON-only cells**, or 13 changed cells and a net increase of five. The earlier assignment SHA-256 is `cea9870a696168836e0bba5f4e0f0ba47d1a3113921bce5127320ccf3ce96306`; the archive-derived assignment SHA-256 is `a4066e01fc60a835d36748f3c89204d0ca7eeaa81d51fcaed89bb70c0122853f`. These are different gzip files and the latter uses a synthetic decision, not an authenticated revision. Changed `(row, column)` cells are:

- Archive only: `(37507,115259)`, `(37794,115259)`, `(37795,115259)`, `(37904,117087)`, `(37925,115404)`, `(37933,117087)`, `(37964,117087)`, `(38180,117087)`, `(38740,115725)`.
- Earlier GeoJSON only: `(37641,117134)`, `(37641,117140)`, `(38264,114975)`, `(38695,116996)`.

A further test rerasterized 42 non-Gulf features with different geometry against the retained physical-water mask: 217 archive-only and 224 historical-only cells, totaling 441 per-basin changes. Seven features had no cell changes. With the Gulf, the total is 454 per-basin differences, not a count of distinct cells or final-label changes. Hole-to-shell grouping remains unverified even for the 49 ring-normalized exact matches.

This comparison is source-footprint evidence, not a complete rebuild or final-label comparison. Preserve the archive, earlier source and comparison artifacts; regenerate all selected masks and validate their overlap and downstream composition before publication.

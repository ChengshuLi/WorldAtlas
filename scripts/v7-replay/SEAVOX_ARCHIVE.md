# Compact SeaVoX input

`extract_seavox_feature.py` selects one feature from a SHA-256-pinned SeaVoX shapefile ZIP. It verifies the archive and the selected decision's source, version, feature ID and geometry hash before it exclusively creates a new output directory. The output contains a single-feature GeoJSON and a manifest binding the archive, decision snapshot, selected geometry and extracted file hashes. Input bytes are never changed. The archive must remain available to downstream stages for independent hash validation.

Use `--inspect-feature ID --archive-sha256 HASH --input-root DIR --archive FILE` to print an unbound candidate geometry hash. Inspect mode does not approve a decision or write output. Persist a decision with that hash through the authorized decision workflow before running a production build. The selected-feature hash depends on the extracted representation and GDAL version; it need not match a previously saved lower-precision GeoJSON.

Build mode requires `--policy`, `--policy-sha256`, `--decision-id` and an `--out` directory outside the input root. The temporary `--allow-unverified-snapshot` flag enables local synthetic testing only. The snapshot parser does not authenticate Neon acceptance; no result produced under that flag is authorized for publication. The Python environment needs the GDAL bindings. The tool extracts EPSG:4326 GeoJSON at 15 decimal places and records the GDAL version.

The adapter only extracts a geometry; it does not rasterize, create assignments, verify an authenticated revision, or publish a grid. Downstream code must verify both archive and feature file bytes, the manifest, and the same decision snapshot before using the geometry.

## In-process complete batch

`extract_seavox_features.py` reads the complete selected feature inventory from
one archive scan. Its coordinate candidate batches all rings of a feature into
ordinary PyArrow array operations, preserving polygon/ring/vertex order and 2D
or 3D coordinates. Near-zero scientific-notation values use the existing scalar
conversion. Every complete canonical geometry must still match its selected
decision hash; otherwise the unchanged OGR writer is used. No coordinates or
features are omitted. This adds no compiler, process, subprocess or memory cap.

`--scalar-coordinate-reference` retains the original scalar conversion for
exact comparisons. `scripts/v7-pipeline/benchmark_seavox_coordinates.py` runs
both complete selected batches sequentially in the same Python process, then
checks every canonical feature byte and scientific provenance field. Give it
the pinned `--archive`, `--archive-sha256`, `--policy`, `--policy-sha256`, an
existing `--input-root` and fresh `--out`. Timing excludes source acquisition
and the subsequent exact comparison. Record any concurrent shared-machine work;
a complete extraction comparison is not an end-to-end pipeline timing claim.

The separate [complete 92-feature comparison](../../docs/benchmarks/seavox-coordinates-20261108.json)
measured 35.11s scalar versus 32.08s batched, with all 182,644,857 feature bytes
and scientific provenance identical and no OGR fallbacks. This approximately
8.6% observed reduction is one paired extraction trial, not a complete-pipeline
timing. The earlier shared-load result is retained and labeled in the evidence.

## Selected archive and comparison evidence (2026-11-03)

The user-supplied complete SeaVoX v19 archive has SHA-256 `78a7983940aa73989642f2b95f9261c07fc234bf7f8cd14e0dff96bb90ce7e0a` and contains 249 feature records. It is the draft source pin; any build must verify the exact bytes and an authenticated decision revision. An earlier derived 92-feature subset has SHA-256 `53a8209108721f9472b6e8f42c53cb5796f788570c8a315e26362b98f8a3cf97` and is comparison evidence only. Its 92 selected SHP geometry records were byte-identical to the corresponding records in the complete archive; an independent GDAL extraction also matched all 92 canonical geometry hashes. Do not substitute either archive or an earlier feature GeoJSON under another source pin. Gulf feature `24063`, extracted with GDAL 3.10.3 at 15 decimal places, has canonical geometry SHA-256 `fd50f0dc4673c62d5f508681c6d49fa5994802f0bae8fadbaf037175fffc8e22`. Geometry hashes are representation-specific.

The 92 archive feature IDs matched the 92 selected source IDs. Relative to recovered historical source geometries, 49 matched exactly under the ring-normalized comparison; another 40 matched the tested ring sequences within 1.1e-7 degrees. Three (`24019`, `24030`, `24022`) did not pass that comparison. The comparison did not independently verify hole-to-shell grouping. These results do not establish historical geometry identity, and selecting this archive does not make it an equivalent historical source.

A test-only Gulf rasterization over the retained physical-water grid selected 3,582,504 cells in 6,150 spans. The earlier separately fetched Gulf GeoJSON selected 3,582,499 cells. The difference is **nine archive-only cells and four earlier-GeoJSON-only cells**, or 13 changed cells and a net increase of five. The earlier assignment SHA-256 is `cea9870a696168836e0bba5f4e0f0ba47d1a3113921bce5127320ccf3ce96306`; the archive-derived assignment SHA-256 is `a4066e01fc60a835d36748f3c89204d0ca7eeaa81d51fcaed89bb70c0122853f`. These are different gzip files and the latter uses a synthetic decision, not an authenticated revision. Changed `(row, column)` cells are:

- Archive only: `(37507,115259)`, `(37794,115259)`, `(37795,115259)`, `(37904,117087)`, `(37925,115404)`, `(37933,117087)`, `(37964,117087)`, `(38180,117087)`, `(38740,115725)`.
- Earlier GeoJSON only: `(37641,117134)`, `(37641,117140)`, `(38264,114975)`, `(38695,116996)`.

A further test rerasterized 42 non-Gulf features with different geometry against the retained physical-water mask: 217 archive-only and 224 historical-only cells, totaling 441 per-basin changes. Seven features had no cell changes. With the Gulf, the total is 454 per-basin differences, not a count of distinct cells or final-label changes. Hole-to-shell grouping remains unverified even for the 49 ring-normalized exact matches.

This comparison is source-footprint evidence, not a complete rebuild or final-label comparison. Preserve the archive, earlier source and comparison artifacts; regenerate all selected masks and validate their overlap and downstream composition before publication.

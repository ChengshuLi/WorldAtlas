# Shared evidence calculations and preparation, version 1

Install the committed `requirements.txt`. Run `python test/evidence-geography.py` and `python test/ellipsoidal-area.py` for scientific/immutability controls. Workers import `evidence.geometry` and `evidence.immutable` with `scripts/` on their Python import path. Record both helper version strings, actual inputs and method metadata in the version-1 evidence manifest. No helper performs network access, live imports, approval or publication.

## Geography

GeoJSON input is explicitly **longitude, latitude**, WGS84. `transform_point` uses `always_xy=True`; its control is (10° E, 45° N), whose Web Mercator result cannot pass with swapped coordinates. `distance_m` uses inverse ellipsoidal geodesics in metres, including dateline crossings. Projected distance is not substituted for geodesic distance.

`land_area_m2` unwraps short straight longitude/latitude source edges, aligns holes, splits the antimeridian and integrates WGS84 latitude strips through the existing `ellipsoidal_area` implementation. It records square metres and the straight-source-edge method, which differs from connecting sparse vertices by geodesic arcs. Analytic ellipsoid rectangles and independently densified pyproj geodesic areas are tested at equatorial/high latitudes, to relative tolerances 1e-10 and 1e-6 respectively. Dateline holes, multipart islands and small parcels are covered. No count/classification is a factual conclusion merely because the calculation passes.

Invalid unwrapped polygons, overlapping source multipart land, empty/nonpolygon input, ambiguous 180° edges, polar-cap vertices, pole-winding rings, longitude spans ≥180° or latitude spans >120° are rejected with an error. These need reviewed segmentation or a separately versioned method. Almost-polar valid parcels are supported. There is no implicit MakeValid; a worker may inspect a clearly labeled diagnostic clone while preserving original bytes.

`ownership_overlap` unions a stable polity's pieces before intersecting the entire applicable location land footprint. It records that denominator, shares, coverage and method. More than 50% plus recorded numerical tolerance 1e-8 permits a derived winner. Partial coverage cannot manufacture a majority; ties and contradictory positive-area claims remain unresolved. This diagnostic helper is not a replacement for dated direct evidence, resolver precedence or the production ownership pipeline.

## Immutable preparation

`Baseline(repo, commit, files)` verifies an exact immutable 40-character commit and every declared whole-file SHA-256/byte count before any generation. Ordinary committed blobs are read with Git; symlinks/submodules and files above 32 MiB are refused. Mutable checkout files are never treated as original source bytes. Include reviewed release, hierarchy, subject scope, source registry and source byte pins. An entry hash is not a file hash.

`Baseline.subjects(ids)` follows the committed `data/world-index.json` parts read loop and records the **actual containing file** and its byte hash. It never infers `part-0` from an optional feature property. All parts are scanned for duplicate/missing requested identities. The index must itself be pinned. Compressed input has a bounded decompression limit. Source registry/receipt pairs can be checked with `validate_source_receipts`: source IDs, whole-file hashes and pinned retained source paths must agree; duplicate receipts fail. Restricted/unretained sources remain explicit limitations in the evidence contract, not invented retained bytes.

`write_new_vintage` writes only beneath an issue-declared research prefix under `vintages/<new-name>/`. Supply the exact owned prefix from the actual issue; the helper cannot discover a GitHub reservation offline. It rereads pins before creating any directory, rejects symlink destinations, preserves existing files and creates a new file atomically with an exclusive hard link. Original retained evidence is never refreshed in place. Choose a new vintage for changed inputs/methods and retain its predecessor. Output descriptors contain actual compressed and canonical uncompressed hashes.

New JSON is sorted-key compact UTF-8 with one trailing newline and rejects nonfinite numbers. New gzip uses level 9, empty filename, zero mtime and OS header 255 via `GzipFile`; it is reproducible in the pinned Python/zlib environment. Record those versions. Cross-zlib compressed-byte identity is not promised; raw canonical hashes distinguish semantic identity. Older gzip can only be byte-reproduced when its original header/compressor metadata is retained; otherwise produce a separate new vintage rather than pretend it is the original.

A bounded area-ledger CLI is available:

```sh
python scripts/evidence/prepare.py --repo /path/to/WorldAtlas --request /path/to/request.json
```

Request fields: `version:1`, `baseline:{commit,files:[whole-file descriptors],pin_files:{release,hierarchy,scope,source_registry}}`, explicit `subject_ids`, exact `owned_path`, `new_vintage`, and `output_filename` ending `.json` or `.json.gz`. Every role path must occur in the verified baseline files. Optional `source_receipts` are verified against the normalized pinned source-registry array of `{id,sha256}` rows and baseline files. The CLI outputs a new diagnostic ledger with areas, containing-file descriptors, commit and method, plus its output descriptor on stdout. It does not assert territorial/historical approval.

Retrieve lawful public source bytes once, retain permitted originals with URL, license/vintage and receipt, and pin them. Record inaccessible/restricted evidence honestly; do not repeatedly retry a blocked source or use another chat's credentials. This tooling does not migrate old packets or resolve their outstanding factual corrections.

# OpenStreetMap imports

[`features.py`](features.py) imports selected nodes, closed ways and relation
polygons into `atlas.decision_features`. It reads each archived object graph
once through osmium's Python API. [`features/build_features.py`](../features/build_features.py)
handles catalog lookup, verified downloads and transactional storage.

Use the common command below with a `selected_osm_features` construction. Each
selection identifies an output `feature_id`, provider `source_feature_id`,
`object_type` (`node`, `way` or `relation`), `object_version` and identity tags.
The constructor joins member ways at shared node IDs in stable way-ID order.

Relations preserve inner rings by default. An explicit `holes: outer_envelope`
selects the outer envelope, while `ignored_member_roles` identifies non-geometric
members such as label nodes. Optional `ring_anchors` select particular rings by
tagged node ID/version and member way; `parent_relation` checks a selected
membership. These interpretations live in the construction record. The same
implementation handles administrative, reef and archipelago sources.

`test_features.py` covers joining, holes, anchors, membership, source identity
and invalid geometry.

## Boundary lines

Construction records in Neon choose the sources, destination boundary IDs, and
construction descriptions.
Reuse these functions for boundaries made from a single chain of OpenStreetMap
ways. Local processing and the Neon/R2 workflow are separate:

- [`ways.py`](ways.py): read local archives and manifests, check source
  files, join ways into a GeoJSON line, and optionally check its geometry checksum.
- [`build_boundary.py`](build_boundary.py): look up a raw source ID
  in Neon, download it from R2, assemble the line, and save the boundary and source link
  in Neon. Existing notes and supporting source links are retained.
- [`atlas_sources/catalog.py`](../atlas_sources/catalog.py) supplies the document, catalog, and download
  functions also used by other source processors.

## Local processing

Use the shared [project environment](../../../../environment.yml).
`ways.py` uses Shapely to reject a line that crosses itself.
An archive is a ZIP containing `manifest.json` and the OpenStreetMap JSON
responses it names. Each response contains a way and the coordinates of its
nodes. The manifest identifies the ways to join and the starting endpoint:

```json
{
  "start_node": 1,
  "ways": [{"id": 3, "file": "3.json", "sha256": "<response file SHA-256>"}]
}
```

The ways must form one continuous, unbranched line and meet at shared node IDs.
The assembled line must not revisit a node or cross itself. Lines crossing the
antimeridian need a separate construction method that splits them there.
Coordinates are longitude followed by latitude. Source checksums identify the
exact response files used.

Import these functions from `osm.ways`:

| Function | Input and result |
| --- | --- |
| `assemble(manifest, directory)` | Read the responses named in a parsed manifest and return a GeoJSON `LineString`. |
| `assemble_archive(archive, archive_sha256, expected_geometry_sha256=None)` | Check the ZIP checksum and contents, then return the assembled line. Supply the optional geometry checksum to verify an existing result. |

## Neon and R2 workflow

The workflow also requires `psycopg` and `boto3`. Set `NEON_DATABASE_URL` to the
working database and configure R2 credentials through `AWS_PROFILE`.

Run from the repository root, replacing the uppercase placeholders with your
Neon record IDs, and R2 account ID, and choosing a local work directory:

```bash
worldatlas-import \
  --recipe CONSTRUCTION_ID \
  --r2-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --work-dir /absolute/path/to/worldatlas-work/inputs
```

| Argument | Meaning |
| --- | --- |
| `--recipe ID` | Construction record's `source_id` in `atlas.construction_records`. |
| `--r2-endpoint` | Address used to access the Cloudflare R2 account. The catalog supplies the bucket and object path. |
| `--work-dir` | Local directory for downloading and reusing the source archive. |
| `--expected-geometry-sha256` | Optional checksum of the expected boundary geometry. A mismatch stops the command before saving. Omit it when building a changed boundary. |

The construction record is a JSON object in the existing
`atlas.construction_records` table:

```json
{
  "method": "osm_way_chain",
  "source_id": "raw-source-id",
  "boundary_id": "boundary-id",
  "basis": "A plain-English explanation of how the boundary is built."
}
```

`osm_way_chain` selects the typed function in [`build_boundary.py`](build_boundary.py),
which calls the assembly function in `ways.py`. Its signature defines required
fields and types; [shared validation](../README.md#document-validation) checks
them in Python and PostgreSQL. The construction record is editable. Change its settings and rerun its ID.

`worldatlas-import` reads and validates the record, then `osm_way_chain()` looks up its exact
raw source ID in `atlas.source_assets`,
downloads its R2 object into the work directory, checks its size and checksum,
and assembles the boundary. A checked local download is reused on later runs.
An optional expected geometry checksum supports replaying an existing result.

It saves the geometry in `atlas.decision_mainland_boundaries` and its construction
source link in `atlas.decision_mainland_boundary_sources`, in one transaction.
The construction description is saved in the boundary's `provenance.basis` field.
The selected record ID is saved in the boundary’s
`construction_id` column. The source link identifies
the catalog entry with the raw file’s R2 location, size and checksum.
Repeating the command updates the
same boundary, retaining other notes and supporting source links. Changing the
source ID replaces the previous construction source link.

For another boundary using this method, add a construction record and run the
same command.

## Tests

`test_ways.py` checks chain assembly, source verification and invalid geometry.
`test_build_boundary.py` checks the Neon/R2 workflow and database transactions.

Run the tests from the repository root:

The map-builder integration test also uses GDAL's Python bindings.

```bash
python .github/scripts/run_tests.py --suite source_imports
```

The runner creates a disposable database and includes the database write tests.
Those tests cover complete builds, repeat runs, source updates, preservation of
notes and supporting evidence, unrelated records, and failed-write rollbacks.

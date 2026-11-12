# Shared OpenStreetMap boundary tools

Construction records in Neon choose the sources, destination boundary IDs, and
construction descriptions.
Reuse these functions for boundaries made from a single chain of OpenStreetMap
ways. Local processing and the Neon/R2 workflow are separate:

- [`ways.py`](ways.py): read local archives and manifests, check source
  files, join ways into a GeoJSON line, and optionally check its geometry checksum.
- [`build_boundary.py`](build_boundary.py): look up a raw source version
  in Neon, download it from R2, assemble the line, and save the boundary and source link
  in Neon. Existing notes and supporting source links are retained.
- [`atlas_sources/catalog.py`](../atlas_sources/catalog.py) supplies the document, catalog, and download
  functions also used by other source processors.

## Local processing

Use the shared [project environment](../../../environment.yml).
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
Neon record IDs, version, and R2 account ID, and choosing a local work directory:

```bash
PYTHONPATH=scripts/source-imports python3 -m run_import \
  --recipe CONSTRUCTION_ID VERSION \
  --revision DECISION_REVISION \
  --r2-endpoint https://ACCOUNT_ID.r2.cloudflarestorage.com \
  --work-dir /path/to/work-directory
```

| Argument | Meaning |
| --- | --- |
| `--recipe ID VERSION` | Construction record's `source_id` and `version` in `atlas.structured_documents`. |
| `--revision` | Existing group of editable decisions in Neon where the boundary is saved. |
| `--r2-endpoint` | Address used to access the Cloudflare R2 account. The catalog supplies the bucket and object path. |
| `--work-dir` | Local directory for downloading and reusing the source archive. |
| `--expected-geometry-sha256` | Optional checksum of the expected boundary geometry. A mismatch stops the command before saving. Omit it when building a changed boundary. |

The construction record is a JSON object in the existing
`atlas.structured_documents` table:

```json
{
  "method": "osm_way_chain",
  "source_id": "raw-source-id",
  "source_version": "raw-source-version",
  "boundary_id": "boundary-id",
  "basis": "A plain-English explanation of how the boundary is built."
}
```

`osm_way_chain` selects the assembly function in `ways.py`. Each stored
document version is immutable. To change settings, insert a new version and
select it in the command.

`build_boundary()` reads and checks the construction record, looks up its exact
raw source version in `atlas.source_assets`,
downloads its R2 object into the work directory, checks its size and checksum,
and assembles the boundary. A checked local download is reused on later runs.
An optional expected geometry checksum supports replaying an existing result.

It saves the geometry in `atlas.decision_mainland_boundaries` and its construction
source link in `atlas.decision_mainland_boundary_sources`, in one transaction.
The construction description is saved in the boundary's `provenance.basis` field.
The selected record ID and version are saved in `provenance.construction`, along
with the processing function and raw source details.
The destination revision must already exist. Repeating the command updates the
same boundary, retaining other notes and supporting source links. Changing the
source version replaces the previous construction source link.

For another boundary using this method, add a construction record and run the
same command.

## Tests

`test_ways.py` checks chain assembly, source verification and invalid geometry.
`test_build_boundary.py` checks the Neon/R2 workflow and database transactions.

Run the tests from the repository root:

The map-builder integration test also uses GDAL's Python bindings.

```bash
PYTHONPATH=scripts/source-imports python3 -m unittest discover \
  -s scripts/source-imports -p 'test_*.py'
```

To include the database write tests, set `WORLDATLAS_TEST_DATABASE_URL` to a
disposable local PostgreSQL database initialized with
[`001_initial_schema.sql`](../../../database/migrations/001_initial_schema.sql).
Those tests cover complete builds, repeat runs, source updates, preservation of
notes and supporting evidence, revision isolation, and failed-write rollbacks.

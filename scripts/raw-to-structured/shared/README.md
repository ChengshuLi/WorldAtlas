# Shared OpenStreetMap boundary tools

Boundary-specific folders choose the sources, destination records and construction
description.
Reuse these functions for boundaries made from a single chain of OpenStreetMap
ways. Local processing and the Neon/R2 workflow are separate:

- [`osm_ways.py`](osm_ways.py): read local archives and manifests, check source
  files, join ways into a GeoJSON line, and optionally check its geometry checksum.
  Also provides a command for assembling extracted files.
- [`build_osm_boundary.py`](build_osm_boundary.py): look up a raw source version
  in Neon, download it from R2, assemble the line, and save the boundary and source link
  in Neon. Existing notes and supporting source links are retained.

## Local processing

Use Python 3.11 or later. `osm_ways.py` uses Python's standard library.
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
Coordinates are longitude followed by latitude. Source checksums identify the
exact response files used.

Import these functions from `shared.osm_ways`:

| Function | Input and result |
| --- | --- |
| `assemble(manifest, directory)` | Read the responses named in a parsed manifest and return a GeoJSON `LineString`. |
| `assemble_archive(archive, archive_sha256, expected_geometry_sha256=None)` | Check the ZIP checksum and contents, then return the assembled line. Supply the optional geometry checksum to verify an existing result. |

The local command takes three paths: manifest, source directory, and output
file. It writes GeoJSON and prints the point count and checksum. The output file
must not already exist. See the [boundary example](../panama-colombia/README.md)
for commands that assemble first and then verify the result.

## Neon and R2 workflow

The workflow also requires `psycopg` and `boto3`. Set `NEON_DATABASE_URL` to the
working database and configure R2 credentials through `AWS_PROFILE`.

Boundary entry scripts take these arguments:

| Argument | Meaning |
| --- | --- |
| `--source-version` | Exact raw source version to look up in Neon's catalog. |
| `--revision` | Existing group of editable decisions in Neon where the boundary is saved. |
| `--r2-endpoint` | Address used to access the Cloudflare R2 account. The catalog supplies the bucket and object path. |
| `--work-dir` | Local directory for downloading and reusing the source archive. |
| `--expected-geometry-sha256` | Optional checksum of the expected boundary geometry. A mismatch stops the command before saving. Omit it when building a changed boundary. |

`build_boundary()` looks up the exact source version in `atlas.source_assets`,
downloads its R2 object into the work directory, checks its size and checksum,
and assembles the boundary. A checked local download is reused on later runs.
An optional expected geometry checksum supports replaying an existing result.

It saves the geometry in `atlas.decision_mainland_boundaries` and its construction
source link in `atlas.decision_mainland_boundary_sources`, in one transaction.
The construction description is saved in the boundary's `provenance.basis` field.
The destination revision must already exist. Repeating the command updates the
same boundary, retaining other notes and supporting source links. Changing the
source version replaces the previous construction source link.

For another OSM boundary, write a small entry script that supplies its source ID,
boundary ID and construction description to `run_cli()` from
`shared.build_osm_boundary`.
Add `scripts/raw-to-structured` to the Python import path. See
[`panama-colombia/build_boundary.py`](../panama-colombia/build_boundary.py)
for a caller and its README for release-specific commands.

## Tests

Run the tests from the repository root:

```bash
PYTHONPATH=scripts/raw-to-structured python3 -m unittest discover \
  -s scripts/raw-to-structured/shared -p 'test_*.py'
```

To include the database write tests, set `WORLDATLAS_TEST_DATABASE_URL` to a
disposable local PostgreSQL database initialized with
[`001_initial_schema.sql`](../../../database/migrations/001_initial_schema.sql).
Those tests cover complete builds, repeat runs, source updates, preservation of
notes and supporting evidence, revision isolation, and failed-write rollbacks.

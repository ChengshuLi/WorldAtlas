# Shared source-processing code

Boundary-specific folders choose the sources, destination records and rationale.
Reuse these functions for boundaries made from a single chain of OpenStreetMap
ways:

- [`assemble_osm_ways.py`](assemble_osm_ways.py): join the ways listed in a local
  manifest into a GeoJSON line. Also provides a local-file command.
- [`osm_source_handoff.py`](osm_source_handoff.py): check an archive and assemble
  its contents; optionally compare the line with an expected geometry checksum.
- [`osm_boundary.py`](osm_boundary.py): look up a raw source version in Neon,
  download it from R2, assemble the line, and save the boundary and source link
  in Neon. Existing notes and supporting source links are retained.

Use Python 3.11 or later. The Neon/R2 workflow also needs `psycopg` and `boto3`.
Add `scripts/raw-to-structured` to the Python import path, then import functions
from `shared`. For a complete caller, see
[`panama-colombia/build_boundary.py`](../panama-colombia/build_boundary.py).

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

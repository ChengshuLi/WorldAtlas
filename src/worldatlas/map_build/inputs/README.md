# Frozen build inputs

[`selection.py`](selection.py) reads the selected mainland, regional, named-water
and ocean decisions, their raw-source catalog references and entity colors in
one repeatable-read, read-only transaction. The transaction ends before downloads
or map calculations begin.

Save that result with the run. Resume and explicit replay read the saved selection,
so another worker's edits cannot enter partway through a build. Executing code
and runtime versions are separate provenance; a code change does not require
permission to resume.

[`geography.sql`](geography.sql) exports working records once. New selections use
format v3 with one geography collection (including entity colors), contributing construction
settings and exact raw-file catalog records. Stage views distinguish ocean barriers
from mainland closure lines without independent database revisions.

Retained v1/v2 selections remain readable without rewriting their bytes or reading
current Neon data. Their old labels are historical metadata, not working selectors.

Provider endpoint decimals are exported as text to preserve their exact values.
Stored GeoJSON coordinates remain numeric. Source versions, sizes and hashes
come from the same database view as the decisions.

Large feature geometries are read as individual records in that same
transaction. PostgreSQL does not need to assemble all coordinates into one JSON
aggregate before sending them. Basin checks reject changed geometry checksums,
wrong coordinate references and duplicate provider parent/child selections.

`test_selection.py` uses disposable PostgreSQL to check concurrent edits, saved
replay and missing selections. Source-import integration tests also exercise the
real mainland and geography queries against newly imported records.

Generated JSON cache entries are published as complete files, so builds can share
verified inputs and retry interrupted writes. Water and ocean calculations use the
same frozen working selection.

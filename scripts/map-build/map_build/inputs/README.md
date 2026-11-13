# Frozen build inputs

[`selection.py`](selection.py) reads the selected mainland, regional, named-water
and ocean decisions, their raw-source catalog references and entity colors in
one repeatable-read, read-only transaction. The transaction ends before downloads
or map calculations begin.

Save that result with the run. Resume and explicit replay read the saved selection,
so another worker's edits cannot enter partway through a build. Executing code
and runtime versions are separate provenance; a code change does not require
permission to resume.

The SQL files select the corresponding records by a bound `revision` parameter:

- `mainland.sql`: boundaries, closure routes, seed regions, witnesses and rules.
- `regional.sql`: geographic features, affiliations, groups and source evidence.
- `geography.sql`: named basins, ocean routes/seeds and water policies.

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
the input directory and retry interrupted writes. Water rules come from the
selected water revision; ocean-fill rules come from the selected ocean revision.
These revisions may be the same.

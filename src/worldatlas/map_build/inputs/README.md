# Frozen build inputs

Freeze the exact geographic records and raw-source identities that a build uses.

## Use

Save that result with the run. Resume and explicit replay read the saved selection, so another worker's edits cannot enter partway through a build. Executing code and runtime versions are separate provenance; a code change does not require permission to resume. Pass a saved selection to the [map builder](../README.md#use) with `--selection`.

## How it works

[`selection.py`](selection.py) reads the selected parent divisions, their rules, geometry, raw-source catalog references and entity colors in one repeatable-read, read-only transaction. The transaction ends before downloads or map calculations begin.

[`geography.sql`](geography.sql) exports working records once. New selections use format v4 with geography version 2, which uses explicit points for `connected_to`. The selection includes entity colors, contributing construction settings and exact raw-file catalog records. Imported geometry is separate from the rules that assign parent cells to children.

| Neon records | What the builder reads |
| --- | --- |
| `geographic_entities`, `geographic_levels`, `map_category_bindings` | Parent and child relationships, physical eligibility, colors and the map codes that encode ownership. |
| `geographic_rules`, `geographic_rule_features`, `geographic_rule_targets` | Each operation, the geometry it uses and its explicit child targets or face labels. |
| `source_features` | The actual coordinates used by the rules. |
| `construction_records`, `construction_sources`, `geographic_rule_sources`, `source_assets` | How each feature was built, supporting citations and exact raw-file identities. Physical-stage source IDs also resolve through this catalog. |

Release archives retain their original inputs and any code captured at build time. Replay with those records and that code. Historical backfills document gaps in the data or code they could recover.

Imported GeoJSON coordinates remain numeric. Source IDs, sizes and hashes come from the same database view as the decisions.

Large feature geometries are read as individual records in that same transaction. PostgreSQL does not need to assemble all coordinates into one JSON aggregate before sending them. Before calculation, the builder checks working and saved selections for valid geometry and unique entity, feature, and rule IDs. Assignment checks reject conflicting claims.

Water and ocean calculations use the same frozen working selection.

## Code and tests

[`selection.py`](selection.py) freezes working records and validates saved inputs. [`selection_types.py`](selection_types.py) defines the keys and types of the saved records. [`geography.sql`](geography.sql) selects the records. [`releases.py`](releases.py) looks up and caches the files for `worldatlas-compare`.

[`configuration.py`](configuration.py) defines what the build and physical requests accept. The loaders check the JSON fields and types before passing settings to the build. File checksums are verified when files are opened.

`test_selection.py` uses disposable PostgreSQL to check concurrent edits, saved replay and missing selections. Source-import integration tests also exercise the real geography queries against newly imported records.

Run the [map-building suite](../README.md#code-and-tests).

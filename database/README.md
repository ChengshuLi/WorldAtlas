# Database

Neon stores editable geography and construction settings, raw-file identities, and release pointers. Each build freezes its selected records and coordinates before computation. The website reads published files in R2.

## Schema

[`schema.sql`](schema.sql) creates an empty database in dependency order:

| File | Tables and responsibilities |
| --- | --- |
| [`sources.sql`](schema/sources.sql) | `source_assets`: one immutable raw-file capture; `construction_records`: typed editable import settings; `construction_sources`: generated raw-source links. |
| [`construction_contracts.sql`](schema/construction_contracts.sql) | Generated validation and source-reference extraction from Python signatures. |
| [`source_features.sql`](schema/source_features.sql) | Imported geometry and its producing construction. |
| [`geographic_entities.sql`](schema/geographic_entities.sql) | Hierarchy levels, geographic entities, and entity/physical-class map codes. |
| [`geographic_rules.sql`](schema/geographic_rules.sql) | Parent-division rules and their feature, child-target and supporting-source links. |
| [`releases.sql`](schema/releases.sql) | Immutable R2 bundle identity and publication-state flags. |

These twelve tables have distinct purposes. A feature stores geometry; its construction describes how raw sources produce it. A rule explains how geometry assigns parent cells to children. Category bindings encode the resulting owner and physical class; display colors do not determine ownership.

`source_features` has three required columns: `id`, `geometry`, `construction_id`. Geometry is GeoJSON using WGS84 longitude first, latitude second, in degrees. Database checks validate types, nesting, coordinate ranges and polygon closure. Importers also check geometric validity. Provider feature selectors remain in construction settings rather than being copied into output rows.

`geographic_levels` describes the hierarchy; `geographic_entities` links each entity to its level and parent, records its physical eligibility, and stores its color. World has ID zero. Deferred constraints validate the final state of a transaction, including edits involving a parent and its children. Independent families do not require a database-wide entity lock.

`geographic_rules` selects one of six operations. `geographic_rule_features` provides source areas, component-identifying points, boundaries or distance references. Optional `connected_to` links restrict eligible query connectivity using direct points or an interior point derived from combined polygon features. `geographic_rule_targets` identifies direct-child owners and, for divisions, their label points. Each rule stores its rationale. `geographic_rule_sources` links supporting raw sources and records the cited section and interpretation for each one. Ordinary foreign keys and deferred checks reject missing/forbidden roles, incorrect geometry types and invalid targets. See the [division guide](../src/worldatlas/map_build/division/README.md).

`map_releases` points to a release folder and pins `manifest.json` by SHA-256. The manifest pins each release file. At most one bundle is official per version; at most one official bundle is current. Publication changes flags and the fixed R2 homepage separately from map calculation. See [release commands](../src/worldatlas/map_releases/README.md).

## Editing and replay

Raw identity, storage location, size, checksum and capture time are immutable; correctable descriptive metadata remains editable. Changed source bytes require a new source ID. Construction settings, geometry and geographic rules are editable. Released input archives retain their exact earlier values and code.

`construction_records.method` selects the importer and `arguments` stores its named inputs as JSONB. The importer registry and typed Python signatures define their checks. Regenerate those checks after changing a constructor:

```bash
python -m worldatlas.source_imports.contracts database/schema/construction_contracts.sql
```

For an existing database, back up its data, rehearse the transition locally, then apply the tested change in one transaction. Keep one-off transition scripts with the maintenance backup. Keep the authoritative schema in the files above.

## Tests

```bash
python .github/scripts/run_tests.py --suite database
```

The runner creates disposable PostgreSQL databases. SQL checks cover raw immutability, generated construction contracts, geometry, hierarchy, geographic rule relationships and release-state constraints. Python integration tests cover atomic imports, consistent snapshots, concurrent edits, run reuse and release file verification. Tests never use the working Neon database.

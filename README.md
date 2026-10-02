# WorldAtlas

A polygon-based world history atlas with a six-level spatial hierarchy, fourteen map modes, and a timeline from 3000 BC to 2026 AD.

## Run

Requires Node.js 24 or later. Prepared geography is committed; Python and data downloads are **not** needed to run the app.

```sh
npm ci
npm run dev
```

Open http://localhost:3000. The first launch creates `data/atlas.sqlite` from the bundled geography and examples. Subsequent launches preserve imported data. Existing bundled locations receive the complete hierarchy migration on launch; a SQLite backup is made first, and historical states and boundary records are retained. Set `PORT` to change the port.

`localhost` is reachable only on the machine running the server. For a hosted preview, use `npm run build:static` and serve `dist/` with a static host. This exports the current database and preserves all map modes, search, hierarchy, and date filtering without requiring a Node server. It is a read-only snapshot: rebuild and republish after importing new data. `npm run build` retains the normal server-backed build. A static export includes all reference and historical records in the database; keep its hosting audience appropriate for those records.

The persistent Site build uses `npm run build:hosted`: a Worker API with D1 for historical records and graph identities, R2 for media/source bytes, and independently cached map assets in `dist/client`. The owner-private Site's **Add historical records** dialog imports bounded, sourced JSON batches without rebuilding geography. Stable people, event, army, route, artifact and place identities connect through dated evidence; media retains checksums, licenses and attribution. See [storage architecture](docs/HOSTED_STORAGE_ARCHITECTURE.md) and [publication scope](docs/PUBLICATION_SCOPE.md) for the implemented contract and remaining geographic work. Future content-only research should follow [the Luna handoff](docs/LUNA_DATA_HANDOFF.md); [the reproducible checkpoint](docs/REPRODUCIBLE_CHECKPOINT.md) explains fresh-clone recovery and preservation of paused work.

Generate schema migrations with `npm run db:generate`; never edit a migration after it has been applied. `npm run data:hosted-catalog` prepares resumable reference identity imports separately from deployment assets. Local production API verification uses `scripts/verify-hosted-local.mjs` with a local Wrangler D1/R2 instance. Its marked test examples are restricted to localhost and are never seeded into production. Future factual boundary imports invalidate prepared assignments until regenerated; that geometry workflow requires the Python preparation dependencies.

```sh
npm run build
npm start
npm test
npx playwright install chromium
npm run test:ui
npm run build:static
npm run test:static
```

The browser tests launch a separate development server on port 3198. `npm test` validates the full geography, hierarchy, dates, imports, and temporal resolution using an in-memory database.

## Geography and coverage

The seed uses named administrative and physical territories across six continents, excluding Antarctica. The ongoing sourced framework rebuild and its acceptance criteria are documented in [HIERARCHY_REBUILD.md](docs/HIERARCHY_REBUILD.md); its semantic review queue remains open. Country-specific source roles replace the former mean-area heuristic. Compact city territories and published metropolitan groupings consolidate wards; named rural groupings and physical regions refine the opposite scale problem. EU5 counts are rough reference only. See [the complete granularity policy, evidence and exceptions](docs/GRANULARITY.md) and [the current per-location audit](data/granularity-audit.json).

Regions/areas use the published WGSRPD geographic scheme, adapted to six continents, independently of political ownership. Large countries can span regions; small countries/territories can share a region. Whole-territory provinces and geographic portions are explicitly labeled where necessary. These are reference atlas groups, not verified historical administrations. Current counts are generated in the audit and shown in the interface.

The political timeline includes **13,378 dated Cliopatria territory records**, covering portions of 3000 BC–2024 AD, adapted under CC BY 4.0. These are coarse reconstructed political polygons. They are evidence for prepared location ownership: same-polity polygons are unioned, and an owner requires more than half the entire location land area with no contradictory claims. Every political fill comes from that single resolved record. Missing majorities and conflicting claims remain unknown. No historical coverage is extrapolated into 2025–2026. In 2026, modern source polity ownership is available as a labeled reference, not a verified current political snapshot.

Population, culture, religion, location rank, topography, vegetation, and climate remain unknown without dated records. Optional London and Paris examples demonstrate the attributes and temporal transitions; their values are illustrative. No population interpolation or demographic inference is performed. Imported dated boundary overrides replace reference location geometry only for their validity intervals; dated entity names, membership, existence and independent settlement records are supported, with source-required imports. Missing historical names stay unknown and present-day reference labels remain visibly separate.

Duplicate source collections are retired and shared polygon interiors are reconciled before rendering. Existing databases archive retired locations and preserve their imported history. The worldwide overlap audit is in [data/topology-report.json](data/topology-report.json).

Read [source research and limitations](docs/DATA_SOURCES.md) for selection methodology, alternative datasets, licenses, attribution, and remaining gaps.

## Database and temporal imports

Topography, vegetation and climate use [fixed classifications](docs/ENVIRONMENT_CLASSIFICATIONS.md), with stable IDs, display labels and explicit legacy aliases. New imports reject unsupported text; unknown uses JSON null. The full catalog is available from `GET /api/classifications` and the import dialog. Existing evidence remains immutable.

SQLite stores `units`, `locations`, `states`, `boundaries`, historical `polities`, stable `entities`, `entity_history`, and `entity_links`; see [data/schema.sql](data/schema.sql). States contain nullable owner, population, culture, religion, topography, vegetation, climate, and rank. Rank is restricted to `unsettled`, `rural settlement`, `town`, `city`, or `metropolis`; unsettled requires explicit evidence of no inhabitants, independently of unknown or estimated population. Validity uses **inclusive `valid_from`, exclusive `valid_to`**, signed calendar years (negative = BC), and no year zero. Use `2027` as an exclusive endpoint for records including 2026.

Import a JSON object containing arrays named `units`, `locations`, `states`, `boundaries`, `entities`, `entity_history`, and/or `entity_links`:

```sh
npm run data:import -- /path/to/records.json
```

For example, the following *illustrative* record adds a test period without presenting it as evidence:

```json
{
  "states": [{
    "location_id": "atlas:city:GBR-Greater London", "valid_from": 1801, "valid_to": 1802,
    "owner": "United Kingdom", "population": null,
    "culture": null, "religion": null, "rank": null,
    "topography": null, "vegetation": null, "climate": null,
    "source": "Illustrative import example, not historical evidence", "is_example": 1
  }]
}
```

For evidence-backed records, set `is_example: 0` and cite the source and its scope. A state is a complete snapshot: omitted attributes become unknown, not inherited values. Real records take precedence over examples when both cover a year. Unknown is distinct from population zero. Import real records for every interval they actually support; the system does not extend them beyond that interval.

Boundary records use the same interval, source, example flag, and location ID with a GeoJSON `geometry` field. Geographic coordinates must be valid longitude/latitude pairs with closed polygon rings. Imports validate structural geometry, not arbitrary geometric self-intersection or overlap between different locations; curated replacement boundaries must be checked together in GIS before import. Each location has a stable ID and one supported higher-level parent. New `units` require `id`, `name`, `level`, and `parent_id`; new `locations` require `id`, `name`, `parent_id`, and `geometry` (optional `reference_owner`). Each parent must be exactly one level higher: location → province → area → region → subcontinent → continent. Both inserts and updates reject skipped levels; the browser and seed importer validate complete chains. Imports are transactional, reject duplicate record IDs and overlapping intervals within a record type/example class, and require a source for every dated record. Dated records are append-only; explicit entity lifetime imports can update lifecycle metadata. Source migrations preserve imported history and archive replaced reference polygons. Back up the database before making manual corrections. Restart the server after importing reference geography or entity history so its cached catalog refreshes; legacy state/boundary records are queried on each year request. Rebuild static exports after every import.

`GET /api/geography` returns reference polygons, hierarchy, and the temporal entity catalog shared with static exports. `GET /api/snapshot?year=1444&examples=1` returns applicable field records, legacy states and boundary overrides. Historical source polygons are available separately with `source_evidence=1`; they do not paint the normal map. The UI loads reference geography once and requests small temporal snapshots on year changes, cancels stale requests, and debounces the slider. Leaflet hosts a fixed-grid WebGL2 renderer (with a Canvas fallback) without a remote basemap dependency. A Web Mercator grid at zoom 7 (about 1.22 km per cell at the equator) assigns one integer location ID to each covered land cell. Fill, hover and click selection share this ID buffer; parent memberships come only from the location hierarchy. The published build precompiles the canonical ownership grid and loads it as compressed assets; a background Web Worker handles development data or dated geometry changes, storing equal-ID row runs to avoid a dense multi-gigabyte bitmap. Zoom, pan, and resize only read that grid; they never rasterize polygons again. The compressed ownership tables and map-mode palettes stay on the GPU. Navigation changes view uniforms, with no cell buffers, border paths, or texture uploads rebuilt on the main thread. The existing canvas scales during zoom animation. Every zoom uses the original grid: cells naturally become subpixel when viewed from far away, without the previous forced four-screen-pixel blocks. Province and location borders are styled in screen pixels independently of cell resolution. Devices without WebGL2 use the cached Canvas renderer at screen resolution. Only geographic footprint/lifetime changes rebuild the location grid; changing the year selects prepared ownership attributes. Location borders fade out below zoom 7, while thicker province borders remain. Ownership borders are highlighted only in Political mode; geographic modes highlight geographic groups. Features smaller than a cell may disappear at this resolution; background cells denote water or uncovered source coverage.

## Rebuild source geography

Only needed to change the seed. Requires Python 3 and the pinned Shapely dependency; the checked-in provenance records the pinned Natural Earth revision and source hashes.

```sh
python -m pip install -r scripts/requirements.txt
npm run data:prepare
npm run data:history
python test/geography.py
python scripts/audit-granularity.py
```

In environments with an HTTP proxy, use `node --use-env-proxy scripts/prepare.mjs`. Downloaded inputs are cached in `.cache/`. Rebuilding writes seed files. On next launch the bundled reference migration backs up the database, installs new coverage, archives replaced source IDs, and retains their historical records. Custom locations are retained. Replaced source IDs and their historical records are archived; new territories receive new IDs with source-member provenance. geoBoundaries metadata is cached from its current API, with downloaded layer hashes recorded for audit. Preserve existing databases and imported work when regenerating. For a fresh development database, move the old `data/atlas.sqlite` aside while the server is stopped, then restart.

Natural Earth is [public domain](https://www.naturalearthdata.com/about/terms-of-use/); geoBoundaries licenses vary by original source; Cliopatria is CC BY 4.0. The global hierarchy audit is recorded in [data/hierarchy-report.json](data/hierarchy-report.json). See [data/sources.json](data/sources.json), [data/administrative-sources.json](data/administrative-sources.json), and [data/cliopatria/index.json](data/cliopatria/index.json) for attribution and provenance. The interface optionally loads Google Fonts and falls back to system fonts when unavailable.

## Dated names, memberships and settlements

See [docs/TEMPORAL_IMPORTS.md](docs/TEMPORAL_IMPORTS.md) for the import contract. `entity_history` uses `field: name | parent | existence | attributes`, a typed `value`, source, half-open interval, and optional example flag. Names also accept `language` and `name_role: preferred | alias`. All geographic tiers keep stable IDs across renames. Split/merge events link distinct IDs and require their own lifetime/boundary evidence; they do not automatically subdivide land or infer populations.

Every settlement has `kind: settlement` and a location parent. Its rank does not overwrite its host location's rank. Missing habitation is not uninhabited. Imported absent lifetimes suppress nonexistent geographic entities in the applicable year; dated membership also updates province borders and map-mode grouping. Higher boundaries derive from location membership, preserving one parent chain per covered cell.

The current implementation and top-down audit scope are recorded in [docs/IMPLEMENTATION_PROGRESS.md](docs/IMPLEMENTATION_PROGRESS.md). Field precedence and source constraints are documented in [docs/ATTRIBUTE_CONTRACT.md](docs/ATTRIBUTE_CONTRACT.md).

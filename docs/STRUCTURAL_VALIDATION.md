# Structural validation

This runbook checks the schema, import contract, geographic identity and rendering machinery without expanding historical coverage. Content can remain sparse. A passed structural check does not mean a historical claim is accurate, a geographic branch has completed semantic review, or every location has evidence for every year.

Run commands from the repository root with Node 24+, installed npm dependencies, Python 3 and the scientific libraries used by the preparers (`numpy`, `rasterio`, `pyproj`, `shapely`). Browser checks require the Playwright Chromium installation. The validation runner adds no dependencies and stops at the first failed command:

```sh
node scripts/validate-structure.mjs --list
node scripts/validate-structure.mjs contracts
node scripts/validate-structure.mjs scientific
```

`contracts` runs migration immutability, shared attribute and temporal resolvers, local/hosted imports, sourced retirements, geographic releases, prepared-content ingestion and dated-footprint invalidation. `scientific` runs every `test/*.py` file separately, including files with hyphenated names that Python unittest discovery can omit. It also runs GHSL's synthetic `--self-test`, which exercises allocation and interrupted-publication safeguards without preparing another historical epoch. Set `ATLAS_PYTHON` if the scientific environment uses a different Python executable.

## Immutable schema and retained evidence

`test/migration-hashes.test.mjs` pins SQL and Drizzle snapshots for migrations 0000–0006. Existing installations must retain these bytes. Subsequent changes require a new migration; the journal may append entries. The test also verifies migration order and the snapshot identity chain.

| Migration | SQL SHA-256 |
| --- | --- |
| 0000_bizarre_sentry | `a7d4945214a37835bc6cbe8c6c0bfe2073d15fbf76fa1c510e6db072b64ba699` |
| 0001_evidence_retirements | `1f29f4af9eb41425dbd932b9d68e1c54406cb99221a02a2a1bc6b6cab2e3846f` |
| 0002_geographic_reference_releases | `fc03e50b1c7053d9ffe89534395bcbb644e3192231122eca51a424fd14753c53` |
| 0003_unsettled_location_rank | `dc249cb326203bee26446fb010e0f2c05d8bd9bcbb918649199382d517e0fa4d` |
| 0004_population_precision_guard | `302660bc2d4d673bab67820d3c54637ca8cd50460ace57e3142fb3c6f40da447` |
| 0005_population_source_class_guard | `44ec5f5a82317b7c430f7d98439e6ce41d04859d46719c36c3e0dc072f102194` |
| 0006_unresolved_attribute_status_guard | `e2778adcf77945b294609111ecd21a02ffc177e41463393f07e7d15e50e97475` |

The hosted contract fixtures apply the real migration SQL to SQLite using the D1 service interface. Nonempty migration tests compare original claims, retirement pointers, indexes and trigger definitions; they also check foreign keys and append-only behavior after migration. These tests complement native workerd/D1 checks; the SQLite adapter alone is not a native Worker runtime check.

`npx drizzle-kit generate` checks schema/snapshot drift. On this frozen schema it must report no changes. Do not accept generated changes to an old migration as a repair.

## Resolver and correction requirements

The focused suites check half-open source intervals, no year zero, direct/derived/reference/estimate precedence, opt-in examples, stable category IDs, explicit unknowns and unsupported-year gaps. Reference or modeled data cannot become direct historical evidence through import. Names have dated preferred/alias roles; an undated reference name remains separate from a sourced historical name.

Unsettled requires sourced evidence of no inhabitants. Direct literal zero may support it; estimated, modeled, rounded, reference-only, unknown or legacy untyped zero cannot. `metadata.estimate` is recognized in both the shared resolver and SQL contracts. Both import orders are tested against inhabited/settled evidence, including corrected or retired claims. Authoritative source classes are checked separately: estimate/reference sources cannot masquerade as direct evidence, example claims require opt-in, and an example-source zero cannot become factual no-inhabitants evidence even if a claim explicitly supplies `status=sourced`. Migration 0005 aligns the SQL guard with that resolver rule.

Retirements must reach every reader. `test/prepared-evidence.test.mjs` verifies that withdrawn attributes and names cannot reappear through prepared fallback assets, that all API evidence pages have a consistent revision, and that imported/prepared duplicates preserve full provenance. Stable-ID collisions and failed corrections must roll back the whole import, including the ingestion ledger. Old claims remain inspectable.

## Full publication gates

Freeze the local geographic seed, prepared products and hosted/static build together before running this phase. An old `dist` may legitimately fail against newly staged geography; rebuild and revalidate rather than relaxing the comparison.

```sh
node scripts/validate-structure.mjs publication
```

This runs all `test/*.test.mjs` with prepared/static products required, geographic-release preparation tests, `scripts/validate-prepared.mjs`, and exact ownership transport validation. Publication cannot silently skip missing prepared products. The full static/server comparison resolves every active location at 13 dates, with examples on and off, and compares complete values/provenance and the current geographic/identity catalogs.

Ownership checks compare source intervals and evidence with bounded century transport, including majority shares, competing claims and source IDs. Spatial tests cover strict majority of the entire location's land, union of same-polity claims, missing coverage, conflicting claims, dated overrides, latitude and antimeridian geometry. Prepared-product gates compare footprint, source, algorithm, boundary-version and content hashes. Changing a footprint must invalidate derived values; direct evidence can still resolve the location.

Geographic gates check complete adjacent-tier parents, unique identities, retained archives and sourced migration crosswalks. Whole-location pixel ownership is audited separately from source geometry. Global semantic-review gates require every current identity to have an explicit disposition and prevent an unresolved child from being hidden by a structurally complete parent. Review status and pixel exceptions come from current reports, not a target count.

The fixture checks do not replace native hosting validation. Before publication, run the current migrations against an isolated local D1 environment and exercise the real Worker API, R2 media reads/ranges and rollback behavior. Preserve the exact build/package hash and deployment receipt used for that milestone.

An initial native smoke test can use a new, empty persistence directory. After building the hosted bundle, apply its migrations and start the Worker in a separate terminal:

```sh
npx wrangler d1 migrations apply DB --local --config dist/server/wrangler.json --persist-to .cache/structural-native-qa
npx wrangler dev --local --config dist/server/wrangler.json --port 3197 --persist-to .cache/structural-native-qa
```

Then run `node scripts/verify-hosted-local.mjs http://localhost:3197`. This local-only check creates marked fixture identities/claims/media and verifies D1/R2 contracts; it expects an otherwise empty example dataset. Use a separately seeded disposable directory for full atlas/content-only browser verification. Neither command should target production storage.

## Browser and content independence

For a hosted build, start an isolated local Worker with a seeded **disposable** D1/R2 directory and provide its URL. The browser runner starts the development server on `ATLAS_TEST_PORT` (default 3198) and serves static assets on port 3199; these ports must be available.

```sh
ATLAS_TEST_PORT=3307 ATLAS_TEST_API_URL=http://localhost:3197 node scripts/validate-structure.mjs browser
ATLAS_CONTENT_TEST_ORIGIN=http://localhost:3197 node scripts/validate-structure.mjs content-only
```

Use the project build/hosting workflow to start the local Worker; `test/static-rendering.mjs` requires `ATLAS_TEST_API_URL` when `dist/client` is present. The content-only test deliberately imports and retires test claims in the local database and rejects a production hostname. It compares website asset hashes before/after, proving that new content can update profiles, dated titles and political colors without rebuilding the UI.

Browser checks cover all map modes; profiles across all six continents; historical/reference name separation; exactly eight main attributes and collapsed sources; all six hierarchy tiers; complete date controls; sparse/unknown data; source-report retries; desktop/mobile layout; real GPU cell colors and borders; context recovery; and Canvas fallback. Zoom, pan and resize must preserve ownership compilation and texture-upload counters. Performance numbers are observations from the tested environment, not guarantees for every device.

## Current verification and limits

The precision-guard milestone passed 37 rank/hosted-record/shared-attribute checks, the GHSL synthetic conservation/publication checks and Drizzle's no-drift check. A subsequent focused schema/model/server run passed 85 checks with no skips, including full-world seed migrations and persistent imports of the completed name/census products. WGS84 majority, exact transport, geographic-decision and semantic-closure fixture checks also pass. UI checks passed the approved panel, all modes and continents; the two stale/racy assertions were fixed and rerun alongside explicit Unsettled/estimated-zero checks. The immutable-migration gate also passes.

Atomic hosted-stream availability is a separate regression gate: partial failures may not mix fresh attributes/names with missing retirements. A stale cache must retain a complete consistent triple and its actual revision, and may not cross a year/example setting. Its focused regression passes; the contracts runner passed 75 checks before the separate suppression check was added, and that added check also passes. Unavailable withdrawals suppress all attribute sources, including modern ownership fallback and derived Unsettled, without changing the stored content. Final browser checks must confirm the matching cold/warm outage behavior in the built UI.

The source-class guard passed 40 focused contract checks. An isolated native local D1/workerd application of migration 0005 preserved two populated claims, one retirement, all 71 triggers and every other index/trigger definition; foreign keys remained valid. Native inserts also confirmed that an opt-in example zero and example city may coexist without being mistaken for factual no-inhabitants evidence. This receipt is a migration check against disposable storage, not a production deployment or capacity benchmark.

Final publication parity and browser results must be recorded against the final build, after staged geographic repairs and their derived products are activated together. Existing completed historical data is retained; unfinished population output remains unvalidated staging. These checks do not manufacture missing history, finish semantic review, prove capacity for 200 million claims, or substitute for production database capacity planning and device/load benchmarks.

Migration 0006 adds one bounded INSERT trigger: `unknown`, `disputed`, and `no-majority` attribute evidence requires both a null value and a null category ID. Hosted imports, local imports, and the UI preview reject contradictory records before saving. The shared resolver suppresses malformed retained values and category IDs while preserving provenance and precedence; a direct unresolved assignment blocks weaker derived/reference values, including inferred Unsettled rank. Existing claims remain physically unchanged.

Verified on 2 October 2026: 49 focused resolver/import/migration tests passed with no skips and Drizzle reported no schema drift. Native local D1 preserved all four test claims, one retirement, and every original index/trigger definition (71 old triggers plus the single new guard), with foreign keys valid. Native SQL rejected each of the three unresolved statuses with a non-null value and also a null value carrying a category ID. The durable test-only receipt is `data/validation/unresolved-attribute-contract.json`; the portable populated-legacy regression is `test/unresolved-attributes.test.mjs`. These checks do not assert a remote deployment.

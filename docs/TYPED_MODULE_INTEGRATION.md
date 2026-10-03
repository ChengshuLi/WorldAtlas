# Typed module integration and compatibility handover

This finishes the structural contract integration for #529. Empty typed datasets work without factual research, changing the canonical grid, or implementing domain map modes. Production installation and publication are separate owner operations. A green local test is not a historical approval, geographic certificate, native D1 certificate or physical-device result.

## Controlled definitions

Use the existing entity, source and relationship identities. Nine additional structural type definitions are in `data/typed-entity-types-v1.json`; the original identity/type catalog is unchanged. Import these definitions through the existing catalog protocol before importing a feature of one of these kinds. Vocabulary definitions do not assign facts or approve regions.

Each domain worker owns a declarative module and its tests. Coordinate the one explicit module list in `src/observation-modules.js`; never discover uploaded code, mutate the registry globally, replace existing definitions, or have parallel workers rewrite the same registrar. `createObservationRegistry` enforces unique namespaced IDs and definition references. Government is an entity field; location measures and feature links remain separate.

The registry hash is SHA256 of its JSON serialization, not the formatted file hash. The retained base registry in `data/observation-registry-history/base-v1.json` has logical hash `cc6aae6c18099d3e776c73ee4144556422ac87b911aa30aa95bef831ca18d2d2`. The loader verifies that hash and preserves every old definition and module version when adding current definitions. Retain additional reviewed vintages explicitly in that loader before advancing a deployed registry. Never remove a historical registry needed by stored rows or relabel those rows with a new digest. New imports pin the current registry; known old row hashes resolve through the retained unchanged definitions. Unknown hashes fail closed.

Domain children own their algorithms, maps and evidence: GDP identities/units and uncertainty, exclusive polity government, language classifications, literacy cohorts, annual mortality unions, river/lake/shoreline contacts and port operation/functions. Shared provenance validation prevents missing, ambiguous, self/circular inputs and example-to-factual promotion; it does not calculate these domain results or establish their scientific compatibility. Coordinate shared edits and wait for explicit coordinator readiness after dependency completion.

## Additive API

All old record/import payloads and existing resolver semantics remain intact. The optional private Worker routes are:

| Route | Behavior |
| --- | --- |
| `GET /api/typed/v1/capabilities` | Returns typed capability zero on an uninstalled or altered schema; verifies the complete known V3 catalog before advertising support. |
| `GET /api/typed/v1/registry` | Returns the verified current declarative registry and supported retained digests. |
| `POST /api/typed/v1/import` | Bounded atomic typed evidence/correction import with a retained ingestion receipt. |
| `GET /api/typed/v1/snapshot` | Separate observation, feature-link and retirement streams tied to one complete storage fingerprint, revision, registry and territorial pins. |

An import envelope has `version:1`, current `registry_sha256`, exact `expected_geography:{release_id,hierarchy_sha256,footprints_sha256}`, `source_pins:[{id,sha256}]`, optional `ingestion_id`, explicit `examples:true` when applicable, and `observations`, `feature_links`, `retirements` arrays. Factual batches also identify approved `region_ids`. At most 200 evidence rows and 1 MiB enter one request. Approval comes from compiled trusted regional evidence, never a certificate in the HTTP request. No complete regional branches are approved at this checkpoint; real factual imports remain paused.

Each source pin hashes the ordered original source-catalog columns, including original JSON TEXT metadata. It binds the catalog's archive references, not a new verification of remote archive payload bytes. Source archive verification, support and approval remain the research/publication obligations. No source bytes or archived evidence are rewritten by this adapter.

Use `original_json:{value,metadata}` to retain exact raw observation JSON and `original_json:{metadata}` for links/retirements. Parsed content must equal the supplied semantic values; whitespace, numeric spelling, false, zero and null stay distinct. Raw source metadata is returned as `original_metadata_json`. Unsupported source intervals, examples, reference/estimate labels, identities, lifetimes, measurement definitions and source pins fail before an atomic write.

Every factual typed claim's original metadata must include `expected_geography` matching its envelope. Factual derivation dependencies require the same retained territorial pins, including explicitly reused legacy evidence; this prevents importing a result against a newly selected territory without source revalidation. A retirement/replacement cannot transfer evidence between subjects/fields or silently repin its target. A changed published release makes old factual typed reads fail closed for reviewed revalidation while original rows and raw backups remain retained. A prepared archive uses its declared original `geography_pins`; callers must pair it with the matching map assets, never reinterpret it as the latest map.

Derived metadata uses retained `derivation_input_ids`. The supported closure is bounded to 4096 identities, 128 direct inputs per row and 64 levels; unknown/ambiguous identities and cycles are rejected. Both existing typed observations and legacy attribute records can be explicit inputs. Factual outputs cannot consume example evidence, including a same-batch example or an example source. Example-only chains remain available with opt-in under the paused factual gate. Factual dependencies/results require their own approved subject scope; an example label does not approve a factual dependency.

Corrections append a retirement, replacement and journal in one supported atomic batch. An exact ingestion retry returns its retained receipt even if current release/approval later changes; a different payload with the same ID conflicts. An unknown commit response requires retrying the identical request, not inventing a new ingestion ID. No partial batch is usable.

## Prepared/static and client use

`src/typed-snapshot.js` is the shared resolver; it retains old precedence, retirements, source support, original JSON, zero/false/unknown and sparse BC/AD intervals without year zero. `data/typed-prepared-v1.json` is an empty structural archive. It does not assert that any hosted database has installed typed storage.

The static builder validates and copies exact archive bytes to `typed-evidence.json` with `typed-evidence-manifest.json` containing their SHA256 and byte count. The Node server serves the same files and `/api/typed/v1/prepared-snapshot?year=...&examples=1` using the same resolver. These additive prepared routes do not replace old APIs.

Domain modules opt in to `loadPreparedTypedEvidence` or `loadHostedTypedEvidence` from `src/typed-client.js`. The prepared loader requires the exact descriptor hash. The hosted loader fetches the three streams, checks every page/context/source pin, rejects repeated identities/cursors, missing totals and mixed revisions/registry/geography, then resolves the complete coherent snapshot. It bounds pages, bytes and catalog identities, and enforces a whole-load deadline (default60 seconds, configurable1–120000 milliseconds) with caller AbortSignal cancellation and body cleanup; it never combines partial results from a failed load. Existing map navigation does not fetch these empty optional modules or rebuild/upload ownership geography. Future domain UI work consumes these seams under its own issue.

## Storage and owner rollout

V3 is the complete 26-table raw storage contract. The original V1 baseline and V2 archived contracts/restorers remain frozen. On a complete known V3 schema, legacy V2 HTTP reads project the original 23 tables and explicitly label the projection as incomplete. The catalog body keeps its old exact JSON shape; headers `X-Atlas-Storage-Scope:legacy-v2-projection` and `X-Atlas-Complete-Export-Version:3` disclose the complete backup requirement. Current V2 maintenance capture refuses a labeled projection; use the V3 exporter/restorer for complete preservation. Unknown/altered extension schemas cannot be hidden through projection.

The owner forward workflow's closed ordered list now includes `0003_typed_observations`, preserving the original core schema, baseline bytes, guard/function contracts, sequence and owner registry. Isolated PostgreSQL controls prove all three migrations, idempotent/verify-only replay, disabled-guard rejection, and least-privilege access: SELECT/INSERT on the three new tables, no UPDATE/DELETE/TRUNCATE/DDL, no owner-registry access or PUBLIC trigger-function execution. This is a protocol extension, not a receipt of production application.

Normal merges neither deploy nor apply DDL. The designated publisher coordinates issue #39, confirms live-work ownership, preserves rollback, enables and verifies read-only maintenance, drains imports through the shared publication lock, and dispatches only the reviewed manual owner workflow with exact source/operation/baseline/maintenance pins. Verify actual application, raw preservation, catalog, runtime role and import resumption before ending maintenance. Never rerun the original baseline copy, bypass the owner registry or invent provider receipts.

The existing baseline attestation must match the actual source being preserved. If production has changed since that original baseline, the current closed operation rejects the mismatch; a separately reviewed current-source preservation operation is required. Do not relax that guard or substitute the old revision as current evidence. Existing V3 raw export provides the complete input for such a bounded follow-up.

Production PostgreSQL remains at the last verified V2 checkpoint until an authorized reviewed owner operation occurs; its new typed capability stays zero. Native D1 retains its documented failure in frozen0008 before0010 is reached. Keep production D1 at0000–0007 with capability zero; Node SQLite/PGlite results do not certify native D1 forward installation. A separately reviewed compatibility follow-up must resolve that transport limit.

## Reproduction

Run `node --test test/typed-integration.test.mjs test/typed-observations.test.mjs test/neon-forward-migrations.test.mjs test/storage-export-v3.test.mjs test/storage-export-v2.test.mjs`, then the required full regression, scope and hosted package checks. Isolated SQLite/PGlite fixtures are synthetic and invoke no provider. Keep failed probes and distinct reviewer reports alongside corrected results in the owned engineering evidence directory. Final exact-head review, required checks and actual serialized squash merge remain separate completion gates.

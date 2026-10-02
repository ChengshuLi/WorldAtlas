# Dated geographic content campaigns

The research compiler accepts an optional `temporal_geography` namespace alongside ordinary sources, names, attributes and graph content. It writes dedicated batches for `/api/geography/temporal/import`; ordinary dependencies are imported first. Existing scalar-only input and prepared batch bytes retain their original shape. See [the service contract](HOSTED_TEMPORAL_GEOGRAPHY.md), [compiler](../scripts/prepare-research-bundle.mjs) and [resumable importer](../scripts/import-research-bundle.mjs).

```json
{
  "sources": [],
  "temporal_geography": {
    "memberships": [{
      "id": "stable-sourced-parent-claim",
      "entity_id": "EXISTING_LOCATION_ID",
      "parent_id": "EXISTING_PROVINCE_ID",
      "valid_from": 1000,
      "valid_to": 1100,
      "source_id": "EXISTING_HISTORICAL_SOURCE_ID",
      "method": "direct",
      "metadata": {}
    }],
    "existence": [],
    "retirements": []
  }
}
```

This illustrates the input format only; IDs must match the approved geographic release. Sources can be supplied in the ordinary `sources` collection or already exist in hosted storage. Intervals are half-open, exclude year zero and stay inside the source's supported interval. Modern reference sources cannot support ancient claims. Example evidence remains opt-in. Identity existence differs from habitation: uninhabited territory still exists geographically.

Each emitted temporal transaction contains at most 200 rows and 1 MiB of JSON, including its ingestion ID. The importer adds and checks the published release ID plus hierarchy and footprint hashes on every transaction. Server-assigned release/validation fields and unreviewed footprint geometry cannot be submitted through this namespace. Original JSON-text metadata is retained without rewriting its bytes.

## Plan coherent changes before importing

The compiler orders dependencies and keeps each replacement claim together with its retirement records. An atomic replacement group exceeding the request budget is rejected. It does **not** infer a safe global sequence for arbitrary changes to ancestor existence and descendant membership. Database validation checks every committed transaction, across every affected interval; a valid final combined proposal can still contain invalid intermediate transactions.

Inspect the prepared manifest and batch files before import. For a correction that would disconnect a geographic branch, every required reparenting/suppression must either fit in one emitted transaction or be divided into explicitly safe campaigns:

1. Reparent descendants to sourced, existing adjacent-tier parents before suppressing their former ancestor.
2. When removing a whole branch, suppress leaves first, then provinces, areas, regions and higher ancestors. Each phase must be valid throughout its supported intervals.
3. When restoring a branch, restore the supported ancestors before descendants. Do not manufacture existence or parents merely to make a transaction pass.
4. If none of these phases is evidence-supported, retain the proposal as open research rather than partially changing the hierarchy.

Use separate input campaigns for these dependency phases; lexical claim-ID sorting is not a topological branch-change plan. Retirement corrections may also require a single coherent transaction when removing an old claim would alter another claim's validity. The receipt ledger retains earlier successful batches if a later phase fails, so a failure is not a rollback of an entire campaign. Resume with the same verified input and receipts, or prepare an explicit sourced correction to already committed facts. Do not edit successful immutable rows.

## Browser read contract

The production route `/api/geography/temporal/snapshot` reads only affected winning membership/existence claims, with `year`, `examples`, `stream=records|withdrawals`, `cursor` and `limit` (maximum 200 affected IDs). Every page carries a common revision and geographic release/hash pins. Source-free years return no claims and do not download the full reference registry. Permanent withdrawal pages must be exhausted even when their claims do not cover the selected year.

The browser [bridge](../src/hosted-temporal-geography.js) validates bounded packets and converts winning claims into shared temporal history. The caller must exhaust both streams, deduplicate identical source objects by stable ID, and verify the same year, examples context, revision and geography pins before calling `mergeHostedTemporalHistory` with `complete: true`. Partial reads cannot supersede reference history. A retry or cached snapshot must preserve authoritative withdrawals so an outage cannot revive a retired parent claim.

An explicit sourced unknown parent keeps the complete **reference** parent chain for display while retaining unknown historical membership and its evidence. It does not claim that reference membership was historically verified. Names preserve their existing language/alias behavior. Parent/existence resolution follows direct, derived, reference, then opt-in example precedence. Scalar attributes and independently dated names are retained during an authoritative temporal merge.

Historical footprint selection is deliberately unavailable in this phase (`datedFootprints: 0`). Membership changes affect hierarchy and boundaries built from the existing reference location footprints. A future geometry phase requires separately reviewed immutable geometry/grid assets; this campaign interface must not pretend to accept them.

## Executable checks and publication scope

Run `node --test test/research-bundle.test.mjs test/hosted-temporal-geography.test.mjs test/temporal.test.mjs test/temporal-geography.test.mjs test/temporal-geography-worker.test.mjs` for compiler, bridge, actual SQLite/PostgreSQL service and Worker-route checks. The route tests cover revision changes, idempotent imports, retained source evidence, page cursors, examples, invalid pins, body/origin checks, read-only maintenance, scalar snapshots and media routes. PostgreSQL fixtures run actual PostgreSQL through PGlite; they do not establish live multi-session concurrency or production deployment.

Passing local tests does not prove that the forward migration or Worker routes have been published. Production receipts and remaining footprint work are tracked by the main implementation handoff.

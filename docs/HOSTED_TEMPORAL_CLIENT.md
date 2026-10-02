# Bounded dated-geography loading

`src/hosted-temporal-client.js` is a pure read-only loader. It reads only affected dated membership/existence records and permanent withdrawals through the sibling bounded snapshot endpoint. It never scans the entire geographic entity registry, selects independent political polygons or changes footprints. The existing reference footprint remains explicit reference context.

## Interface

```js
const result = await loadHostedTemporalGeography({
  apiGet,                    // async (relativeURL, {signal}) => parsed JSON
  year,
  examples: false,
  expectedGeography: referenceRelease,
  expectedRevision: completedScalarSnapshot.revision,
  signal,
  legacyHistory: []
});
```

`apiGet` throws errors with `status`, `retryable` and optional `suggested_limit` for failed HTTP responses. The loader supplies only `/api/geography/temporal/snapshot?year=…&examples=…&stream=records|withdrawals&cursor=…&limit=…`. Authentication, transport and deployment-origin handling remain the caller's responsibility. The two independent streams start together; dependent pages remain sequential within each stream.

`expectedGeography` must have `release_id` or `id`, plus exact `hierarchy_sha256` and `footprints_sha256` hashes. Every page must match those pins, the selected year, supported capability and the same overall content revision. Passing an expected scalar revision binds the geographical result to that already-complete scalar snapshot. It must never silently change during pagination.

The successful result is:

```js
{
  available: true,
  complete: true,
  revision,
  combinedSnapshot,  // complete wire shape below
  mergedHistory     // sibling merge applied only to caller's legacyHistory
}
```

`combinedSnapshot` has `year`, `stream: 'records'`, the three release pins, all unique `records`, all unique `withdrawals`, a deduplicated source array, `next_cursor: null`, `revision` and `{datedMembership:1, datedExistence:1, datedFootprints:0}` capability. Claims have deterministic entity/collection/ID order; sources and withdrawals have deterministic ID order. It is validated through `hydrateHostedTemporalGeographyPage(...,{complete:true})` before the loader grants authority.

`mergedHistory` uses `mergeHostedTemporalHistory(legacyHistory, combinedSnapshot, {complete:true, year, examples, expectedGeography})`. The caller's array stays intact. Names and unrelated legacy fields remain preserved. Permanent withdrawals remove the matching old claim IDs; resolved winning fields override active fallback fields. Direct unknown parent evidence retains its source and effective reference chain; absence/exclusion handling remains the sibling bridge's responsibility.

The caller can ignore `mergedHistory` and use that same sibling merge after combining its own preserved history and dated names. The loader does not reach into another content cache or invent an archive input. It returns no partial history or incomplete snapshot when either stream fails.

## Consistency, retries and cancellation

With `expectedRevision`, revision drift or HTTP 409 immediately throws a retryable error. The integrating client must discard both scalar and geographical partial reads and retry the whole selected-year snapshot within its own bounded retry policy. Repeating only the geographical stream with a new revision would falsely combine two content states. Pin mismatch is likewise rejected; it cannot authorize a different footprint/grid.

For standalone reads without a scalar revision, the first valid page anchors both streams. Drift restarts both streams from empty cursors, with a default maximum of two attempts (hard maximum three). No rows from the discarded attempt survive. Every retry keeps the supplied geographic pins fixed.

Retryable HTTP 413 can reduce only the affected stream's page limit, preserving its cursor. An invalid suggested limit is rejected. Normal page size is at most 200 affected entities/withdrawals; membership and existence together can contain up to 400 winning rows per record page. Empty/source-free years need exactly two requests and no reference registry read.

Cancellation propagates the caller's original abort reason, aborts sibling requests, and removes temporary listeners. Pending requests cannot publish a partial result or become authority for a different year. Ordinary transport failures propagate to the caller without an authoritative empty fallback.

## Operational bounds and validation

Defaults are 2,000 total request attempts per snapshot attempt, 150,000 unique claim/withdrawal rows and 64 MiB of cumulative serialized wire data. A page cannot exceed 8 MiB. Options allow deliberate bounded adjustments: `limit` 1–200, `maxAttempts` 1–3, `maxPages` 2–100,000, `maxRows` 0–1,000,000, and `maxBytes` 1 KiB–256 MiB. Exceeding a budget throws rather than truncating evidence or claiming completion.

Source records are validated and compared by ID before deduplication. Identical observations are reused; conflicting observations reject completion. Legacy JSON source metadata is parsed once for the complete aggregate, allowing hydrated claims to share the same source object. Identical affected rows repeated across pages deduplicate by stable collection/claim ID. Different winners for the same field, changed identities, missing sources, repeated cursors, malformed intervals/example flags, unsupported capabilities and a withdrawal targeting an active winner all reject authority.

`onProgress` is an optional callback receiving `{stream,pages,rows,sources,revision}` after each verified page. These are loading progress counts, not a declaration of completed evidence coverage.

```sh
node --test test/hosted-temporal-client.test.mjs
```

Focused tests cover both streams, source-free years, exact deduplication, cross-page/cross-stream contradictions, fixed-revision failures, bounded standalone retries, oversized-page adjustment, abort propagation, budgets, cursors, explicit unknown parents and the BC/AD boundary. They use synthetic facts and perform no live content reads or writes. Existing bridge/database tests separately verify the source/tier/interval and transactional contracts.

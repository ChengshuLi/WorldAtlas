# Hosted dated geographic membership and existence

This forward contract stores dated **parent membership** and **geographic identity existence** on the existing approved geographic IDs. It does not publish historical polygons, rebuild the grid, change the reference release, or describe habitation. A location's existence is independent of whether people live there.

The implementation is `hosted/temporal-geography.js`, with SQLite migration `drizzle/0008_temporal_geography.sql` and PostgreSQL migration `postgres/migrations/0001_temporal_geography.sql`. The PostgreSQL migration follows the frozen fourteen-table foundation; it must be applied after the verified foundation copy. These files have local SQLite/PostgreSQL tests, not a production migration receipt.

## Import contract

The intended dedicated Worker route is `/api/geography/temporal/import`. Its payload is separate from ordinary scalar, name, relationship and original-evidence retirements:

```json
{
  "expected_geography": {
    "release_id": "APPROVED_RELEASE_ID",
    "hierarchy_sha256": "64_LOWERCASE_HEX_CHARACTERS",
    "footprints_sha256": "64_LOWERCASE_HEX_CHARACTERS"
  },
  "memberships": [{
    "id": "STABLE_CLAIM_ID",
    "entity_id": "EXISTING_GEOGRAPHIC_ID",
    "parent_id": "EXISTING_ADJACENT_TIER_PARENT_ID",
    "valid_from": 1000,
    "valid_to": 1100,
    "source_id": "EXISTING_SOURCE_ID",
    "method": "direct",
    "status": "sourced",
    "is_example": 0,
    "metadata": {}
  }],
  "existence": [{
    "id": "STABLE_EXISTENCE_CLAIM_ID",
    "entity_id": "EXISTING_GEOGRAPHIC_ID",
    "value": "not_exists",
    "valid_from": 1000,
    "valid_to": 1100,
    "source_id": "EXISTING_SOURCE_ID",
    "method": "direct",
    "metadata": {}
  }]
}
```

The example above describes shapes, not a valid simultaneous geographic change. The existing descendants must still have complete chains. Do not import it verbatim.

Each request contains 1–200 rows and at most 1 MiB of JSON. Sources and existing approved identities must already exist. Dates are half-open, have no year zero, and range from 3000 BC through the exclusive end 2027 AD. A claim must fit entirely inside its source interval and any known identity lifetime. This capability accepts historical, reference and example sources; estimated membership/existence requires a future reviewed policy rather than silent acceptance. Reference sources require `method: "reference"`; examples remain opt-in.

Methods are `direct`, `derived` and `reference`. Statuses are `sourced`, `derived`, `reference`, `unknown`, `disputed` and `example`. Membership `parent_id: null` is explicit historical uncertainty; existence values are `exists`, `not_exists` or `unknown`. Unresolved statuses require null membership or unknown existence. Metadata is an object or original JSON object text, at most 16 KiB. Original JSON text is retained unchanged. Claim rows and receipts are immutable. Claims are pinned to their approved release; a later reference release requires a documented maintainer migration/crosswalk or an explicitly compatible older release. The reader does not silently reinterpret old memberships across merges, splits or footprint changes.

Resolution chooses direct evidence before derived assignments before reference claims. Factual claims precede examples. Equal-precedence overlapping claims are rejected instead of arbitrarily picking a winner. An explicit unknown winning parent blocks weaker historical parent claims and uses the separately labeled, complete reference parent chain. That fallback is geographic context, not evidence of ancient administrative membership. An unknown existence claim does not assert historical presence or absence; the reference identity framework remains available unless a sourced absence or known identity lifetime excludes it.

## Atomic corrections and independent SQL validation

Temporal retirements have their own collection:

```json
{
  "retirements": [{
    "id": "STABLE_WITHDRAWAL_ID",
    "collection": "memberships",
    "target_id": "ORIGINAL_CLAIM_ID",
    "replacement_id": "REPLACEMENT_CLAIM_ID",
    "source_id": "CORRECTION_SOURCE_ID",
    "reason": "Explain the sourced correction",
    "metadata": {}
  }]
}
```

Include a new replacement in the same request when it is not already retained. A permanent withdrawal uses `replacement_id: null`. Original rows remain available as evidence. Cycles, example withdrawal of factual evidence, unsupported source intervals and missing replacements are rejected.

Imports add changes, a validation receipt, and an ingestion receipt in one transaction. New rows have deferred foreign keys to the validation receipt; the receipt has a deferred foreign key to the corresponding new ingestion. SQL independently checks source contracts, published geography hashes, replacement completeness and the resolved hierarchy. A caller-supplied validation flag cannot replace these checks. A sealed receipt cannot accept additional claims. Exact stable retries preserve the original claims and return the same public counts.

Chain validation walks the changed branches' possible descendants and ancestors, using reference edges and active dated edges. It evaluates every claim and identity-lifetime transition in that closure, with examples disabled and enabled. A present non-continent must have one present adjacent-tier parent. A continent cannot have a parent. Suppressing an ancestor requires atomic descendant reparenting or suppression; otherwise the transaction fails. The closure can be large for continent-wide changes, so maintainer batches must be benchmarked before importing global reorganizations. Local correctness tests are not a capacity promise for arbitrarily large histories.

PostgreSQL uses the same publication/import advisory lock `807245315,1`. Forward deployment must grant the restricted application role the new tables' required permissions and verify those permissions; the frozen base role installer does not automatically grant future tables.

## Bounded production reads

`temporalGeographySnapshotPage(db, year, options)` is the production transport helper. Options are `releaseId`, `examples`, `cursor`, `limit` (1–200) and `stream` (`records` or `withdrawals`).

Each `records` page keysets at most 200 affected entity IDs and returns at most two winning rows per ID: one membership and one existence. It fetches reference context only for those IDs. A year without matching claims does not scan the reference entity or membership registry. Ranking happens in SQL. Winner and source text is byte-preflighted before materialization, and the final JSON page is limited to 8 MiB. A 413 includes `suggested_limit`; a single oversized legacy source still needs maintainer review because reducing the page count cannot shrink that source.

Every page contains:

```text
year, stream, release_id, hierarchy_sha256, footprints_sha256,
records, withdrawals, sources, next_cursor, revision,
capability: { datedMembership: 1, datedExistence: 1, datedFootprints: 0 }
```

`sources` is a deduplicated array containing the source identity, original supported interval and parsed metadata. Each winning row retains its claim and validation IDs, source ID, original claim interval/method/status, `reference_parent_id`, `reference_active`, `entity_kind`, and known entity lifetime. Membership winners additionally carry `effective_parent_id`, `parent_context` and `membership_status`. Unknown membership uses the reference effective parent with `parent_context: "reference"` and `membership_status: "unknown"`. Existence winners are returned even when their value excludes the entity.

The `withdrawals` stream pages **all** permanent withdrawals for the selected release, regardless of selected year. The client must finish both streams, require matching release hashes and revision on every page, and then merge them into the local reference framework. Failed or incomplete pages cannot gain authority over retained static/cache history. If the revision changes, restart the whole read. No historical claim is made by a fallback reference chain.

`temporalGeographySnapshot` is a full-registry resolver for offline/maintainer validation and tests. It must not be routed as a production year endpoint. The raw `temporalGeographyPage`, `temporalWithdrawalsPage` and `temporalGeographyEvidence` helpers support evidence inspection; normal map rendering should use winners from the bounded transport.

## Deployment and remaining engineering

This phase must be integrated with Worker routes, the bounded map snapshot reader, browser data client/shared temporal resolver, evidence UI, runtime grants, raw export/restore versioning and publication gates before it is advertised as deployed. Those changes belong to technical maintainers. Research imports are limited to existing approved identities until that integration is published and verified.

Dated footprint manifests, staged approved location sets, immutable geometry/grid assets, source-bound date selection, semantic geometry checks and renderer/cache switching are a separate forward engineering phase. `datedFootprints: 0` deliberately exposes that limit; membership evidence must never paint independent source polygons as normal political fills.

The local tests cover SQLite and actual PostgreSQL 18.3 via PGlite: complete fallback chains, BC/AD intervals, source/tier/pin contracts, ancestor suppression, interior transitions, explicit unknown precedence, opt-in examples, immutable original JSON bytes, atomic correction/rollback, forged receipt prevention, raw fractional-year rejection and retention guards, known lifetimes, actual hosted-to-browser hydration, bounded winner pages, permanent withdrawals and oversized legacy source preflight. They establish contract behavior, not a live production cutover or completed worldwide historical research.

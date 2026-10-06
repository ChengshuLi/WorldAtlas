# Queue freshness infrastructure — #1210, first implementation

Issue changes, confirmed merges and accepted releases now check the original
issue and its dependents. The existing hourly full audit catches missed events.
Only the dedicated attention label is projected; scope, readiness, scientific
acceptance, canonical claims and production permissions remain reviewed.
There is no additional ledger. Main / issue creation consumes the original-issue
flags. Auditor #726 continues quality review and its existing table.

The audit now validates evidence declarations and reports exhausted PR budgets
with exact acceptance-to-child dispositions. New last-partial-PR submissions
must retain an actual bounded handoff through the trusted merge queue's initial
and final authority checks. Legacy claims/scopes are preserved. Workers must
record their reviewed handoff after merge and release safely.

Local deterministic controls cover malformed evidence, symbolic pins, stale
scope/PR lists, missing/PR/umbrella follow-ups, failed event outcomes, dependency
closure, targeted coverage, idempotent attention flags, changed issue inputs,
partial-read retention and the actual trusted integration rejection. Separate
compatibility controls cover the existing evidence, claim/lane, merge-client,
entrypoint and capacity behavior. Exact test outputs are retained beside this
handoff. Local tests do not prove hosted workflow permissions or live delivery.

Remaining #1210 acceptance: independent exact-head review and normal hosted
integration; actual main/event/full-audit readback; retrospective original-issue
acceptance reconciliation and deduplicated residual children, including the
separate typed-hierarchy subject gate #1208. Do not close #1210 based on this
infrastructure PR alone. No source, geography, provider or production mutation
was performed by these controls.

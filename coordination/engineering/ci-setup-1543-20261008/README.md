# #1543 P0: shared Actions API quota

The human prioritized preventing another shared Actions installation quota outage
before the remaining setup and scientific performance work. This is partial work
on #1543, not completion of its original setup acceptance or #1544.

The concrete missing optimization was the trusted premerge evidence entry point:
queue validation used authenticated exact-OID Git batches, while premerge fetched
whole files individually through REST. The revised entry uses the existing bounded
transport with complete byte validation and fresh mutable authority. Superseded
read-only handoff, PR regression and PR package runs for the same PR are cancelled.
Main package push observations remain separate. Other workflows, including
the five-minute scheduler and serialized mutations, retain their scheduling.

`pr-1547-comparison.json` and `pr-1552-comparison.json` bind observed candidate/base
commits and manifest hashes. The revised path performed real remote reads with
the local credential; the old path was replayed offline using the identical
captured mutable metadata and exact local Git blob bytes. It is a request-count
comparison, not a hosted Actions-token capacity measurement or scientific review.
Both paths produced identical full validation results, including every limit.
Do not infer global hourly capacity savings or guaranteed availability from two
PRs. The baseline did not issue hundreds of unnecessary real API requests.

`compare-transport.mjs` repeats the read-only experiment for explicitly supplied
current PR numbers from an owned, adequately admitted checkout whose shared Git
store contains their complete objects:

```
node coordination/engineering/ci-setup-1543-20261008/compare-transport.mjs 1547 1552
```

It requires the existing local GitHub credential, never prints it, creates bounded
transport scratch in the working checkout, removes that scratch and retains small
reports in a fresh exclusive `.cache/quota-probe-*` directory. At most two distinct
PRs are accepted per run; failed probes remove only their newly owned scratch and
never publish partial comparison reports. Current heads can change; a different head is a different
observation. No candidate code, hooks, provider actions or live scientific
computation run. The retained results are observations, not expected outputs for
a new reproduction. Missing local objects fail rather than being assumed valid.

`quota-controls.log` records the focused entry-point, byte corruption, stale head,
readiness race, quota, ambiguous write, notification loss, deadline, profile and
trusted-checkout controls. The large synthetic transport inventory models the Git
protocol in memory; separate transport tests and the two remote probes use real
Git objects. No input/hash/semantic/file-budget or independent review gate is
relaxed. Geography/history source-only regression selection is unchanged.

Claim failures now retain their exact quota diagnostics and HTTP accounting even
when notification fails. Proven quota rejection avoids another doomed comment;
possible writes require reconciliation of canonical state. No internal mutation
retry or unbounded quota sleep is added to the five-minute job. Profile and linked
issue failures similarly retain their actual sanitized quota evidence. Deployment
classification retains a proven quota refusal and makes the required package job
fail before costly setup/build work; unknown non-quota input inventories still
choose the conservative full-build fallback. Concurrent read batches drain their
bounded requests before accounting/diagnostics are finalized. Successful
response headers provide numeric capacity observations without additional polls.

Limits: Actions installation and local credentials have distinct budgets. Shared
quota remains finite and concurrent jobs can exhaust it. Existing final queue
capacity/deadline admission remains mandatory. Workers wait for actual retry/reset
conditions rather than immediately redispatching. Hosted post-merge token behavior,
worker adoption and whole-window consumption must still be observed; local tests
alone do not prove those. The existing finite transport may retain REST fallback
when a complete inventory exceeds its cache admission; no evidence limit or
scientific acceptance is widened in this change.

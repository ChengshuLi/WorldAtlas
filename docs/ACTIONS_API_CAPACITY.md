# Actions API request capacity

The trusted queue reports actual HTTP attempts by phase and endpoint category.
The local result includes the final notification; the public decision receipt's
count stops before that notification. These counts exclude Git transport and
external consumers sharing the same credential. They are observations, not a
reservation or a guarantee that capacity cannot be exhausted.

Final capacity and scheduler admission inspect headers from an actual repository
GET. Generic `/rate_limit` can describe a different bucket and cannot establish
repository capacity. Invalid or missing repository headers fail closed. A primary
zero/reset or a secondary Retry-After can cause a bounded read wait; ordinary
permission denial cannot. Scheduler refusal spends no execution attempt. A quota
rejection retains its durable request identity and an observable next retry time.
Registration and preparation read waits share an eight-minute API deadline;
final reads share a 61-minute API deadline inside the existing final job limit.
Writes and ambiguous transport outcomes are never automatically retried.

Evidence validation binds every input to an exact complete tree, path, mode,
size and blob OID. Eligible bounded inventories transfer those exact blob OIDs
in one Git fetch into a disposable bare store. Each object is checked against
its whole Git blob hash and declared size before the batch becomes available.
No candidate checkout, candidate execution, persistent credentials, shared
store or mutable authority cache is introduced. Existing descriptor/byte,
scientific, independent-review and exact-head checks still run. Inventories that
exceed the transport's cache limits use the existing complete REST validation.

Issue state, claims, review receipts, checks, refs, PR disposition and FIFO
admission still reach GitHub on each required authority pass. Geography/history
CI selection and the five-minute merge scheduler are unchanged.

If a bounded wait ends, inspect the same request and current workflow before
recovery. Do not manufacture a new request, retry an uncertain write, infer
completion from quota recovery, or bypass review. Notification/cleanup failure
is retained in the existing result artifact. The direct hotfix exception
explicitly authorized by the human is not permission for ordinary worker bypass.

## Whole-system investigation and completion criteria

The global investigation covers 1,243 workflow runs created between
2026-10-08 02:05 UTC and 2026-10-09 02:05 UTC. Creation times identify the
selected runs, not the billing hour of each request. The measured demand is:

| Consumer | Recorded demand | Measurement limit |
| --- | ---: | --- |
| PR evidence file reads | At least 21,454 requests | Code-derived lower bound from 171 successful authenticated receipts; failed scans, comparison originals and metadata excluded |
| Merge preparation/finalization | 13,987 HTTP attempts | All 91 attempts accounted; 4,532 immutable metadata attempts and 9,455 other attempts |
| Merge registration/scheduling | 1,873 HTTP attempts | 118 of 119 runs accounted; the missing count is unknown |
| Accepted claim transitions | At least 1,515 requests | Code-derived floor for 158 accepted transitions; refused transitions, dynamic dependencies and additional pages excluded |

These are different measurement kinds. Do not combine them into an exact total,
market share or percentage reduction. Historical worker CLI reads, Actions'
internal traffic and some selectors have no complete endpoint telemetry.
Provider/publication workflows were callable but had no executions in this
window. Missing usage is unknown, never zero. Workflow core receipts observed a
5,000-request limit; admission must use the actual authenticated response rather
than assume that value or a documented default applies to every credential.

Volume matters independently of cost per operation. In this window geography
accounted for 698 PR-triggered workflow runs across 212 distinct branch/head
pairs; engineering accounted for 141 across 38 pairs, and history research for
three across one pair. These are workflow runs, not distinct PRs or unnecessary
duplicates. Required metadata checks can legitimately run again after a body
edit. Consolidation must not launch full regression again merely to refresh
metadata, or omit that refresh because the code head stayed the same.

The fully accounted merge/scheduler subset contains 15,144 GET attempts and
716 mutation attempts. This subset excludes claim and worker mutations; it
cannot establish an installation-wide secondary-rate margin. Fewer primary
charges alone do not prove that mutation or concurrency limits are safe.

PR #1556 addresses the largest file-read class. Its approximately 93% reduction
was measured in two local evidence-checker comparisons, not whole-system hosted
traffic. Older PR bases still execute the older trusted checker. Merge metadata,
independent selector reads and observer traffic remain separate obligations.

The following is the global implementation target, not a claim that it is
already deployed:

1. Reduce demand first. Reuse one short trusted PR metadata phase for
   linked-issue ownership, test-profile selection and package applicability.
   Evidence transport and scientific checks run separately alongside selection
   and tests; they never become a dependency of test selection.
   Selectors share freshly fetched records within one bounded authority pass;
   final contract/ownership reconciliation bypasses that pass. Reuse authenticated
   conditional GETs across passes: every required authority pass reaches GitHub. A valid unchanged 304
   can avoid primary charges; it does not eliminate secondary request traffic.
   Keep bounded exact-object Git transport and complete scientific validation.
2. Reduce aggregate demand without pacing normal development. Remove repeated
   downloads, redundant readers and unnecessary reruns before considering any
   new scheduling control. Do not add a shared API queue, fixed request sleeps
   or routine per-client FIFO serialization. Independent reads remain parallel
   after the first already-required response establishes actual capacity. Respect
   actual quota refusals and remaining job deadlines; preserve durable request
   identities when work must defer. A canceled pending run is not proof that its
   external operation failed or permission to submit again. Verify mixed bursts
   and peak headroom after the demand reductions; client floors alone do not
   establish installation-wide capacity.
3. Cover every boundary. JSON readers, artifact redirects, provider proof reads,
   publication/readiness tools and local claim/merge observers require explicit
   admission and accounting or a documented bounded exception. Signed artifact
   delivery remains credential-free. Do not hide these reads behind an adapter
   that reports only the surrounding logical operation.
4. Make recovery sustainable. Submit once; discover the exact execution with a
   complete bounded inventory, then observe only that execution and durable
   result. Fit retries to the actual remaining deadline. Primary reset time
   alone grants no capacity. Preserve ambiguous writes and usable recovery
   capacity; a floor must not accidentally make its cleanup allocation unusable.
5. Verify rollout and total workload. Old trusted baselines and worker-held
   instructions do not refresh themselves. Check actual new-base runs, worker
   handoffs and callable low-frequency consumers. Compare mixed engineering,
   geography and history workloads, including burst arrivals, cold transport,
   failure/recovery, actual paid/304 attempts and end-to-end queue delay.

Consolidation must preserve the existing native `scope`, `evidence`, `profile`
and regression proof identities, exact scheduled head/base, credential isolation,
complete-path inventories and ordinary merge-queue protections. A missing or
failed metadata check cannot turn required verification into a successful skip.
Source-only research must retain its focused test path. A saved old scientific
verdict cannot replace current input authentication or required positive proof.

Global completion requires measured peak demand with margin, verified safe quota
recovery for the controlled clients and real hosted adoption. Passing helper
tests or merging one request-saving PR does not establish those properties.
External consumers and GitHub service failures remain outside the repository's
control; the system must defer safely rather than promise unlimited availability.
No new ledger, background chat monitor or unattended report consumer is needed.

Developer latency is an acceptance condition alongside demand reduction. The
metadata phase does not allocate a Git evidence store. Evidence retains its own
required native check and actual job deadline. Scope, geography, regression and
package jobs depend only on quick metadata selection, so expensive evidence
verification can overlap them. Body-only edits refresh authority in a separate
cancellation group; they neither cancel unchanged-head tests nor rerun them.
A missing scientific verdict still blocks merging. Hosted validation must measure
cold/warm time to usable checks and queue delay, not merely count fewer HTTP
attempts. The draft is not accepted on local request savings alone.

The draft common client has no discretionary request pacing. Concurrent attempts
reserve their possible primary charge in memory; an authenticated 304 refunds
only its own reservation. A conservative observed floor protects failure handling.
Only owned integration-candidate cleanup and a durable merge-result notification
may use its bounded recovery allocation (at most four actual attempts while below
the normal floor). Existing exact-ref ownership and fresh-SHA checks still precede
deletion. This cannot reserve capacity against other clients or external consumers.
Artifact redirect requests share actual HTTP accounting/admission; signed archive
delivery receives no GitHub credential. Package classification uses the same
client rather than a separate unaudited JSON reader. Claim CLI checkpoints retain
original request reason separately from observation failures, and canceled or
uncertain dispatches never cause an automatic second write. These are draft
implementation facts, not hosted rollout or global capacity evidence.

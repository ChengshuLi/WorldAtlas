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

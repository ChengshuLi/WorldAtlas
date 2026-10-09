# #1201 final hosted verification

This packet completes the CI inventory and measured harness improvement in PR
#1537. It reports observed executions; it does not promise identical host speed or
scientific approval. The implementation was independently reviewed at
`defda65defb79a403788228bdf3f229039a5aa70` and merged normally as
`cd063c6e253238ba49572c62a1addf67a0fcdb49`. `actual-main-files.json` checks every
changed Git entry, including modes, against the reviewed head at that merge.
`executed-code-vintages.json` separately matches the actual before/after PR and
combined-candidate code bytes to their authenticated ancestor inputs.

## What changed and what remains protected

Unchanged complete-world custody is no longer redundantly authenticated during
fixture finalization before each semantic validator authenticates it again.
Altered descriptors and shared receipt bindings are updated together; unchanged
corrupt bindings cannot repair themselves. All seven self-consistently rehashed
semantic corruption cases remain, alongside the separate uncached exhaustive
positive proof. The narrowly input-keyed reconstruction cache is unchanged;
additional controls test all relevant identity/roster/property/geometry/tile/scope
changes and method setup/teardown. Their counted synthetic kernel tests cache
behavior, not scientific truth.

The long corruption-control file moved from the migration shard to the middle
shard. All discovered test files still run exactly once. The runner and Python
wrapper stream results, retain bounded output, propagate failure/cancellation and
clean their owned descendants without killing unrelated processes. Independent
review found inherited-pipe and ordinary-failure cleanup gaps; those were repaired
and tested before the accepted final head.

There are no new scientific/source exclusions. The authoritative package-input
contract, canonical restoration on full jobs, credential-free candidate execution,
SHA-bound exact-head review and normal serialized merge are unchanged.

## Actual hosted engineering comparison

The before PR run is [#1529 / 37848776291](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37848776291)
at `924c06d41356bbbf327f5d2cac95097a2b0382c3`. The after run is
[#1537 / 37857741876](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37857741876)
at the accepted final implementation head. All three shards succeeded. Before
ran 1,516 passing cases; after ran 1,528, with zero failures and zero skips in each.
The additional cases exercise streaming, cleanup, fixture bindings and cache
invalidation; no old test file was removed.

The longest complete PR job was 1,091 seconds before and 1,045 after. Longest TAP
execution was 557.630358965 seconds before and 489.306153952 after. The seven-case
control was 417.368177482 seconds before and 419.849496345 after: **no end-to-end
speedup of this scientific test is claimed**. Earlier local alternating fixture
preparation trials establish byte-equivalent cheaper preparation, not a faster
world reconstruction. The full job includes checkout/restoration/build overhead
that does not appear inside TAP; step totals must not be added to TAP as if every
measurement were disjoint.

The before normal queue is [37851051485](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37851051485).
The after normal queue is [37859632825](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37859632825),
which tested the combined tree `4134cbe8ac5cf433b2f2c94949236b064bc42114`
against main `19ca4765a6de436f868742279f86f1f4e340e289` and accepted the merge.
Longest integration job was 1,055 seconds before and 996 after. After again passed
1,528 cases with zero failures/skips. Its seven-case semantic control took
418.73603797 seconds; the separate whole-world positive took 97.406376056 seconds.
These are observed critical-path reductions in one PR and one queue comparison,
with different hosts and surrounding changes, not statistically isolated causal
speedups or a guarantee. Setup and semantic validation remain substantial.

`hosted-verification.json` retains job IDs, steps, outcomes, per-shard timings,
longest cases, complete seven-phase lines and raw-log hashes. Reviewers can fetch
the identified actual logs independently while GitHub retains them. The phase
lines appeared at distinct times during the seven-minute control, before its
completion; selected files and final TAP timings identify other active work.
Inner wrappers that still buffer subprocess output remain a stated limit.

## GitHub API, observer and local resource costs

The owner's additional requests on issue comments 6026252116 and 6026388069 are
included in `api-and-observer-costs.json`. The actual queue records REST attempts
per phase: registration 4, scheduling 12, preparation 99 and final merge 106, including the result-comment notification.
The pre-notification testing/accepted receipt bodies show 98 and 105 respectively;
these are distinct accounting points, not inconsistent runs.
Preparation used 42 immutable-metadata requests and one immutable-blob request;
final merge used 26 and one respectively. Batched immutable transport and bounded
per-phase caching coexist with fresh mutable ownership, contract, review, head,
base, checks and complete pagination. Six candidate-refresh attempts were needed
for the real combined object; they are not local five-second observation polling.
The run's capacity receipt reported sufficient capacity. Recorded phase status
counts contain no quota rejection. Admission `waited_ms` includes HTTP observation
latency, so it is not reported as quota-induced sleep. Separate quota-sleep counters
for the earlier phases were unavailable; this component is explicitly unmeasured
and assigned to #1543's bounded setup-observability acceptance.
No new API/quota speed improvement is attributed to this CI harness PR; the existing
bounded transport/observer safeguards remain in force.

The original submission observer ended after 1,351.071 seconds with nine reads
and one registration submission. That includes queue execution, adaptive sleeps
and observation lag; it is not CPU time. A separately executed actual read-only
accepted-state observer used three reads and zero writes, took 2.07 seconds wall
time, 0.22 seconds user CPU and 0.07 seconds system CPU, with 52,363,264 bytes maximum
RSS and 17,669,312 bytes peak footprint. It verified both the authoritative receipt
and actual merged PR state, requested no cleanup and touched no other checkout.
This short probe does not estimate memory for the entire queue or other workers.
The observed authenticated local response retained actual remaining/reset/resource
headers; those belong to the local credential, separately from the Actions token.

Additional 38 real client/entrypoint controls passed without skips
(`observer-controls.log`), including actual reset/deadline handling, stale or
missing receipts, uncertain submission, pagination and owned cleanup. The existing
observer doubles from one-minute waits to five minutes with jitter, stops at its
bound, and stops rereading successful registration after its durable request is
seen. It preserves HTTP quota/reset diagnostics when rejected; no rejection was
fabricated just to create a live quota example.

The first packet preserves observed complete-world local RSS/footprint and managed
storage measurements. This report's author slot stayed within the shared storage
check and uses small derived metadata, not another world copy. Host storage and
scientific-kernel peaks are separate from the accepted-state observer resource
probe. Evidence can identify remaining setup cost without authorizing the removal
of freshness, hashes, complete inventories or rejection guards.

## All lanes, selection and remaining opportunities

`inventory-assessment.json` reads the complete current test roster, direct imports
and representative declared protections. The first packet retains standalone
Python/browser support and every workflow entry point. This is a categorized
assessment of avoidable work, not reproduction of every historical defect.

- Source-only geography: retain the exact owned-path/reservation evidence roster
  and trusted source/evidence/geography gates. Benchmark the entire checks, not
  just the shortest regression job. No measured justification was found to remove
  another substantive gate. Actual post-implementation evidence is recorded below.
- History: meaningful campaign-directory controls exercise the real PR and queue
  selectors, reject foreign namespaces/rename origins and preserve the focused
  roster. No dummy campaign or provider/import operation was created to benchmark
  a future lane.
- Documentation and coordination: audited own-packet/docs selection remains
  focused. Unknown paths, sensitive helpers/workflows and missing classification
  require sufficient coverage; invalid ownership/incomplete inventories reject.
- Application/browser/build/package: retain real export/browser/worker and
  immutable asset equivalence. The build runs only where the selected shard needs
  it; undeclared builder reads and imports reject against the single package-input
  declaration. Setup remains measured optimization opportunity #1543.
- Database/migrations: retain source history, identity, staging and constraint
  controls; their measured long cases are preserved. Operator workflows were
  inventoried without live writes or database/provider experiments.
- Scientific/evidence: preserve exhaustive proofs and all adverse semantic
  controls. Further repeated world-validation optimization is bounded issue #1544,
  requiring real profiling and independent equivalence, rather than arbitrary
  timeout increases or sampled substitutes.
- Queue/classification/authority: retain FIFO/exact-tree/main/head/review guards.
  Registration, queue waiting and API overhead are separate from test runtime.

The fresh managed checkout ran 105 runner/profile/proof/restoration/cleanup tests,
all passing without skips (`selection-tests.log`). Initial local failures were
missing sparse inputs; those original files were included before the successful
rerun. The additional 19 package/deployment controls passed without skips in the
prior admitted author slot (`package-history-tests.log`). They exercise actual
sandboxed build read/import denial, approved input promotion, unknown/missing
metadata and focused source/history selection; they do not certify factual data.
The previous packet preserves the independent complete-custody/cache probes.

#1543 and #1544 own distinct broader setup and semantic-kernel redesigns allowed
by the original bounded scope. They preserve this implementation and the original
scientific guarantees. They wait on completion of #1201 and are reassessed before
readying; neither is automatically ready merely because its dependency closes.

## Geography hosted verification

Before geography PR #1512 ran focused regression in 12 seconds and an inapplicable
package job in 4 seconds; its required evidence gate took 68 seconds. Its normal
queue [37854544663](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37854544663)
ran focused integration in 12 seconds and geography in 19 seconds.

After, the normal queue for geography PR #1542
[37862050812](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37862050812)
used the new main implementation as tested base and accepted the combined tree.
Focused integration took 10 seconds, with 207 passing cases and zero failures/skips;
geography took 17 seconds. This is actual post-implementation queue execution,
even though the authored #1542 branch was created before the implementation merge.

Fresh geography PR #1548 based on the implementation merge separately ran the
new runner in [37862286946](https://github.com/ChengshuLi/WorldAtlas/actions/runs/37862286946).
Focused regression took 12 seconds, passed the same 207 cases with zero
failures/skips, and used the same complete audited file roster. Package, scope,
profile, classify and geography passed. Its independent evidence gate **failed**
with “Incomplete changed-file receipts”; the original worker must repair its
packet before merge. This report neither calls that PR green nor weakens the gate.
The conditional initial-foundation job is inapplicable, distinct from zero skipped
cases in the actual selected regression.

`geography-verification.json` retains all observed check outcomes, steps, actual
heads/bases/candidate/merge and log hashes. Source-only regression still skips
application installation/build, browsers and worldwide restoration. Different
packets may have different trusted evidence costs; a fast regression is not a
promise that the complete pipeline always finishes in that time. Meaningful
history/unknown/rename controls and package sandbox probes independently cover
selection without inventing research data.

## Limits and disposition

No deployment, content import, scientific approval, provider mutation or completed
historical repair is claimed. One-run comparisons do not establish stable latency.
Full-source factual review remains independent of machine checks. Original bytes
and prior evidence are retained. Managed author/review slots are released after
durable evidence and verified merge; only owned scratch is removed.

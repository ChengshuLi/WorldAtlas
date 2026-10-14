# Bounded CI input checkout

The full application acquisitions in `merge-integration-checks.yml` (regression
and the selected-data package route) and `worker-merge.yml` (integration) use
`scripts/acquire-ci-checkout.py` after its source is authenticated from the exact
trusted base. Evidence-only sparse checkouts, geographic readers, test selection,
package producers, artifact uploads and merge policy retain their existing roles.
The complete software-regression route omits two unconsumed source-only namespaces
from its input download; complete regression still means every original test runs.

The author workflow is a `pull_request` workflow. Its workflow SHA can include
candidate changes, so the acquisition helper is obtained from
`github.event.pull_request.base.sha`. The queue uses the base emitted by trusted
preparation. Bootstrap authenticates the base commit, path/tree entry, ordinary
file mode and Git blob hash before executing the helper from a private temporary
directory. Only proven helper absence in that trusted tree retains the original
pinned checkout action during initial rollout. Failed authentication, unavailable
transport, malformed metadata or a broken existing helper never select that
legacy route. Candidate helper code is never a bootstrap fallback.

## Invocation and authority

```sh
python3 "$AUTHENTICATED_HELPER" \
  --repository ChengshuLi/WorldAtlas \
  --sha "$EXACT_CANDIDATE_SHA" --tree "$AUTHENTICATED_TREE_SHA" \
  --workspace "$GITHUB_WORKSPACE" \
  --total-timeout-seconds 420 --elapsed-seconds "$BOOTSTRAP_ELAPSED_SECONDS"
```

The workflow obtains the candidate's tree from the exact immutable Git commit
metadata. Both identifiers must match the fetched commit and checked-out tree.
The workspace must be an existing empty ordinary absolute directory. The helper
rechecks its device/inode, absence of symlinks and emptiness immediately before
atomic same-filesystem replacement. Preexisting or newly arriving foreign files
are preserved. Acquisition uses one private sibling repository; terminal cleanup never removes
the workspace. No phase discards a progressing download and starts another repository.

The dedicated `WORLDATLAS_CHECKOUT_TOKEN` environment variable is removed from
the helper environment immediately. Only acquisition fetch/materialization children receive authentication,
through transient Git configuration environment entries. Tokens are not included
in arguments, repository configuration, receipts or progress output. Verification inherits an allowlisted environment without authentication;
ordinary full checkout materialization remains credential-free. Global and
system Git configuration, template hooks, credential helpers and LFS smudge are
disabled. No submodules are acquired. Both routes remain normal Git repositories with a detached exact HEAD,
depth-one history and unchanged included file modes/content. They are not
reconstructed from an archive or file API.

## Complete software-regression inputs

The final queue integration acquisition step supplies its existing
trusted `INTEGRATION_PROFILE` and `INTEGRATION_TEST_SELECTION` outputs. Only
`full` plus `complete` enables the sparse input download. Standalone package and
selected-data acquisitions retain the full tree. An older authenticated base helper
ignores these environment values, so initial integration safely retains the old
full acquisition; the candidate helper never becomes a credentialed fallback.

The sparse route includes the whole current tree except `data/regional-review/`
and `research/campaigns/`. These are source-only owned lanes: the ordinary software
suite uses their namespace strings in ownership tests and creates its own fixtures,
but does not read their real current packet bodies. Actual application data,
engineering archives, the current test inventory and consumed `research/geography/`
remain included. The package-input control fails if either omitted namespace
becomes a required package/verification input. A new real consumer must revise
this audited input boundary rather than silently hydrate absent source data.

Git first fetches the exact depth-one commit and complete tree metadata with
`--filter=blob:none`. Sparse checkout then obtains the selected missing blobs within
the same supervised total deadline, using transient authentication. Global/system
configuration, hooks, credential helpers and LFS smudge remain disabled. No candidate
code runs. The helper disables the origin's promisor behavior and removes its
partial-clone filter before promotion, preventing later implicit downloads.
The existing explicit native regression commit fetch remains unchanged; included
historical input paths can obtain their unique old bytes. An excluded source-only
historical blob is not promised as a software input, and a plain commit fetch is
not proof that every omitted blob became available.

At accepted main `ecb837c599544ff8462b50f43a678d60c80fa5f6`, complete Git tree
metadata contains 31,905 files / 13,068,725,465 raw file bytes. The two exclusions
remove 5,131 worktree files and 3,955 unique blobs / 2,254,479,257 distinct blob
bytes, approximately 24.8% of unique source bytes. Shared blobs needed elsewhere
are retained. These numbers describe input selection, not compressed wire traffic
or measured throughput; a later ordinary adopted CI run must establish real timing.
No checkout artifact/cache framework or altered test selection is introduced.

## Overall deadline and cleanup

One monotonic total budget includes the supplied bootstrap elapsed time, fetch,
selected blob acquisition/checkout, identity checks and terminal cleanup. A progressing fetch has no separate
cutoff and is not restarted in a fresh repository. The workflow default remains
420 seconds. The helper accepts a finite total budget up to 1,800 seconds, with
bootstrap elapsed time below it. The 30-minute implementation ceiling remains a
runaway-acquisition safeguard, below the existing 35-minute queue job limit; it is
not an additional job allowance. A trusted caller must choose its budget within
its job deadline and leave time for subsequent work. The author and package job
limits remain 25 and 30 minutes. Invalid, nonfinite, spent or oversized budgets
refuse before staging. The supervisor reserves time inside the total budget for
termination and cleanup. Command failure, wrong commit/tree, failed checkout,
changed workspace, cancellation or unverifiable process cleanup ends acquisition
without restarting acquisition.

Each command starts a new process session. SIGINT/SIGTERM and deadlines trigger
bounded TERM/KILL escalation, direct-child reaping and verification that no live
group member remains. A zombie has no execution capability and is distinguished
from a live descendant. If termination cannot be verified, the helper fails,
preserves its private staging directory and reports that limitation. It does not
delete files beneath a possibly live process. SIGKILL, runner loss, kernel stalls
and processes that deliberately escape the owned session cannot be guaranteed
cleaned by user-space supervision; runner teardown remains the final isolation
boundary. No candidate code runs during acquisition.

The retained 420-second total budget is an operational bound informed by sampled
successful full checkouts (117–292 seconds) and directly inspected fetches
(approximately 80–220 seconds). The incident fetch lasted 1,595.528 seconds before
succeeding. These observations establish neither its root cause nor a performance
percentile. The overall deadline can still reject a healthy slow transfer; this
helper does not discard progress to restart it within that same budget. The existing
25/30/35-minute job limits are not increased, and successful acquisition does not promise that later tests finish within them.

## Observation and verification

JSON lines report phase, status, elapsed/remaining seconds and allowlisted
numeric Git progress. Fetch explicitly requests `--progress`. Raw Git stderr,
trace files, HTTP headers and arbitrary command output are never emitted. Git
progress describes the reported operation; it does not independently measure
network bytes or establish whether a delay was server packing, transport, local
object processing or disk work. No unobserved interval is labeled idle time.

The workflow retains one canonical successful checkout verification step under
the existing proof-consumer name, following either authenticated acquisition or
the initial legacy path. That step checks the actual detached HEAD, tree, origin
and absence of credential configuration. Build/tests begin only after success.
A failed acquisition does not dispatch another workflow or rerun completed
scientific checks.

Run the lightweight controls with Node 24 and Python 3.7 or newer:

```sh
GIT_NO_LAZY_FETCH=1 node --test test/ci-checkout.test.mjs
```

The tests use tiny real local Git repositories and controlled subprocess failures,
including filtered sparse inputs, explicit historical input fetch, a TERM-resistant
child/grandchild during fetch or materialization, cancellation, unobservable cleanup,
wrong immutable identities, foreign workspace contents and secret-bearing stderr.
Process inspection must be permitted for the actual cleanup controls; denial is
a failed/unverified test, not a reason to omit its assertions. Hosted adoption and
throughput require measurements from a later normal workload using the new path.

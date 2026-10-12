# Bounded full CI checkout

The full application acquisitions in `merge-integration-checks.yml` (regression
and the selected-data package route) and `worker-merge.yml` (integration) use
`scripts/acquire-ci-checkout.py` after its source is authenticated from the exact
trusted base. Evidence-only sparse checkouts, geographic readers, test selection,
package producers, artifact uploads and merge policy retain their existing roles.

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
  --fetch-timeout-seconds 240 --total-timeout-seconds 420 \
  --max-attempts 2 --elapsed-seconds "$BOOTSTRAP_ELAPSED_SECONDS"
```

The workflow obtains the candidate's tree from the exact immutable Git commit
metadata. Both identifiers must match the fetched commit and checked-out tree.
The workspace must be an existing empty ordinary absolute directory. The helper
rechecks its device/inode, absence of symlinks and emptiness immediately before
atomic same-filesystem replacement. Preexisting or newly arriving foreign files
are preserved. Every attempt uses a fresh private sibling repository; cleanup
never removes the workspace to make a retry possible.

The dedicated `WORLDATLAS_CHECKOUT_TOKEN` environment variable is removed from
the helper environment immediately. Only the fetch child receives authentication,
through transient Git configuration environment entries. Tokens are not included
in arguments, repository configuration, receipts or progress output. Checkout and
verification inherit an allowlisted environment without authentication. Global and
system Git configuration, template hooks, credential helpers and LFS smudge are
disabled. No submodules are acquired. The full checkout remains a normal Git
repository with a detached exact HEAD, depth-one history and unchanged tracked
file modes/content; it is not reconstructed from an archive or file API.

## Deadlines, retries and cleanup

One monotonic total budget includes the supplied bootstrap elapsed time, all
attempts, checkout, identity checks and cleanup. Each fetch is additionally limited
to 240 seconds. At most two fetch attempts run. These workflow defaults are
configurable: the helper accepts a finite total budget up to 1,800 seconds, with
the fetch limit no greater than that total and bootstrap elapsed time below it.
The 30-minute implementation ceiling is a broad runaway-acquisition safeguard,
below the existing 35-minute queue job limit; it is not a measured transfer
threshold or additional job allowance. A trusted caller must choose its budget
within its own job deadline and leave time for subsequent work. The author and
package job limits remain 25 and 30 minutes. Zero/negative/nonfinite budgets,
values beyond those relationships or the safety ceiling, and attempt counts
outside one or two refuse. The helper reserves time
inside the total budget for termination and cleanup, and may refuse another
attempt when the remaining budget is insufficient.

Only failed or timed-out fetches are retryable. Wrong commit/tree, failed checkout,
invalid configuration, changed workspace, cancellation or unverifiable process
cleanup refuse without another fetch. A retry starts only after the prior owned
process group has stopped and its partial repository has been removed.

Each command starts a new process session. SIGINT/SIGTERM and deadlines trigger
bounded TERM/KILL escalation, direct-child reaping and verification that no live
group member remains. A zombie has no execution capability and is distinguished
from a live descendant. If termination cannot be verified, the helper fails,
preserves its private staging directory and reports that limitation. It does not
delete files beneath a possibly live process. SIGKILL, runner loss, kernel stalls
and processes that deliberately escape the owned session cannot be guaranteed
cleaned by user-space supervision; runner teardown remains the final isolation
boundary. No candidate code runs during acquisition.

The 240/420-second initial settings are operational bounds informed by the sampled
successful full checkouts (117–292 seconds) and directly inspected fetches
(approximately 80–220 seconds). The incident fetch lasted 1,595.528 seconds before
succeeding. These observations establish neither its root cause nor a performance
percentile. Bounds can reject a healthy slow transfer; a retry may fail or exhaust
the remaining budget. The existing 25/30/35-minute job limits are not increased,
and successful acquisition does not promise that later tests finish within them.

## Observation and verification

JSON lines report phase, attempt, status, elapsed/remaining seconds and allowlisted
numeric Git progress. Fetch explicitly requests `--progress`. Raw Git stderr,
trace files, HTTP headers and arbitrary command output are never emitted. Git
progress describes the reported operation; it does not independently measure
network bytes or establish whether a delay was server packing, transport, local
object processing or disk work. No unobserved interval is labeled idle time.

The workflow retains one canonical successful checkout verification step under
the existing proof-consumer name, following either authenticated acquisition or
the initial legacy path. That step checks the actual detached HEAD, tree, origin
and absence of credential configuration. Build/tests begin only after success.
Acquisition retries do not dispatch workflows, revive settled tickets or rerun
completed scientific checks.

Run the lightweight controls with Node 24 and Python 3.7 or newer:

```sh
GIT_NO_LAZY_FETCH=1 node --test test/ci-checkout.test.mjs
```

The tests use tiny real local Git repositories and controlled subprocess failures,
including a TERM-resistant child/grandchild, cancellation, unobservable cleanup,
wrong immutable identities, foreign workspace contents and secret-bearing stderr.
Process inspection must be permitted for the actual cleanup controls; denial is
a failed/unverified test, not a reason to omit its assertions. Hosted adoption and
throughput require measurements from a later normal workload using the new path.

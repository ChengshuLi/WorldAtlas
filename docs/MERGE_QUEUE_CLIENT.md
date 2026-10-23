# Submit and observe the native Actions merge queue

After the exact PR head has passed its applicable checks and independent review,
submit directly to the trusted main workflow. Generate a fresh request ID for a
new submission and record it with the PR number and reviewed head on the original
issue before dispatch. Request IDs contain 16–100 ASCII letters, digits or hyphens.
For example, use a UUID:

```sh
REQUEST_ID="$(node -e 'console.log(require("node:crypto").randomUUID())')"
gh workflow run worker-merge.yml --repo ChengshuLi/WorldAtlas --ref main \
  -f pr_number=PR-NUMBER -f expected_head=EXACT-REVIEWED-HEAD \
  -f request_id="$REQUEST_ID"
```

Replace the PR and head placeholders. A successful dispatch is only submission,
not a completed merge. The workflow's top-level `worldatlas-main-integrate`
concurrency group uses `cancel-in-progress: false` and `queue: max` to serialize
its entire preparation, isolated candidate tests and final merge lifecycle.
GitHub can retain up to 100 pending runs in that group; additional runs are cancelled.
Order follows when runs begin waiting, not their dispatch time. See the
[official concurrency documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency).
There is no separate registration, FIFO-ticket store, scheduler, wake notifier or
custom observation client. Research, PR checks and independent review can continue
while native Actions holds pending merge runs.

## Submit reviewed consumers without rebuilding the request

When the review identifies a bounded consumer roster, use the existing
`reviewedTestPlan` in the actual accepted `scripts/merge-integration.mjs` with the
exact accepted base, reviewed head, candidate tree, changed files and package
input definition. Its `request` contains that validated pair and the normalized
consumer list, including mandatory packaged consumers. Serialize
`JSON.stringify(plan.request)` directly as the dispatch's `reviewed_tests` value,
and pass that exact serialized value back through `reviewedTestPlan` with the
same current context before recording a request or dispatching it. Do not
serialize `plan.files`, reconstruct the pair, or send the full derived plan.

The reviewed roster remains human-selected review scope, not an automated
sufficiency certificate. Inputs, checkout patterns, build and geography duties
remain independently derived and revalidated by trusted preparation and final
admission. A changed base or head requires review of the new pair, not silently
rebinding the old argument. Without a reviewed argument, ordinary automatic
routing remains unchanged. This is direct use of the existing planner and native
workflow, not a separate dispatch client.

## Find the execution and inspect its outcome

Use ordinary GitHub CLI commands and match the exact request ID in the displayed
run title. Record the matching numeric run ID and URL alongside the request.
Designate one observer for that execution; other workers reuse its observations
and terminal receipt rather than starting duplicate status or discovery loops.

```sh
gh run list --repo ChengshuLi/WorldAtlas --workflow worker-merge.yml \
  --branch main --event workflow_dispatch --limit 100 \
  --json databaseId,displayTitle,status,conclusion,url,createdAt
```

Once the run is known, routine observation needs only its exact status endpoint:

```sh
gh api --cache 60s repos/ChengshuLi/WorldAtlas/actions/runs/RUN-ID \
  --jq '{id,status,conclusion,run_attempt,html_url}'
```

Space routine reads at least a minute apart, or longer while no useful phase
change is expected. The native CLI cache avoids repeated identical reads within
that minute; it is not fresh merge authority. Do not combine this with repeated
run listing, full logs, `gh run view` or another watcher. Inspect exact jobs when
needed to diagnose a changed phase or detect that the final merge finished before
the aggregate run:

```sh
gh api --cache 60s 'repos/ChengshuLi/WorldAtlas/actions/runs/RUN-ID/jobs?per_page=100' \
  --jq '{total_count,jobs:[.jobs[]|{id,name,status,conclusion}]}'
```

If `total_count` exceeds the returned roster, follow pagination for that inspection;
do not infer absence from an incomplete page. For an interactive view, use one
`gh run watch RUN-ID --repo ChengshuLi/WorldAtlas --interval 60 --exit-status`
instead of the status loop. Never use its default three-second interval for
background observation. In CLI v2.102.0 each refresh reads the run, workflow and
jobs, plus annotations for uncached active jobs; `--compact` changes display, not
that request pattern. See the [official command](https://cli.github.com/manual/gh_run_watch)
and [versioned implementation](https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/run/watch/watch.go).

After the final merge job succeeds, verify actual PR state without `--cache`:

```sh
gh api repos/ChengshuLi/WorldAtlas/pulls/PR-NUMBER \
  --jq '{merged, head: .head.sha, merge_commit_sha, state, html_url}'
```

A bounded list can omit older runs: absence from one page is not proof that
submission failed. Search the relevant time window and paginate Actions history
only when discovery or uncertain-dispatch reconciliation needs it, not on each
status read. An interrupted observer or disconnected terminal does not cancel
the workflow. Resume observation of the same known execution rather than
dispatching another request. If a submission response is uncertain, reconcile
existing executions and current PR state first; never blindly redispatch.
Reruns retain the original preparation and exact candidate; they cannot bypass
missing or failed candidate checks.

Read the workflow jobs, logs and canonical bot result comment for diagnostics.
`gh run view RUN-ID --log` retains the complete result even if notification fails;
retrieve it once when needed and reuse it. No duplicate diagnostic result artifact
is produced. Reuse exact immutable Git objects already present locally and the
documented missing-object transport instead of repeating body-by-body source
acquisition while observing an unchanged run.
A green workflow, candidate SHA or bot comment alone does not establish a merge.
Fresh PR API state must have `merged: true`, `.head.sha` equal to the exact reviewed
head, and a nonempty `.merge_commit_sha`. Retain that actual squash commit and the
execution URL in the issue checkpoint. Unavailable or mismatched actual PR state
is unresolved, even if a local observer or result comment reported success.
As soon as the final merge job is green, perform that PR readback: an Actions
aggregate can remain in progress after its final job and actual merge finish.
Do not hold the next ready delivery waiting only for that aggregate watch.

For a settled failed or cancelled execution, inspect its cause and actual PR state.
If preparation succeeded, the PR remains open at its same reviewed head, main is
still the tested base and no execution remains live or unresolved, retry the failed
jobs of that execution:

```sh
gh run rerun RUN-ID --repo ChengshuLi/WorldAtlas --failed
```

Successful jobs and their original artifacts remain valid for that exact candidate,
even after its disposable branch is cleaned up. The final job still rechecks the
immutable candidate's parents/tree, current main/head, review, checks and original
successful geographic producer. For a report freshly authenticated from that
main-run producer, final verification reuses preparation's exact reviewed-byte
comparison through private immutable producer bindings; it does not download both
whole trees again. Ordinary, historical and supplied reports retain the original
comparison. Selected-data qualification still reads its authored/baseline roles.
Artifact uploads are attempt-qualified; no prior
evidence is overwritten. Use a fresh request and dispatch if preparation failed,
main/head changed or the execution predates attempt-qualified uploads. Changed
reviewed bytes need fresh substantive review. A pending run, uncertain dispatch or
missing result is not a settled failure. No new recovery daemon is involved;
existing API quota/deadline guards and native provider queueing still apply.

On a rate-limit rejection, use the response's existing headers rather than polling
`/rate_limit`. Exhausted primary capacity (`x-ratelimit-remaining: 0`) requires
waiting past `x-ratelimit-reset`; `retry-after` must also elapse when supplied.
For a confirmed secondary-only rejection without either delay, wait at least a
minute and increase the wait on further rejection. Stop rather than retry an
ordinary permission error or ambiguous mutation. Do not switch credentials to
work around a limit. The accepted shared client keeps bounded read retries and
conditional ETag revalidation; its phase receipts count its own actual attempts,
not every CLI or integration request made by the account. Keep Actions-token and
user-token accounting separate. See GitHub's
[rate-limit handling guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api#handle-rate-limit-errors-appropriately).

## Release the owned workspace

After actual merge verification, preserve all required evidence and unique scratch,
stop processes using the checkout, and explicitly release its managed slot with
the existing ownership token through the task-bound helper described in
[LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md#finish-and-release). Do not select a
helper from an ambient primary checkout. GitHub CLI observation performs no automatic local cleanup. Reconcile
the original issue and preserve historical claims, then allocate the next job from
fresh main. Settle any retained live-operation reservation through its workflow. A cleanup failure does not invalidate an already verified
merge. Observing or retrying grants no new review, science, publication or provider
permission.

In the final delivery handoff, state the actual local cleanup outcome described in
[Finish and release](LOCAL_WORKSPACES.md#finish-and-release), including any retained
or blocked cleanup and its responsible next action. The queue's remote head and
candidate cleanup results do not establish local workspace cleanup.

## Transition from the retired scheduler

Before native direct submissions, the coordinating integrator must enumerate and
settle old scheduler and worker runs, including queued, requested, waiting,
pending and in-progress states. Already-running workflows retain their original
definition. Preserve old request IDs, exact heads, run links and terminal receipts
on their original issues. Do not cancel the in-flight #1810 work to accelerate this
migration. Reconcile old ambiguous writes or registrations before deciding whether
an unchanged-head request needs a new native dispatch; do not replay all old
registrations automatically. Worker authors do not independently toggle shared
workflow availability. See [WORKER_COORDINATION.md](WORKER_COORDINATION.md).

## Retained historical observation evidence

The retired custom observer's controlled fake-clock tests reproduced a 210-second
terminal delay with nine reads, then detected the same synthetic completion after
30 seconds using 22 reads (four changed 200 responses and 18 authenticated 304s).
An unchanged 65-minute observation used 66 reads (two 200s and 64 304s). These were
deterministic controls, not measured hosted speedups or the native CLI's behavior.

For the #1789 incident, GitHub merged at 10:33:27 UTC and posted its accepted receipt
at 10:33:30. The retained local file's final mtime was 10:36:56.207344 UTC. The
209.207-second merge-to-file difference (206.207 seconds from receipt creation)
is cross-clock and can include buffering, final verification and cleanup. The old
log has no per-poll timestamps. Its nine reads and 1,339,924 ms wall-clock runtime
support the deterministic capped-polling mechanism but do not isolate historical
sleep time or establish saved delivery time. Subsequent adoption of that retired
observer was tracked in [issue #1791](https://github.com/ChengshuLi/WorldAtlas/issues/1791).

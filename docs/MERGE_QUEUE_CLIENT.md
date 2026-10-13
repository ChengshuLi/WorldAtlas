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

## Find the execution and inspect its outcome

Use ordinary GitHub CLI commands and match the exact request ID in the displayed
run title. Record the matching numeric run ID and URL alongside the request.

```sh
gh run list --repo ChengshuLi/WorldAtlas --workflow worker-merge.yml \
  --branch main --event workflow_dispatch --limit 100 \
  --json databaseId,displayTitle,status,conclusion,url,createdAt
gh run view RUN-ID --repo ChengshuLi/WorldAtlas
gh run watch RUN-ID --repo ChengshuLi/WorldAtlas --exit-status
gh api repos/ChengshuLi/WorldAtlas/pulls/PR-NUMBER \
  --jq '{merged, head: .head.sha, merge_commit_sha, state, html_url}'
```

A bounded list can omit older runs: absence from one page is not proof that
submission failed. Search the relevant time window and paginate Actions history
when needed. A `gh run watch` timeout, interrupted local process or disconnected
terminal does not cancel the workflow. Resume `gh run view`/`gh run watch` for the
same execution rather than dispatching another request. If a submission response
is uncertain, reconcile existing executions and current PR state first; never
blindly redispatch. Do not use workflow reruns to bypass a settled failure's
preparation or exact-candidate checks.

Read the workflow jobs, logs and retained result comment/artifact for diagnostics.
A green workflow, candidate SHA or bot comment alone does not establish a merge.
Fresh PR API state must have `merged: true`, `.head.sha` equal to the exact reviewed
head, and a nonempty `.merge_commit_sha`. Retain that actual squash commit and the
execution URL in the issue checkpoint. Unavailable or mismatched actual PR state
is unresolved, even if a local observer or result comment reported success.

For a settled failed or cancelled execution, inspect its cause and actual PR state.
Only after confirming the PR remains open at the same reviewed head and no prior
execution remains live or unresolved may a corrected retry use a fresh request ID
and a new dispatch. Changed heads or reviewed bytes require fresh substantive
review. A pending run, uncertain dispatch or missing result is not a settled
failure. There is no automatic redispatch, queue-capacity engine or cross-run
recovery daemon; existing API quota/deadline guards still apply within the workflow.
Native provider queueing and runner availability are external limits; overflow and
provider failures remain visible and require this same reconciliation.

## Release the owned workspace

After actual merge verification, preserve all required evidence and unique scratch,
stop processes using the checkout, and explicitly release its managed slot with
the existing ownership token:

```sh
node scripts/local-workspace.mjs release --worker YOUR-WORKER-ID --slot work \
  --token EXACT_RETURNED_TOKEN
```

Follow [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md) for clean-workspace guards and
owned release. GitHub CLI observation performs no automatic local cleanup. Reconcile
the original issue and preserve historical claims, then allocate the next job from
fresh main. Settle any retained live-operation reservation through its workflow. A cleanup failure does not invalidate an already verified
merge. Observing or retrying grants no new review, science, publication or provider
permission.

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

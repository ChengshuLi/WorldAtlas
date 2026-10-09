# Submitting and observing a merge request

Submit a new reviewed PR once:

```sh
node scripts/queue-pr-merge.mjs --pr PR-NUMBER --head EXACT-REVIEWED-HEAD
```

Retain the printed request ID on the original issue checkpoint. Identity is printed
before submission, including when the submission's outcome is uncertain. `submitted`
means dispatch returned; `registered` means the bot's durable request was read. Neither
means the PR merged. The GitHub scheduler owns execution and recovery independently
of the worker's observer. Registration and execution retain their existing rules.

Resume an existing request without submitting it again:

```sh
node scripts/queue-pr-merge.mjs --pr PR-NUMBER --head EXACT-REVIEWED-HEAD \
  --request-id EXISTING-ID --observe
```

Supplying an existing request ID never automatically resubmits an absent registration.
An uncertain write may still have succeeded. Inspect its registration/run/comment
before deciding what action is justified; an observation timeout is not cancellation
or evidence that the request is live. A failed registration is reported explicitly.
Incomplete registration searches or comment pagination fail safely.

The trusted registration job separately binds its retries to the current job's
actual start and five-minute workflow timeout. A wait must leave room for the next
HTTP attempt and refusal/accounting. It reports quota/deadline refusal under the
same request identity and fails the registration job; that failure cannot imply a
successful durable request or trigger a duplicate submission. Timing metadata is
one bounded, non-retried current-attempt Actions jobs read. An unavailable timing
authority refuses before queue writes. Inspect the actual workflow/result before
an authorized retry, especially after an uncertain POST. The ten-minute scheduler
uses its own corresponding job budget; local observation retains its separate
65-minute deadline.

The observer uses one-minute then two/four/five-minute waits with bounded jitter.
Once the durable request exists, it reads result comments rather than repeatedly
checking PR state or successful registration. Complete pagination remains required.
An observation ends after at most 65 minutes, with each API subprocess bounded to 20
seconds or the remaining deadline. Pending observation returns exit 3; rejected
merge receipts exit 2; confirmed accepted merge receipts exit 0. Permission/malformed
responses fail; these are not merge outcomes. Slow/in-flight responses cannot extend
the deadline and authorize a later action.

Primary API exhaustion waits for the actual response's reset time. Secondary limits
honor retry-after, otherwise wait at least one minute with exponential retries, at
most three across the observer. A primary reset is applied only when primary quota
is exhausted. This follows [GitHub’s rate-limit guidance](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api). Ordinary permission denial is not retried as throttling. All reads,
including pagination and final merge verification, follow these rules. Uncertain
submission writes are never automatically repeated. Read-only observation writes
no GitHub state and does not clean up local files.

Successful observation freshly checks actual merged state, exact reviewed head and
merge commit against the bot receipt. A missing/mismatched receipt or failed actual
read cannot authorize success or cleanup. Initial submission retains the existing
automatic owned-workspace cleanup only after this verification. To recover cleanup
after an interrupted worker, preserve evidence/unique scratch and stop processes,
then explicitly request the same verification plus the existing owned cleanup:

```sh
node scripts/queue-pr-merge.mjs --pr PR-NUMBER --head EXACT-REVIEWED-HEAD \
  --request-id EXISTING-ID --observe --cleanup
```

Cleanup still enforces reviewed-head, checkout ownership and clean-workspace guards;
a cleanup failure does not invalidate a verified merge. Release/reconcile the issue
claim through the normal workflow. No queue, review, science, publication or provider
permission is granted by observing a request.

The request budget control simulates time and counts actual API function invocations.
It does not measure hosted CI latency or promise that unrelated API clients cannot
exhaust shared limits. Large comment inventories require more than one read per poll.
The existing scheduler's five-minute schedule and completion trigger remain unchanged.

Scheduler admission checks out the executing `github.workflow_sha`, binds its
commit and workflow path/ref to GitHub’s current job environment, and reads the
timeout from that immutable Git blob. A newer main commit cannot extend an
already-running job’s timeout; mixed-vintage checkouts refuse before API work.

Draft readiness is a metadata transition. It refreshes current ownership, contract, evidence and scope without canceling or repeating the unchanged head's code tests. Opening, synchronizing or reopening still starts code validation. Before submission, verify the head's code checks and independent review are complete; a successful metadata run does not replace missing or failed code proof. The queue continues to validate the exact integration candidate.

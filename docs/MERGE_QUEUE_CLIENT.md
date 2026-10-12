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

The ordinary CLI and automatic delivery use the same bounded authenticated
conditional-read adapter. It retains in-memory ETag snapshots through the existing
64 MiB / 128-entry cache and revalidates every result-comment page. A snapshot
alone never establishes current authority; an unbound/mismatched 304, failed read,
or lost response cannot report success. The adapter handles gh's actual complete
304 / exit-1 response while still refusing killed/timed-out subprocesses.

With cacheable result pages and usable core quota signals, normal waits stay at
the existing one-minute floor plus 0–10% jitter, rather than growing with CI age.
The observer honors longer X-Poll-Interval, Cache-Control max-age and Retry-After
signals. It also paces pages against observed remaining quota/reset, preserving
the existing 16-call recovery allowance; that allowance is not reserved against
other clients. Missing cache/quota support retains the conservative one/two/four/
five-minute fallback. Every page is still read, in sequence. No extra quota probe,
workflow-watch process, webhook registration or repeated submission is introduced.

Under healthy one-page observations, no longer provider interval and sufficient
quota, the sleep contribution to terminal detection is at most 66 seconds, plus
HTTP calls and local scheduling. Each API subprocess is bounded to 20 seconds or
the remaining deadline. Slow service, quota waits, larger comment inventories and
machine suspension can exceed that normal target. An observation ends after at
most 65 minutes of monotonic elapsed time (subject to local scheduling). Pending
returns exit 3; rejected receipts exit 2; confirmed accepted receipts exit 0.

Controlled fake-clock tests reproduce the old 210-second terminal delay with nine
reads, then detect the same synthetic completion after 30 seconds using 22 reads:
four changed 200 responses and 18 authenticated 304s. A full 65-minute unchanged
window uses 66 reads, including two 200s and 64 304s. These are deterministic test
results, not measured hosted speedups. Authenticated 304s save primary quota;
secondary limits still apply. See [GitHub's polling and conditional-request guidance](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api).

Primary API exhaustion, including a successful response reporting exhaustion, waits for the actual response's reset time. When present, the response Date anchors that wait so client clock skew does not shorten it. Secondary limits
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

## Observation timing

Progress records include scheduled and actual sleep, read duration/status,
receipt discovery, final PR reconciliation and observer completion. Durations and
deadlines use the monotonic clock; UTC fields use the wall clock and are explicitly
separate. The returned result also carries a bounded observation summary, retained
by automatic delivery's ordinary queue journal. Standalone cleanup start/end
records distinguish workspace cleanup from receipt discovery and reconciliation.
None of these timing fields grants merge authority.

For the #1789 incident, GitHub merged at 10:33:27 UTC and posted its accepted receipt
at 10:33:30. The retained local file's final mtime was 10:36:56.207344 UTC. The
209.207-second merge-to-file difference (206.207 seconds from receipt creation)
is cross-clock and can include buffering, final verification and cleanup. The old
log has no per-poll timestamps. Its nine reads and 1,339,924 ms wall-clock runtime
support the deterministic capped-polling mechanism but do not isolate historical
sleep time or establish saved delivery time. Actual subsequent adoption remains
tracked in [issue #1791](https://github.com/ChengshuLi/WorldAtlas/issues/1791).

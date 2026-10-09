# Global request waste: bounded implementation, issue 1543

Refs #1543. This is a partial implementation of the original issue, not evidence that its setup-performance acceptance or global quota verification is complete.

The existing exact-object Git transport removes individual evidence blob downloads. This change consolidates fresh metadata reads, uses authenticated conditional requests between required authority passes, separates scientific evidence from quick test selection, and avoids restarting code tests after body-only edits. Independent reads remain parallel. There is no discretionary request sleep, shared API queue, or routine client serialization. Actual provider refusals retain bounded deadline and recovery handling.

The retained investigation distinguishes actual HTTP accounting from code-derived lower bounds. Its workflow-created time window is not a request billing window. The recorded 93% from the previous repair concerns two local evidence comparisons, not the whole system. Conditional requests still consume secondary traffic. The shared client's capacity floor cannot reserve quota against other clients.

The retained local regression log runs real CLI entry points with isolated fixtures, shared client concurrency, uncertain dispatch recovery, credential-free artifact delivery, workflow trust/sparse-checkout controls, and existing exact-head proof controls. It does not establish hosted end-to-end latency or installation-wide demand.

Remaining acceptance: independent exact-head review, normal merge, actual main verification, fresh hosted engineering/geography/history checks, measured paid requests and latency under mixed workloads, and real worker adoption. Cold/warm checkout, restoration and build measurements and complete scientific performance work remain under their original issues. No issue should close on these local checks alone.

Low-frequency boundaries inspected: publication planning scans complete operation history and associated commit PRs once per explicit plan invocation; it had no execution in the investigation window. Local merge observation already follows one durable request with bounded backoff. Manual provider-proof readers use bounded explicit reads and credential-free signed delivery. These remain coverage limits, not proof of zero demand or a reason to remove their authority checks.

## Reproduction

Use Node 24, without provider credentials or full-world materialization:

```
node --test test/github-admission.test.mjs test/github-snapshots.test.mjs test/github-quota.test.mjs test/geographic-report-artifact.test.mjs test/deployment-budget-scope.test.mjs test/trusted-workflow-checkouts.test.mjs test/pr-gates.test.mjs test/merge-integration.test.mjs test/final-capacity.test.mjs test/issue-lease-cli.test.mjs test/issue-lease-client.test.mjs test/git-blob-transport.test.mjs test/integration-proof.test.mjs test/job-deadline.test.mjs
```

## Independent-review amendments

The retained per-run inventories and classified accounting records are included with their original extraction scripts. Run `node coordination/engineering/global-quota-1543-20261009/aggregate-demand.mjs --out coordination/engineering/global-quota-1543-20261009/NEW-RUN-NAME` (replace the name with a fresh lowercase run ID) to reproduce the summary and execute duplicate/inconsistent-accounting controls. These records authenticate the retained investigation, not new independent retrieval of every original hosted log.

Mutating claim CLI actions now require a durable output path and exclusively own that local receipt. Atomic synced publication retains the last complete checkpoint on interruption; pending observation resumes the original identity. Missing output, unrelated/completed collisions and symlink outputs are rejected before HTTP. A dead local process lock can be released without treating the provider operation as failed. This is local request ownership, not an API queue or scheduling delay.

The four `day-*.py.txt` files are archived extraction provenance only. They preserve the historical extraction logic and paths, have no safe output admission, and are not reproduction commands. Use the bounded fresh-destination aggregator for reproduction of retained records; independent refetching of original logs is a separate investigation.

The renewed control run (`repro-final-20261009/`) uses the admitted fresh destination and binds all retained consumer records to the authoritative workflow inventory, including exact selected rosters. Wrong consumer joins and missing receipts reject before any output. Falsey/nonpending JSON receipts are preserved. The latest complete local regression log records 258 passing controls; earlier logs remain historical observations.

## Hosted full-suite correction

Hosted code run 37883373337 at f5e8f287500287f441737bd999ab8ec17749ae05 exposed tests omitted from the focused local selection. The geography bootstrap fixture selected the first inline workflow script rather than the geographic fallback and mutated the first permission block rather than the geographic job. Merge-entrypoint mock responses omitted authenticated core capacity headers while their child processes inherited Actions admission. These fixtures now exercise the intended boundaries with realistic capacity headers; production admission is unchanged.

The existing failure-only, read-only API diagnostic is restored. It uses one bounded request only after failure, preserves validation failure and redacts tokens, request metadata and unsafe message content. Successful jobs incur no diagnostic request or delay.

`hosted-fixture-repair.log` records 23 passing actual-entrypoint/bootstrap/diagnostic controls with `GITHUB_ACTIONS=true`. `expanded-actions-regression.log` records 278 passing selected controls with that same environment. These are not a claim that the complete hosted world/regression suite passed. Other hosted shards and renewed exact-head review remain pending. Metadata-only run 37883392065 succeeded while its same-head code run continued; package and regression jobs were skipped in the metadata run. This establishes the event split's behavior, not installation-wide quota savings or new baseline-helper adoption.

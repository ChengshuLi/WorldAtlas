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

# Worker system before and after the five engineering changes

The comparison baseline is `7e0d5c97aeb1f0d98ac035959a2fe7a3cafe99c3`, immediately before PR #631, the first change in this effort. It is **not** the state immediately before the fifth change. The five work items are #625, #628, #626, #627 and #650. GitHub Issues remains the live work record.

| Worker step | Before this effort | After the five changes |
| --- | --- | --- |
| Pick an issue | Ready labels, dependencies, bounded scopes and lane contracts already existed. Workers had to discover inconsistencies individually. | A read-only readiness audit reports contradictory readiness, dependency, ownership and scope conditions. It does not invent approval or claim issues. |
| Reserve work | Serialized bot reservations, unique worker IDs and owned paths already existed. | Those protections remain. Trusted sparse-checkout regression tests additionally catch missing module dependencies that can break reservation and merge workflows. |
| Do the work | Workers supplied their own evidence and scripts. Green scope/build checks did not establish that scientific calculations or source preservation were correct. | Versioned whole-file evidence manifests bind retained inputs, outputs, subjects, release pins, methods and limitations. Shared immutable preparation helpers provide tested coordinate, area and reproduction safeguards. They do not substitute for geographic research. |
| Submit and review | A claim, lane scope and current successful checks were required; there was no enforced substantive independent evidence review in the merge entry point. | Trusted validation checks manifests and the issue's evidence contract. A distinct worker's substantive review must bind the exact authored head and manifest. Scope, evidence and review are separate requirements. Legacy applicability follows the published policy; explicit issue contracts remain authoritative. |
| Another PR advances main | The merge script rejected a branch that was not ahead of or identical to current main. Workers manually updated the branch, reran checks and could repeat this when main moved again. | Preparation pins GitHub's exact combined-tree candidate. Changed reviewed files, including rename sources, must retain identical blobs and modes. Safe disjoint main advances can be tested without changing the authored head. Real conflicts and changed evidence inputs still need worker intervention. |
| Validate and merge | PR checks were inspected, then a globally serialized workflow performed a head-guarded squash merge. | Candidate validation runs in isolated read-only jobs in parallel across workers. Isolated evidence/docs packets run focused ownership, evidence and research-gate invariants. Runtime, workflow, schema and core-data changes run all regression files in three shards and one package build. Only the final authority recheck and merge hold the shared lock. |
| Handle contention/failure | Workers could need manual resubmission or branch updates; run lookup could lose an older request. | The client paginates discovery, latches the run ID, retries cancellation or a changed tested base up to three times with the same head, and verifies the bot receipt against actual merged state. Failed tests, expired claims, changed heads or invalid reviews never produce a successful receipt. |

## Quality and efficiency

New work after the evidence-policy activation has explicit evidence and review requirements. The system checks source preservation, scientific preparation, ownership and review instead of equating green CI with factual approval. It still cannot prove that a worker's historical interpretation is true; the independent review must assess the actual sources and limitations.

Evidence-only changes do not run application/browser/database regression unnecessarily. Application changes do need broader checks. Browser dependencies are installed only in shards using Playwright. Asset-dependent tests run after the single application build; migration-staging tests prepare their small derivative locally. Browser startup failures close their test server and exit instead of hanging CI.

The queue removes routine manual updates for disjoint main changes. It does not promise zero retesting or a fixed duration: if main advances after a candidate was tested, that candidate is rejected and retried automatically. This is safer than merging an untested combination. Heavy application tests remain outside the final shared lock, so other workers can prepare and validate concurrently.

## Boundaries that remain intentional

- Genuine conflicts or a change to reviewed bytes require a new authored head and review.
- Evidence asserting current-main metrics must be refreshed when its required baseline changes. Preserved baseline evidence can survive unrelated advances; stale factual conclusions cannot.
- GitHub's merge API guards the PR head, not the base. Cooperative main writers must use the shared queue. An emergency direct merge must coordinate with/drain it; the final read-to-merge interval is not an atomic base comparison.
- GitHub Actions concurrency is not FIFO and can cancel pending jobs. Bounded retry handles this, with an explicit failure after the limit rather than an infinite loop or false success.
- Research evidence does not implement geographic changes, approve a regional branch, authorize an import, or deploy the Site. Those retain their separate gates and publisher.

Actual hosted checks and activation receipts belong to issue #650 and its owned evidence packet. This document describes the implemented design; it is not, by itself, a successful activation receipt.

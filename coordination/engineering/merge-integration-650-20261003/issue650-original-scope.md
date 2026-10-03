Raised: 2026-10-03 (America/Los_Angeles). User reports concurrent workers repeatedly fail to merge because main advances while PR checks run. Current scripts/run-worker-merge.mjs requires main to be an ancestor of the PR head; serializing only the final PUT does not protect the longer test window.

Goal: workers keep developing independently, while an ordered integration process validates latest main plus the exact queued PR, without repeated manual main-update commits.

Acceptance:
- Investigate GitHub native merge-queue availability and the existing queue; choose the simplest supported safe approach.
- Validate the exact integration candidate against the latest main, including applicable CI, issue/lane/claim and evidence/review gates. Never merely remove the latest-main check and merge an untested combination.
- Keep the worker-authored head stable where possible. Reuse its review only when its reviewed bytes and scope remain unchanged; integration conflicts or substantive changes require intervention/review.
- Serialize the integration/test/merge lifecycle, handle a base advance safely, and give durable actionable queued/waiting/conflict/failure receipts. Avoid holding a global slot indefinitely for unfinished work.
- Cover two independently green PRs sharing a base, genuine conflicts, stale head/review, failed integration tests, expired ownership, base advances and retries with mocked or isolated tests. Do not mutate production as a setup test.
- Preserve squash title, historical records, stable identities, source bytes, lane isolation, geographic approval/import restrictions and the designated publisher. No live import/deployment/token rotation.
- Update worker documentation so ordinary workers use the mechanism without manual repeated rebases. Provide actual activation proof and report remaining platform constraints.

<!-- worldatlas-work:v1
{"max_prs":3,"depends_on":[627],"mode":"engineering","scope":"Eliminate concurrent main-advance retry loops with serialized exact integration checks; preserve issue ownership, current-head evidence/review and publication gates","evidence_quality":{"version":1,"manifest_path":"coordination/engineering/{job}/evidence-quality.json","subject_ids":[],"pins":{},"review_kind":"release"}}
-->


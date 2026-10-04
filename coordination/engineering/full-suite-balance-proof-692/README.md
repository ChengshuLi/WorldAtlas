# Full-suite scheduling: actual hosted result

Issue #692 source PR #693 merged as `e97c0e83d7637b316f2ae38339930cf2978c9ab8`. The normal queue tested candidate `e11f16fe27d9088af925be7509eab52847c58593`; its exact receipt is retained. The source and candidate both passed 676 tests with zero failures or skips; the prior baseline passed 673. The added three tests check complete shard assignment and stable heavy-file placement.

The slowest regression job took **520 seconds before**, **521 seconds in source CI**, and **506 seconds in merge-candidate CI**. This is not a demonstrated meaningful performance gain. The code stabilizes heavy-file placement, but the parity work remains the bottleneck. Issue #694 handles repeated preparation separately. These are full job durations, including setup and build; they exclude queue waiting and the separate package job. This proof records the result honestly instead of asserting a speedup from a green check.

Raw GitHub job metadata, exact source merge receipt, accepted branch-rotation claim, extracted TAP summaries and bound benchmark values are retained here. Full logs can be fetched with the connected GitHub `github_fetch_workflow_job_logs` tool using the job IDs, or GitHub Actions APIs with repository access. The baseline run is 37165467753, source run 37167079503 and normal queue run 37167746270.

This PR changes only the issue's owned evidence. It does not deploy, import, change credentials or modify the application. UTC timestamps are preserved as returned by GitHub. Recorded human date: October 3, 2026, America/Los_Angeles.

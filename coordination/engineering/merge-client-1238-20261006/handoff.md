# Merge-client API usage and recovery

Issue #1238; author 01a10843-da4b-7fc1-a482-d3186bc6334d.

The client submits once, prints identity before submission, and observes existing requests without submission. After durable registration it reads complete result-comment pages; successful registration and PR state are not repeatedly polled. Adaptive waits, actual limit responses, bounded retries/deadlines and exact final merge verification preserve queue protections. Observation alone never cleans files; explicit recovery cleanup retains ownership and preservation guards.

Actual local controls: 122 queue, integration-proof, result and workspace controls passed; 16 scope/entrypoint controls passed. The fake-clock hour test bounds API invocations to 18 for a one-page durable request; this is a simulation, not hosted CI timing. A real read-only recovery observation of merged PR #1221 used three API reads and verified reviewed head plus actual merge commit. No submission or cleanup was requested.

A large sparse-index control exceeds 1 MiB without materializing those dataset files, proves wrong-token/ignored-work refusal, and proves clean owned release plus recovery. The bounded 32 MiB Git buffer fixes the observed release failure while retaining guards.

No scheduler, production, provider, database or scientific changes. External running old clients are not upgraded by this patch. Actual main verification, hosted new-PR queue completion and adoption remain to be observed after independent review and normal merge. Refs linkage leaves #1238 open until those acceptance checks are reconciled.

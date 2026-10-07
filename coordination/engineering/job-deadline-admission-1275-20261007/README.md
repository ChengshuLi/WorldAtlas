# Remaining job time for #1275

The original registration job could admit two 181-second quota waits inside a
constructor-relative eight-minute window despite its five-minute timeout. This
repair authenticates the actual current run/attempt/job start through one
non-retried jobs read, reads the literal timeout from trusted workflow bytes,
and charges setup, metadata and elapsed work. Registration gains only actions:read.

Each retry must fit its wait plus a complete 20-second HTTP attempt, leaving
30 seconds for refusal/accounting and runner cleanup. A monotonic clock prevents
wall-clock rollback extending the admitted window. Admission runs before and
after the existing capacity hook, after sleeping and before another attempt.
Response consumption retains the existing HTTP timeout; late successful bodies
cannot admit subsequent queue work. Explicit quota metadata and same request
identity remain visible in refusal; ordinary denial and ambiguous writes do not
retry. A registration refusal fails its job, preventing an unregistered ticket
from advancing scheduling. Scheduling separately uses its real ten-minute budget
and refreshes dispatch/recovery timestamps after waits. FIFO, cadence, scientific
checks, exact-head review, immutable evidence, final capacity and cleanup stay intact.

## Reproduce without credentials

Use Node 24. Run the named suites from commands in evidence-quality.json; every
path was checked present. job-deadline.test.mjs calls the actual exported entrypoint
with the real API classifier and also spawns the actual CLI with synthetic HTTP,
clock and token. It checks both original long-wait cases, valid short retry,
elapsed setup/metadata/requests, late bodies, primary reset, permission denial,
oversleep, ambiguous POST, durable replay, complete run/attempt authority,
capacity refusal and a dispatch timestamp after a real classified quota wait.
Original tracked bytes are never modified by the controls; CLI scratch is exclusive
and removed in finally. Do not reproduce by exhausting GitHub or posting live data.

The controls retain 160 passing queue/capacity/evidence/integration tests and
23 scope/entrypoint/sparse controls. These are simulated admission proofs, not
hosted quota recovery. Historical-job-metadata.json records a prior complete
two-job attempt inspected under the operator credential; it does not prove the
new job token's permission. Fresh hosted acceptance, exact-head independent
review, actual main and subsequent corrected scheduling remain separate checks.

Preparation/final validation retain their established separate bounds; this
repair binds registration and scheduling, not every other job in the repository.
If setup prevents reaching the initial bounded metadata read, do not invent a
controlled completion receipt. Original #1249 hosted recovery evidence remains
valid and closed; #1275 is not closed solely on these local tests.

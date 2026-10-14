# Current processing-memory admission

The immutable selected reader (`processingAllowance`) and native preparation
(`preparationAllowance`) derive finite grants from current observations. They do
not require a fixed amount of physical RAM or a fixed 2.75 GiB free-memory floor.

## Observe and admit the actual process

Use Node 24's `process.availableMemory()` as the reported remaining supply.
The runtime observes the host and the constraints its platform exposes. Do not
replace this with total physical RAM, add swap/cache credits, or subtract the
resident parent/chat processes again. In the observed Node 24.19.0/libuv 1.52.1
Darwin implementation, available memory includes free, inactive and purgeable
pages; `os.freemem()` includes only free pages. Older runtime implementations can
report different conservative availability. See the [exact libuv implementation](https://github.com/libuv/libuv/blob/v1.52.1/src/unix/darwin.c).

`WORLDATLAS_CONCURRENT_RESERVED_BYTES` is a nonnegative safe-integer byte count
of **additional planned growth not already represented by the observation**.
An idle shared heavy-work lane has no such concurrent reservation. Its already
resident applications remain reflected in available memory. A declared pending
parallel job must reserve its prospective additional memory before it starts;
these cooperative guards do not discover or serialize other jobs.

`WORLDATLAS_MEMORY_HEADROOM_BYTES` (or the explicit `headroomBytes` argument)
is an optional explicit positive safe-integer byte reservation for system/parent growth and
uncertainty beyond the named concurrent jobs. Zero or malformed explicit policy
fails with an actionable error and never falls back. When absent, existing
unattended callers retain conservative automatic sizing: half the unreserved
available bytes. That is a default heuristic, not a physical maximum. Explicit
headroom replaces that heuristic completely, so legitimate grants may exceed
the former half-free ceiling. The same setting must reach the immutable reader, native preparation and pre-import
joint entry; existing launches inherit it through their environment.

The coordinator chooses and records the reserve before the operation, using the
actual environment's observed pressure/availability variation, other planned
growth and the operation's uncertainty. Do not pick it by subtracting the desired
job size merely to make admission pass. A historical peak from another input is
an estimate, not an upper bound for a new workload. No universal reserve is
established by this change. An operator choosing explicit sizing must justify
its reserve; absence does not silently select a smaller default reserve.

With explicit headroom, additional admitted growth is available memory minus the
concurrent-growth reservation and explicit headroom. The complete-process ceiling
adds only that same process's measured resident RSS. Phase and RSS grants may be
smaller than this ceiling; existing actual phase/RSS enforcement stays in place.
Automatic preparation observes admission once; an explicit prior grant is checked
against fresh observations and can be rejected after supply falls or reservations
increase. Already resident bytes are not charged twice.

For a **new separate child**, do not credit the preflight parent's RSS. The parent
remains resident and is already reflected in the available-memory observation.
Use zero child resident credit before launch, or independently measured existing
child RSS if the same-child contract supports it. A separate Node preflight does
not enforce a Python child's RSS. Keep the applicable real enforcement and cleanup
contract; do not label `/usr/bin/time` peak measurement as a live memory limiter.

The actual Myanmar coastal refusal observed 1,401,257,984 available bytes and
52,576,256 Node RSS. The removed half-free rule returned 753,205,248. Its historical
Python peak estimate was 995,868,672, leaving 405,389,312 physical bytes before any
new child launch. A nearby observed availability change was 572,882,944 bytes,
larger than that residual. For this current Mac operating session, the coordinator
chose `WORLDATLAS_MEMORY_HEADROOM_BYTES=572882944`, keeping forecast uncertainty
separate. With zero new-child resident credit and no concurrent reservation,
coastal004 would have 828,375,040 admitted bytes and still refuses the historical
995,868,672-byte estimate. This is a recent observation, not a guarantee, universal
default, new-target peak measurement or proof any other job fits. Re-evaluate the
policy after a meaningful operating/environment change; do not shrink it merely
to pass admission or repeatedly poll unchanged conditions.

Existing launch environments propagate this value to child consumers; configure
it once at the actual execution boundary, not through another packet wrapper.
For a separate Python child, the coordinator must pass `currentRssBytes: 0` to
its prospective guard. Setting the environment does not change child execution
or install an RSS supervisor. Existing unattended queue/build callers need no new
configuration and retain their established conservative automatic policy. Do not
apply the observed Mac reserve to cloud/CI machines without their own basis.

## Keep the operation bounded

Operators requesting explicit sizing supply justified headroom through the
argument or existing environment. Native preparation already supports `--phase-bytes` and `--rss-bytes`;
these request smaller limits and never bypass fresh physical admission.
Malformed/negative observations, exhausted remaining growth and unsafe integer
sums fail closed. File/decoded-member bounds, descriptor bounds, complete-phase
input/carry/output accounting and current RSS checks still apply.

Inspect a failure's actual bound and prospective accounting. If a real operation
cannot fit the current grant, preserve its checkpoint and reduce or restructure
that operation, or wait for an actual resource change. Do not invent a larger cap
from an earlier peak, skip a check, or repeatedly poll an unchanged condition.

This admission is cooperative, not a kernel quota or an allocation guarantee.
Availability can change between checks, and reported availability does not prove
all platform limits are exposed. Historical scientific receipts, runtime/group
contracts and distinct producer/consumer checks retain their existing meaning;
this guide changes none of those contracts or geography approval.

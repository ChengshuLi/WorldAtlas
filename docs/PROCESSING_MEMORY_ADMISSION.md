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

After that reservation, half the remaining reported supply stays unallocated for
parent/system growth and expansion. The other half is admitted additional growth.
The complete-process ceiling is current measured RSS plus that growth. Both the
complete-phase byte limit and total-process RSS limit default to this ceiling;
explicit positive grants cannot exceed it. Only measured RSS gets this resident
credit, never runtime executable size, transport size or historical phase counts.
Repeated request validation observes resources again without subtracting already
resident bytes a second time. Lost remaining supply or increased future concurrent
reservations can still make the same request inadmissible.

For the reported idle observation of 1,590,296,576 available bytes and 51,658,752
current RSS bytes, with no concurrent reservation, the default ceiling is
846,807,040 bytes. That is an admission calculation, not a measured GIS peak or
proof that any particular native operation fits.

## Keep the operation bounded

Ordinary launches need no new override. Native preparation already supports
`--phase-bytes` and `--rss-bytes`; they request smaller explicit limits and do not
bypass current admission. The immutable reader's default grant is automatic.
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

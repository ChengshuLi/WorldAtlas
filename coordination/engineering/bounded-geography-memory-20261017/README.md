# Selected checker allocation roots, first coherent cut

Refs #2396. This is an architectural reduction, not a claim that the entire
JSON-backed qualification pipeline uses constant memory. No heap increase,
scientific format change, scope cap, owner concession or source-authority bypass.

## Removed work

- The native comparison no longer expands original base rows, constructs two
  sorted/copy-filled effective maps, or retains every touched decoded container.
  Both states have the same authenticated base and stable owner roster. A full
  streaming disjointness check of each cumulative patch against that base permits
  exact cancellation: all losses and changed-cell witnesses come from the patches.
- Immutable Git blobs and whole containing native transport fragments stream
  through complete encoded/decoded size and hash checks. Shuffled native words
  spill to private scratch on the invocation's working filesystem, then fixed
  16,384-word windows authenticate the complete canonical word hash before use.
  Only the row table and one run container remain open; failures/early exits close
  and remove stores. The default is the working directory, not `/tmp` (which can
  be tmpfs). Deployments must put that working directory on disk-backed storage.
- A derived checkpoint's authentic accepted report already binds its complete
  ledger, registry, patch and manifest. It now retains authority classifications
  rather than reacquiring all historical native patches. Fresh authorities still
  receive full qualification, and the next union is accepted baseline + fresh
  patches. Legacy seeds retain original reconstruction. Changed legacy rebinds
  hydrate only the exact legacy operands they actually need.
- Canonical hashes no longer clone and serialize the entire graph at once.
  Canonical patch-union equality uses one cursor per contributing authority,
  without another complete expected-patch graph or dense-row sort.
- Visibility reuses patch-row references in 128-row scan batches. Polygon
  preparation batches by coordinate slots rather than rejecting component 4,097.
  Native primitive membership and witness order are unchanged. The screening
  caller uses the same bounded preparation, including cross-batch identity checks.

## Memory model and remaining limits

For one active native traversal, working native-byte memory is a fixed number of
stream buffers plus two pairs of 64 KiB word/plane windows. It is independent of
native cell count, total native intervals, largest dense row and total container
count. Disk scratch is the complete row-table decoded bytes plus at most the
largest decoded run container. Hash/scan time still reads complete containing
fragments and complete canonical containers; random fragment reuse can repeat I/O.
Concurrent invocations multiply both working buffers and scratch by concurrency.

The *whole job* still retains parsed baseline/candidate ledger and patch graphs,
owner/source certificates, route/manifest descriptors and changed-row/report
metadata. The legacy rebind path retains its authentic original current and
predecessor rows and may hydrate legacy patch operands. A fresh source authority
may parse a complete original product. These terms grow with actual patch
intervals, geometry vertices, components, owners, sources and input paths; they
are not all unavoidable metadata. JSON parsing still has a largest-document
transient term. Polygon preparation has a largest-single-primitive term. Loss
reports and successful component witnesses retain their full outputs; report
serialization remains proportional to output. Further streamed/disk-backed
JSON qualification/output work is tracked in #2396 rather than hidden behind a
constant-memory promise. Ordinary `projectNativeRows` compatibility consumers
still use their existing expanded representation; the selected comparison does
not call it for newly acquired nonempty rows.

## Evidence

The attached actual comparison uses the same immutable eight-package arithmetic
as the prior #2387 measurement: original base manifest
`d9954fa51d18e4ce785679f920e4b6ac1ebd3cf07ce03fa7e7e674cb2a42faba`, baseline
`c8a5133bc78923b8ca78c6feeb992b87ceaa8c17:coordination/engineering/greenland-repair-delivery-20261017/composition-current-001/patch.json`
(SHA-256 `bb62deda4e1bf4b2d51a08baf6503b21ed13e54a9f1cf03e7c52e408b3518643`), candidate
`f6f6f15109d63b918e1a4569ac68906e948117a7:coordination/engineering/five-repair-delivery-20261017/composition-004/patch.json`
(SHA-256 `c3c83e3bec5a1dbe60df63eea7d22d5173281de1ad1068c5632cbda674c6cf9d`).
All 107,587 changed rows and 20,514,842 original intervals were consumed with zero
loss, and 256 distributed complete-row results matched the old eager arithmetic
exactly. Node 24.19.0 default-heap max RSS was 601,992 KiB versus prior 1,100,084
KiB. The retained emitted containers are 16 MiB maximum; row-table scratch is
2,097,328 bytes. This is arithmetic evidence, not a whole qualification replay or
hosted acceptance receipt. It includes parsed original patch/owner graphs, unlike
the isolated fixed-window scaling kernel.

Repo tests exercise exact small/exhaustive cancellation, 8,193 polygon components,
one large primitive, whole fragment suffix corruption outside a selected member,
Git nonzero exit after exact bytes, encoded/decoded corruption, source failure,
ENOSPC, cancellation, closed stores, complete row consumption and private-state
custody. Independent scaling uses fresh processes and disk-backed scratch; process
RSS excludes filesystem page cache, and cgroup-wide accounting was unavailable.

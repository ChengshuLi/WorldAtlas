# Bounded canonical hashing

Issue #2396 subcut: `valueSha` consumes the exact canonical JSON bytes plus the
existing terminal newline without a cloned value graph, complete serialized
string or complete byte buffer. `valueBytes` retains its literal public behavior.
String slices preserve surrogate pairs; integer-like object keys retain JavaScript
JSON enumeration order after canonical key sorting. Invalid, nonfinite and cyclic
values refuse without returning a hash. No persistent value cache is introduced.

Additional state is traversal ancestors, one current object-key ordering per
level and bounded output fragments. The supplied parsed input still occupies its
original memory, and recursive traversal still has the runtime stack bound. This
is not a constant-memory claim for the complete geography job.

## Controls

`node --test test/canonical-value-hash.test.mjs` exercises exact agreement with
`sha256(valueBytes(value))`, 500 deterministic nested inputs, numeric property
ordering, control characters, Unicode/surrogate chunk boundaries, sparse arrays,
shared references, invalid values, deep failure and mutation without caching.
The large shared-graph child completes with `--max-old-space-size=64`; its expected
hash is the separately executed original serializer result.

The adjacent source/authority controls and original successful qualification
remain separate from these hash-only comparisons. No source or native predicate
was replayed to measure hashing.

## Measured comparison

`comparison.json` retains process measurements and the exact actual Git input pin.
The representative actual input is the complete 26,453,595-byte cumulative map
patch, already independently authenticated in the memory review. Both hashing
implementations produced its exact `c3c83e3b...` SHA256. Separate fresh Node 24
processes measured 478,520 KiB versus 308,676 KiB lifetime maximum RSS (old/new),
and 435.29 ms versus 715.47 ms hash elapsed time. Thus the memory reduction comes
with a measured CPU cost; lifetime RSS includes parsing/imports and is not a
per-operation allocator measurement or enforced whole-job limit.

The shared-graph comparison used 2,000 references to one 1,000-point geometry:
353,208 KiB versus 56,612 KiB maximum RSS, identical complete hash. Only the new
shared-graph process used the 64 MiB heap argument. Actual-patch processes used
the ordinary default heap; neither changed its input or scientific result.

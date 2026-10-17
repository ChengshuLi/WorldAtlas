# Bounded native patch JSON admission

Issue #2396. `scripts/native-patch-store.mjs` is an invocation-local data store;
it does not mint authority or replace source/scientific qualification. Its first
consumer integration is a separate change.

`admitNativePatchStore({chunks, expected:{bytes,sha256}, directory, size,
ownerCount, rowField:'rows'})` asynchronously admits an original JSON byte stream.
The caller still authenticates the immutable source's role, mode and Git identity.
The result has immutable metadata, a canonical JSON SHA, complete row/run counts,
synchronous `rowEntries()`, `rowAt(y)` and `intervals(row)` cursors, plus `close()`.
`rowField:'native_rows'` supports an isolated component with the same parser.
Only a successfully admitted store can yield its private row handles.

Each valid dense row is parsed one triple at a time. Fixed 12-byte run records
and 16-byte row offsets live in owned disk scratch; bounded read/write windows
replace retained JS triple arrays. Complete original byte length/SHA, full JSON
syntax/EOF and all final row domain checks precede admission. JSON.parse key
semantics are preserved: later duplicates replace earlier values and their domain
errors, while malformed syntax in overwritten fields still fails. Canonical
identity retains unknown metadata, field ordering, numeric and string semantics.
The private unsigned integer representation normalizes negative zero as canonical
JSON does. Original wire bytes and legacy materialized APIs are unchanged.

Caller chunks are snapshotted before hashing/parsing. Failed producer, allocation,
setup, syntax, domain and hash admission removes owned scratch and returns the
producer. Runtime disk failures remain visible; no invented file/phase byte cap
is added. Coordinates/owners must fit the unsigned fixed record format. Actual
scientific lattice and owner bounds come from authenticated caller inputs.

## Evidence

`node --test test/native-patch-store.test.mjs test/native-ledger-store.test.mjs`:
19 tests pass, including 180
bounded differential patches, every byte split of Unicode/number fixtures,
duplicate/overwritten fields, complete syntax and hash refusals, mutable chunks,
ENOSPC setup, cursor corruption and a 250,000-triple dense row under a 64 MiB heap.

`actual-patch.json` records one full retained map patch streamed directly from its
exact Git blob through the store and all cursors under a 64 MiB heap. Every one
of 158,773 rows / 1,086,850 runs is retained; the canonical SHA equals the original
canonical product SHA. Temporary records are removed immediately afterward.
An initial measurement preceded the final producer-snapshot/setup-cleanup fixes;
the committed measurement repeats the same parser-only check on the final code.
No scientific/native qualification was replayed.

This bounds valid native row/interval storage, not every input/output term.
The largest individual scalar/metadata/geometry value and caller input chunk are
still materialized; root metadata remains resident. Source geometry, consumer output and qualification adapters remain work
for the integrated bounded-memory change. A giant invalid single value can still
occupy that individual-value term before rejection.


## Ledger component storage

`admitNativeLedgerStore` uses the same JSON parser and interval writer for ledger
`rows[*].native_rows`. The result exposes `componentEntries()`,
`componentMetadata(handle)`, `componentRows(handle)` and
`componentCanonicalChunks(handle,{overrides,newline})`. Each component handle
contains only ordinal, raw canonical SHA and row/run counts. Metadata, including
geometry and unknown legacy fields, resides in a disk spool and is materialized
one component at a time. Complete component canonical chunks include all original
fields and can inject the existing registry fields for normalized identities.
The storage layer never interprets those overrides as source authority.

Duplicate root rows, native_rows, pixelIndex and disposition use only their final
JSON values; previous domains/counts/offsets are reset. Scientific nativeOnly
rules still belong to the existing consumer: exact fields, positive rows/runs,
owner identity, native_cells and authenticated lattice. Empty rows remain legal
at the storage boundary just as with the original completeRows function.

All row, interval and component cursors accept a positive `windowRecords` tuning
option. K-way merge consumers can divide a fixed total prefetch budget across
active operands rather than retaining a default window for every authority.
This tunes memory/throughput and never rejects a product by byte size.

`actual-ledger.json` records complete direct admission/traversal of the exact
48,584,265-byte candidate ledger under a 64 MiB heap: 4,191 ordered components,
547,068 component rows and 1,108,298 intervals, with its original canonical SHA
unchanged. Its 34,935,453-byte scratch store was removed immediately after the
measurement. The largest single component/geometry remains an explicit memory
term; the complete job is not yet migrated to these cursors.

Independent bounded probes covered 7,841 patch cases and 6,188 ledger cases against
JSON.parse, the original row-domain rules and canonical serialization; an
8,000-component stream also passed under a 32 MiB heap. They found and led to fixes
for an allocation-time iterator leak and test mock-restoration leakage. These
are isolated data-store controls, not scientific source or consumer adoption.

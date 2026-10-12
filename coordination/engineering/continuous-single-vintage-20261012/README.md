# Single-vintage coordinate custody

Issue: https://github.com/ChengshuLi/WorldAtlas/issues/1767

The actual selected-continuous entry now performs complete coordinate acquisition,
publication and readback custody in one baseline snapshot frame. That frame ends
before candidate acquisition. The candidate frame performs its complete coordinate
acquisition, publication/readback, two-vintage affected-plan construction and required
source projection. It ends before baseline required-source reacquisition. For the
additive retained comparison this changes five selection loads to three; complete
source scans, identity/provenance joins and original strict polygon comparison remain.

## Complete accounting without changing historical science

The entry owns a private ImmutableReader subclass. Every phase first executes the
ordinary reader's normal runtime/code/output/RSS checks, then prospectively adds
all enclosing context, code identities, acknowledgements, sealed custody, lifecycle
metadata and the growing reader inventory. No body is opened before this addition
fits. The unchanged coordinate shard/join helpers still charge their complete live
snapshot, prior shards and own metadata. Their phase resets cannot discard the
caller's custody. The private reader never escapes a completed acquisition frame.

This is a reviewed accounting adapter, not a source/method replacement or persistent
cache. Shared selected-neighbor-prevention.mjs, supported-programs.json and the
actual 17/28 SOURCE/NATIVE code vectors stay unchanged. Historical execution evidence
is not repinned. The new entry hash is explicitly included in the unchanged-selected
routing profile; the input routes and older audited profiles are preserved.

## Trust and lifetime

Proposed commits remain data only. The trusted checkout and all consumed method
bodies are authenticated at the real entry. A persisted certificate is reread in
full against the exact publication issued by this invocation, joined against the
same genuine selected resolver's complete source/owner identity, then sealed using
the existing private custody helper. Serialized copies cannot mint those receipts.

Native GC now belongs to the continuous process rather than two coordinate-only
children. The Python caller launches the authenticated --expose-gc entry, and the
entry rejects other runtime flags or injected Node options before output mutation.
Whole source frames, coordinate output buffers and each selected snapshot become
collectable at explicit boundaries. Existing standalone coordinate and public
persisted-validation/source-acquisition helpers remain available.

## Verification scope

Focused controls exercise the actual entry, exact source projections, complete
neighbors, missing owners, source/feature/geometry changes, persisted byte tampering,
selected commit drift, private receipt forgery, every shard/join carry reset, a
carry-only budget deficit before source opens, and WeakRef collection before the
next vintage. The actual Python wrapper still executes original positive, loss and
overlap comparisons. These synthetic controls establish the changed boundaries;
they do not constitute new geographic source qualification.

The retained real-input run is separately admitted with full output equality and
sampled process-group observation. Its exact command, input/code commits and timing
are recorded with that run. Historical elapsed comparisons are not controlled or
hosted speedups. No selected release, scientific data, import or deployment changes.

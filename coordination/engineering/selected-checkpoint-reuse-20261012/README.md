# Selected checkpoint reuse

This module is the shared data/custody boundary for the native and continuous
consumers. It does not import candidate code, execute SOURCE/NATIVE science,
activate a selection, or replace geometric predicates.

## Invocation contract

1. Bootstrap the genuine trusted execution/runtime and its current processing
   allowance using the existing selected reader entry. Make all baseline and
   candidate readers share one `ImmutableReader.budget` and allowance.
2. Supply `budget = {shared: reader.budget, carriedBytes}`. `carriedBytes` is the
   complete external live state, including caller custody and output buffers.
   It cannot decrease during the invocation. Historical peak/allowance values
   do not grant current memory permission.
3. Call `qualifyCheckpoint({reader, checkpointId?, budget})` once. `reader.version`
   is the actual requested baseline. Unrelated commit changes do not prevent
   reuse when its selector and complete input/present-or-absent routes match.
4. Call `qualifyTransition({state, reader: candidateReader, budget})` once. The
   module derives all changes from actual committed products. Reuse-unavailable
   returns the still-qualified baseline and `cold: "candidate"`; absence of a
   qualified baseline returns `cold: "baseline-and-candidate"`. The current module
   returns this fallback decision only. A one-acquisition cold-candidate admission
   bridge and the shared consumer orchestration are not implemented here yet;
   legacy callers must not claim they already realize the one-acquisition path.
   Corrupt custody
   throws. Neither outcome is a successful no-change result.
5. Native and continuous consumers use those same private states in one trusted
   Node invocation. Do not serialize the objects to independent children or
   repeat qualification for each consumer. Each consumer may project only its
   complete required scope, then apply its existing strict predicates.
6. Call `releaseCheckpoint(state)` once, in the joint caller's `finally`, after
   both consumers finish. This invalidates every related private capability.

`projectSourceFeatures({state, ids, budget, reuse?})` returns complete original
features plus exact ordinal, owner/parent, whole-source, feature and geometry
inverse/custody. A prior private projection can be supplied explicitly as `reuse`
when the complete source bindings and requested IDs match; each result retains
its actual vintage's `state_binding`.

`projectNativeRows({state, rows, budget})` returns `{y, runs}` for every requested
row, including empty rows. These are selected-base intervals; consumers apply
the qualified state's cumulative `patch` exactly once. Intervals have the actual half-open native x domain
and owner indices. Accepted full rows are reused only under the same complete
base and routing identities; missing rows are reconstructed from complete
containing native members with full row-table/range checks. Results report
`reused_rows`, `acquired_rows`, native binding and actual whole input custody.
Coordinate boxes are never native evidence.

The private state exposes frozen coordinate/ledger/registry/patch/addition views.
The transition exposes complete `changedIds`, `changedNativeRows` and `plan`:
`changed_ids`, `required_ids`, `pairs`, both `source_paths` and both genuine
`source_bindings`. The plan traverses every old and new coordinate row and includes
unchanged neighbors and other changed owners. Its boxes only exclude impossible
neighbors; consumers must still run the original full-polygon predicates.

`deriveCoordinateDelta` is pure arithmetic for testing. It grants no capability
and cannot be supplied to either projector as a qualified state.

## Acceptance root and finite profile

`accepted-checkpoints.json` is read only from the actual executing trusted
checkout. Candidate copies, candidate-chosen Git refs and serialized lookalikes
cannot create authority. The catalogue pins the complete original accepted
products and their actual executed code/runtime, plus a complete immutable route
index. Root products remain in their original retained packet; they are not
copied here or relabelled as new execution.

The initial catalogue indexes both genuine sides of PR #1771's frozen retained
execution. PR #1771 was accepted at main commit
`2f25e80412640f2a34681a7d487737739475c1d2`; activation of this new boundary
still requires its independent review. Its historical
execution is `8b3d8265309d4f6104cca03d78f72a8f48d0f3d2`, and selected commits are
`9473d184683ee8ff8546300f2313779c3cba1d2b` and
`791576647adc41241ce9b438f1bb0034088eed4e`. Those original vintages stay explicit.

Supported transitions conserve the entire old ledger, including exceptions,
registry, original primitives, native assignments and source/native alternatives.
Only genuinely appended authority entries run original programme qualification.
Current rebind products are checked against old accepted whole operands plus
new detached projections. Unknown base/schema/transport identities require cold
validation or refusal. Legacy source-bank transports and split native row tables
are not silently approximated by this initial profile.

The catalogue's finite executing-code vector must be updated coherently whenever
a consumer changes one of its exact shared dependencies. This is explicit
coordination with the module owner; it is not permission to relax historical
execution or producer-code qualification.

## Verification and limits

Run `node --test test/selected-checkpoint.test.mjs`. Tests create a miniature
ordinary trusted Git repository and invoke the real catalogue, private state,
projection and transition boundaries. Synthetic controls do not prove the real
geographic result or establish a speedup. No real selected equivalence execution
has been run for this module yet. One coordinated retained-input equivalence run
is planned after independent contract/code review. No old SOURCE/NATIVE science
rerun is needed or authorized by this implementation.

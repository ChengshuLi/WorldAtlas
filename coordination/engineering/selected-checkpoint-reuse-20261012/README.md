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
   The accepted-artifact alternative, `qualifyAcceptedCheckpoint`, can also
   advance an older accepted selector to the requested baseline. It authenticates
   the accepted merged tree, qualifies the existing append-only transition, and
   carries every newly consumed scientific route into the candidate comparison.
   It never reconstructs the complete source bank. Missing historical transport
   declines reuse; an inconsistent authenticated tree or corrupt custody fails.
   This applies to positive-native additions as well as unchanged native rows:
   consumers still compare every actual changed row and every possible continuous
   neighbor. Accepted geometry is reused only while the complete base, identities,
   scientific routes and prior literal ledger/authority records remain unchanged.
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
   repeat qualification for each consumer. Each public consumer calls
   `authenticateTransition({transition, budget})` to admit the genuine private
   transition and complete scope; caller-created wrappers cannot omit a neighbor
   even when they contain real state capabilities. This lookup does not rescan
   coordinate rows. Each consumer may project only its
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
copied here or relabelled as new execution. Current qualifier code is authenticated
against the executing trusted checkout's Git HEAD and actual local bytes. Editing
reviewed qualifier code requires no catalogue hash refresh; original scientific
execution/runtime and product pins remain historical and unchanged.

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

Run `node --test test/selected-checkpoint.test.mjs`. The 22 controls create an
ordinary miniature trusted Git repository and invoke real catalogue, private
state/transition, projection and budget boundaries.

The admitted retained proof in `retained-proof-001/summary.json` executed shared
module commit `41a9e8c003e57914f5fe03afe62f3ce177d46a93`. Complete scientific
certificate fields for all 49,625 owners equal the genuine retained candidate.
The full 54-owner continuous operands, additions and neighbor plan have the exact
retained SHA-256 `949622e24a0431c707ebc1b9cfaaee21db768bc165aad17ba9e04534b4bb048e`.
All 42 changed native BASE rows equal their complete genuine retained request.
Coverage records zero `loadSelection` calls and five authority qualifications,
matching exactly the registry's 30-to-35 append. No old SOURCE/NATIVE science ran.

Eight whole containing source bodies were read over five distinct sources: three
for new-target authentication, five for the complete affected-neighbor projection,
and zero for candidate-vintage pointset reuse. This is not zero source reads; it
is zero complete world-source scans. Shared authentication and projections took
26.66 seconds; the full supervised proof, retained output and comparisons took
28.51 seconds, with 529 MB sampled group RSS and 710 MB derived final charged phase
inside a 1 GiB current reader allowance. The original pre-admission sample was
707,801,412 bytes; adding its final admitted request gives 709,678,830 bytes,
with the full derivation retained in the summary. These are measured local boundaries,
not a controlled hosted speedup or an integrated native/continuous checker run.

Only the certificate's historical `complete_phase_bytes` accounting counter is
excluded from semantic equality. Both old values are retained in the summary;
no scientific binding, row, source identity or polygon is excluded. A derived
certificate retains its original checkpoint's historical counter; current
permission is always the joint reader budget, never this old number.

The first comparator attempt and corrected successful attempt are both retained,
including complete successful actual products before comparisons. Their original
supervisor emitted an empty `owned_processes_remaining` array without a terminal
scan. The summary explicitly supersedes that unsupported field: cleanup-at-exit
was not measured. The later process observation records present visibility only.
Do not reuse the original supervisor as a lifecycle verifier without correcting
and testing its terminal check.

The initial post-proof delta added constant-time private transition admission
and freezing of the returned native-row scope for consumer safety. The later
policy-continuity and scientific-route correction is documented below and has
its own focused controls/review. Neither change relabels the archived proof's
original execution head.

Consumer integration, actual joint strict-predicate execution, and the one-load
cold-candidate admission bridge remain unfinished. No activation, geographic
approval or production delivery is claimed by this module.

## Current-baseline policy identity and finite consumer preregistration

Metadata-only inspection of the accepted Australia13 comparison established that the pre-AUS selector at `46438af8901acbad11a9b627828a9e9184018a77` exactly equals retained1771 candidate `791576647adc41241ce9b438f1bb0034088eed4e`. The complete source/owner/domain/release binding is unchanged. Of its 145 archived routes, the only later difference is the executing trusted `supported-programs.json` policy. That file is not selected geography. The qualifier retains and authenticates the complete archived census, independently reads the actual inventoried execution-policy body and current executing policy, and requires every old programme/migration record to remain exact. Removal or alteration returns explicit fallback. Only then is this exact policy path excluded from scientific-route equality; this initial append-only policy profile is intentionally conservative. Appended producer authority still reads the actual executing trusted catalogue, never candidate policy. Every source/native/alias/presence-absence route remains exact. Focused controls exercise policy evolution, forged candidate-only producer policy, census omission/corruption and neighboring input drift.

Independent finite profile review: https://github.com/ChengshuLi/WorldAtlas/pull/1782#issuecomment-6120928599. This accepts code/profile preregistration, not a main merge or any new validation product.

The coordinated preregistration derives one exact future SOURCE/NATIVE17 and CURRENT_REBIND28 vector from frozen combined `392b1cda6d529f13f8e9d5fc86efe8dc436386a3`. The native checker is exact reviewed `39792e02c603e262513dd0d9df4b63dc275e5a15`; allocator `fd20a0acfe97dcbffa2369a9dfba61e04832837a` is now accepted at `9b27b8405d85741e43184b5c25e1a6ac391d4449`. Only the native-checker position differs from the already registered allocator-aware vectors. All prior nineteen programmes and seven migrations remain unchanged. The only new historical mappings are the two actual rebind executions consumed by the successful accepted pre-AUS/AUS comparison: `85ca24519d87bb1d62a86d5cb142006e206cb2b8` and `40d792b2c67b18098c00cd71bce3cfd6a8e63a0b`. Preregistration does not activate runtime code, grant candidate policy authority, or alter the old scientific bodies.

The runtime qualifier catalogue in this inactive PR continues to bind the existing native checker. The one-row native pin update belongs with coordinated runtime adoption in1784. The archived41a9 proof remains under its original execution identity; these corrections do not relabel it as a current-AUS or integrated proof. One subsequent admitted joint pre-AUS→AUS validation will retain genuine derived checkpoint products and compare all available accepted outputs. Automatic accepted-artifact advancement and the one-candidate cold bridge remain separate unfinished work.

Final focused controls at `c95082fbdb1e092d6cada098e7b48dd4809140dd`: twenty checkpoint tests and fourteen catalogue tests passed, zero failures/skips. Both complete suites finished in 38.548 seconds; this test timing is not a batch-performance claim.

A final custody-only correction shares each temporary archive/authority reader inventory with its invocation parent. This retains every actual consumed pin for the joint publication without rereading it or exposing a new authority API. A focused real-Git test confirms whole archived pin retention and separate invocation inventories/lifetimes; prior numerical and policy controls remain reusable. The original41a9 proof is not relabelled.

## Accepted AUS optional producer limits

The first joint current-AUS attempt in1784 stopped during authentication: the accepted producer request includes bounded `stdout_bytes`, `stderr_bytes` and `monitor_bytes`, while this module duplicated an obsolete six-field limit schema. No native/continuous comparison ran. The correction reuses the existing cold producer's `validateCurrentRebindLimits` required/optional schema and retains the ordinary output cap. Unknown fields, missing required bounds, unsafe/nonpositive limits, excessive descriptors/log bounds and a stop threshold above RSS still reject. Original complete plan/limits equality remains authenticated by `verifyCurrentRebindExecution`.

The real accepted limit schema and adverse controls pass. The retained metadata-only `accepted-aus-producer-envelope-control` authenticates the complete actual certificate, products and external execution custody, checks the remaining request/facts/publication/operating/acquisition shapes, current/historical code compatibility, and exact output/admission bindings. It performs no source/native projection, numerical rebind or selected reconstruction. The failed actual invocation and its measured operating outcome remain in1784's packet; this control is not joint-equivalence acceptance.

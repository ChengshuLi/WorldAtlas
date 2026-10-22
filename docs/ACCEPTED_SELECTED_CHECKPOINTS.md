# Accepted selected-checkpoint handoff

A batch's provisional products become reusable only through the normal accepted
merge boundary. A locator, a candidate certificate, a local digest or an uploaded
ZIP alone cannot qualify a checkpoint. Source authority and delivered-map validation remain required. Continuous polygon
overlap is outside the selected map-cell repair scope.

## Authority and lineage

`acquireAcceptedCheckpoint` reads the existing bot `worldatlas-merge-result:v1`
receipt, checks the actual merged PR with the same verifier used by the queue,
checks the accepted/tested trees, and authenticates the originating geography
run, job and artifact. It returns an invocation-private handle. The selected
qualifier independently checks complete selectors, source/native bindings,
execution lineage, native conservation and the complete
present/absent route census before creating its own checkpoint capability.

Historical PR provenance uses the removed `merge-integration-checks.yml` /
`pull_request`; its immutable workflow
head is the reviewed PR head. Queue provenance uses `worker-merge.yml` /
`workflow_dispatch`; its workflow head is recorded separately from the reviewed
PR head and tested candidate. Failed-job-only reruns retain the actual original
producer attempt/job/artifact. No result is relabelled as a new execution.

The handle stays inside the trusted joint Node invocation. It is never serialized
between the Python wrapper and a new Node child. Releasing it expires access.
Original predecessor acceptance remains lineage; it is not a request to reacquire
or rerun historical science.

## Final-bank authority profile

The versioned existing checkpoint can bind selector-v2's complete index-v3 final
bank/context instead of cumulative repair products. Initial adoption authenticates
the actual accepted predecessor's exact words and deterministic finished-footprint
conversion. Its compact authority list is derived from the complete accepted
registry: unique sorted authority SHA plus the complete canonical entry digest,
including any completed constructor. Later transitions retain every prior pair
exactly and reject a repeated authority SHA even if its completion pin changes.
Only the existing privately qualified new native append can add pairs/cells.

The shared comparison checks every unchanged word/context value, exact new
unassigned-before intervals/qualified owners, fixed compatibility URLs and current
reference metadata. Lazy untouched reference geometry stays lazy; a newly touched
owner must match its retained original geometry hash. Metadata-only projection
updates remain distinct from new positive cell authorities. Old authority bodies
and cumulative ledgers remain historical evidence, not normal final-bank inputs.

Candidate-code cold reports use the same exhaustive comparison, identify their
actual executing code, and cannot issue or retain accepted checkpoint authority.
This route is credential-free: anonymous read-only custody metadata plus the exact
retained artifact, with no authenticated Actions-download fallback. Ordinary
accepted-code joint issuance still requires its existing authenticated custody.
A malformed or downgraded current profile cannot choose legacy replay.

## Authenticated artifact

`geography-check.json` remains the authenticated root, including the actual native
conservation result and per-component visible-cell witnesses. Its optional `checkpoint` object has version
`1`, kind `selected-checkpoint-products-v1`, and a `members` array. Each member
has a fixed `name`, exact `bytes` and `sha256`; gzip members additionally bind
`decoded_bytes` and `decoded_sha256`.

The complete supported roster is:

- `derived-certificate.json.gz`, `derived-facts.json`, `derived-publication.json`
- `checkpoint-routes.json`
- `operating.json` only when an actual producer emits it

The provisional derived publication keeps `accepted_checkpoint:false` and its
`native-passed` validation stage. Acceptance is external custody, not an edited boolean.
The successful trusted job supplies terminal execution authority; the transport
does not fabricate an operating or cleanup measurement.

The in-memory reader verifies the trusted root hash before interpreting member
descriptors. ZIP entries must be ordinary fixed files, unique and exactly listed;
local records must tile the local-file area without gaps or overlap. ZIP64,
traversal, links/directories, contradictory sizes/CRCs, malformed descriptors,
compressed trailing bytes and excess decoded gzip output are rejected. Nothing
is extracted into the trusted checkout. Legacy one-member artifacts remain
reports and cannot provide checkpoint products.

Existing accepted seven-member archives remain byte-identical. The reader
authenticates their original archive and root, then decodes only the four current
native checkpoint members. It neither decodes archived polygon operands nor
fabricates a polygon pass. New producers emit only the four-member roster.

The existing ordinary/report and archive limits remain 32 MiB and 40 MiB.
Checkpoint acquisition additionally admits the complete transport, decoded JSON,
metadata and live representation union before allocation, within the current
caller's allowance and a 256 MiB phase ceiling. Metadata pages and accumulated
metadata are bounded. Historical operating limits never grant a current memory
allowance.

## Durable next-batch input

After a genuine complete artifact is accepted, run the following from the next
batch's managed checkout with the existing authorized GitHub identity:

```
node scripts/accepted-selected-checkpoint.mjs ChengshuLi/WorldAtlas PR_NUMBER REQUEST_ID REVIEWED_HEAD coordination/engineering/BATCH/FRESH_DIRECTORY
```

The parent batch directory must already exist. The fresh child directory must
not exist, including as a dangling symlink. This writes the exact accepted
`geography-artifact.zip` and then `selected-checkpoint.json` last. The latter is
an untrusted locator suitable for the next batch's `data/selected-checkpoint.json`:

```json
{
  "version": 1,
  "kind": "accepted-selected-checkpoint-locator-v1",
  "acceptance": {"pr_number": 123, "request_id": "the-existing-queue-request", "head": "the-reviewed-40-character-head"},
  "retained_artifact": {"path": "coordination/engineering/BATCH/FRESH_DIRECTORY/geography-artifact.zip"}
}
```

Keep both files in that batch's ordinary evidence. No per-batch executable or
accepted-checkpoint catalogue change is needed. After authenticating the original
accepted PR, run and successful job, acquisition checks a supplied retained ZIP
first against the original receipt's complete length and SHA-256. Only an absent
optional copy falls back to the exact artifact ID. A materialized nonordinary,
corrupt or unreadable copy refuses; remote permission and transport errors also
refuse. Unrelated artifacts and duplicate names do not affect this identity.

Fresh queue runs forward the pinned upload action's native artifact ID and ZIP
SHA-256, plus the checker's exact report length/hash, through job outputs. The
merge job downloads that ID, verifies the whole ZIP and report, and retains the
observed ZIP length in original custody. It never parses human job logs or lists
all run artifacts. Historical accepted receipts remain literal. Fresh runs made
with an older workflow lacking these outputs need normal redispatch after the
workflow update; there is no log-parser fallback.

When a checkpoint is actually used, its original source and complete bytes still
require authentication; the hint itself grants no authority.

## Initial reviewed seed

The first complete hosted artifact cannot depend on already having a hosted
checkpoint. The initial rollout therefore adds one typed
`accepted-derived-selected-checkpoint-v1` row to the existing executing trusted-main
catalogue, after the combined joint implementation and its retained clean proof
are actually accepted. This is a one-time bootstrap, not a per-batch registration
step. The row preserves the original archive pins. Current admission reads only its
certificate, derived facts/publication, native result, successful operating receipt,
executing policy and complete route census. Archived polygon products stay
unchanged and are never rerun or required as a current acceptance outcome.

The seed uses the same private derived-state admission as accepted artifacts,
with `trusted-main-derived-selected-checkpoint-v1` lineage. It does not claim
a hosted job receipt or cold acquisition. Current selectors, complete routes,
consumed policy and current memory allowance are still checked. Candidate data
cannot register itself in the executing catalogue.

The first selected batch using that seed must pass the actual native comparison and
the normal hosted job/merge boundary, which creates the first complete accepted
artifact. The following selected batch uses that artifact's normal merge receipt
and locator through `acquireAcceptedCheckpoint`; it requires no catalogue or
executable change. Those two real batch handoffs establish bootstrap and generic
advancement separately.

Warm admission runs before any optional full-bank prefetch. Only an explicit
cold decision starts that prefetch and the complete native comparison. An
authentication contradiction or access denial remains an error.

The joint entry's pre-import code/runtime gate uses current measured RSS plus
half of currently available memory after coordinator-declared future concurrent
growth. Availability already excludes resident parents and peers; no fixed
resident reservation is subtracted again. This bootstrap calculation stays in
the entry until every project import is authenticated, and parity controls bind
it to the native reader/preparation policy. The complete reader still accounts
for runtime, code, metadata, decoded inputs and outputs and checks actual RSS.
Retaining products after Node exits re-observes the Python consumer's current
allowance. These admission checks remain cooperative, not kernel quotas.

## Completion criterion

Synthetic transport/adverse controls establish the changed boundaries only.
Automatic advancement is complete only when a genuine accepted batch A supplies
batch B's actual baseline through the joint entry point, with original results,
lineage and measured timing retained and no cold authentication replay. The
initial reviewed seed and that actual adoption remain distinct from shipping
transport code.


## Reference metadata during append-only advancement

A retained checkpoint may predate a selected reference-metadata application.
The existing base reader authenticates the complete projection, original/current
hierarchies, source bodies and correction receipts before the checkpoint advances.
Every original scientific source identity, geometry, stable owner/index and native
contract must remain unchanged. Only those validated metadata roles refresh the
current route census; certificate source hashes and parent metadata are updated
from the actual complete current bodies. A later unchanged projection remains
bound by that census, including newly introduced projection and release paths.

Original native constructors may still name the native reference preceding the
metadata application. Their complete native contract and original output/input
joins remain required. The current envelope names the independently validated
metadata reference, while appended native intervals still undergo the existing
owner-zero, overlap and conservation checks. This reuses accepted qualification;
it does not turn a cold candidate-code report into an accepted checkpoint artifact
or claim that historical scientific predicates ran again.

## Finalizer adoption of a chosen checkpoint

The `finalize` handoff config may supply `accepted_checkpoint: {commit, path}`
pointing to the committed `selected-checkpoint.json` emitted by the acquisition
helper. Its exact retained ZIP must be committed at the locator's recorded path.
The finalizer reauthenticates the actual accepted PR, merge/tested trees, original
job and archive using the existing private acquisition API. The archive's
`derived-facts.json` must name the prior `config.selector` selection and the
accepted tested candidate. The newly emitted selection cannot accept itself.

When supplied, the exact chosen locator becomes a `selected-checkpoint.json`
product bound by the ordinary preparation receipt. The finalize CLI also adopts
those bytes automatically at `data/selected-checkpoint.json`; there is no manual
canonical-copy step. Before publication and again before atomic adoption it
requires the existing canonical file to equal the selector commit's original
file (or, for an identical `--resume`, the chosen output). Unexpected local edits,
links and incompatible checkpoints fail. If interrupted after batch publication,
`--resume` verifies every completed product and finishes canonical adoption.

The operand is optional. Existing deliveries can retain an authenticated compatible
checkpoint; age alone neither invalidates it nor requires a new acquisition.
Supplying an incompatible chosen checkpoint is an error, not a cold fallback.
The retained archive stays in batch custody outside package-consumed roles.
Existing selected-data classification and joint-entry scientific admission still
check the actual candidate's canonical locator and accepted lineage.

### Accepted coordinate result reuse

Hosted accepted checkpoint admission authenticates the complete archived
certificate and its publication hashes, supported schema, successful original
native report, accepted execution lineage and code, actual selector, live
ledger/registry/patch/manifest, reader routes and current policy. It does not
repeat the certificate's owner-by-primitive scientific computation.

This relies on the producing code, not on the native success label alone.
`selected-joint-entry.mjs` publishes only the certificate obtained from the
private `authenticateTransition` capability. At the cold or trusted-catalogue
seed boundary, `coordinateCheck` establishes complete owner/index/source and
effective-primitive identities. `qualifyTransition` preserves that baseline;
its private coordinate delta rejects changed old primitives and checks every new
primitive's owner index and base geometry before recomputing changed effective
hashes. Metadata projection checks every stable owner/index and each changed
source feature. The producer then binds that exact candidate certificate in its
facts and publication after the native comparison succeeds. Repeated deliveries
preserve this invariant inductively.

A trusted catalogue seed still runs the full coordinate check because it is not
an authenticated hosted accepted artifact. A fixture which corrupts an owner
index and then invents a fresh successful accepted job, publication and receipt
crosses the accepted-result trust boundary; that negative belongs at seed/cold
admission or producer construction. Tampering with the actual accepted bytes,
unsupported schemas, changed live inputs, changed executing code or incompatible
policy/selector remain admission failures. No caller-controlled skip option is
provided.

The retained South Africa PR #2427 artifact provides a historical check of this
contract: its original executing commit
`2013eb75fdaa4fdd7de311da09a5c0bd1fbf4f28` binds checkpoint code SHA256
`7f12b9fde333a0c17509f573fd92f507047912590faea57d6ca2b1c1e95f43f9`
and joint-entry SHA256
`bfe424cbe10dceb86469659f9bba9d7236133330981ca21e230a4e6e79d038d1`.
Those immutable bodies already implement the same owner/index preservation,
per-addition validation, effective-hash derivation and private publication path.

### Validated checkpoint projections

The private `checkpointAdditions` projection receives fully validated rows from
`readSelection`, or the equivalent privately reconstructed hosted accepted view.
`readSelection` authenticates the selected products and calls
`normaliseRetainedRepairLedger`, which checks each native component's complete
schema, base geometry/hash, owner, custody, interval ordering/count and bounds.
Projection dispatch therefore uses the validated representation tag instead of
repeating that entire validation for every iteration or ordinal lookup. All three
callers (cold qualification, accepted-derived admission and candidate transition)
follow this boundary; no caller-supplied index or projection callback enters it.

Rows remain source-backed and are freshly read on access. No geometry or result
cache survives store closure. The exported `deriveCoordinateDelta` still validates
arbitrary input components, and current-owner, old-row preservation, certificate,
source-authority and route checks remain separate requirements. Real admitted
projection controls reject interval rereads during projection alone, retain exact
values and closure refusal, and malformed committed ledgers fail normalization.

### Accepted ledger and rebind reuse

Hosted admission first authenticates the private accepted archive, successful
trusted producer/native result, complete live ledger/registry/patch/manifest
hashes, selector, policy eligibility and scientific routes. Only then does it
reconstruct the original normalized row cursor. The producing
`qualifyTransition` called the full ledger normalizer before publishing its
private transition; `selected-joint-entry` can publish only that genuine
transition after native success. This existing producer invariant supplies the
validated representation used by `checkpointAdditions`. Rechecking every old
polygon, component interval and row count adds no new proof for identical
accepted bytes.

Whole-body hashing, parsing and invocation-local storage remain. Cheap original
authority-binding reads still establish native/legacy classification; constructor
presence is not used as a substitute. Cold/catalogue seeds and every candidate
transition still normalize their entire ledger. They cannot inherit validation
from a caller flag, fabricated handle, stale archive or changed body. The public
delta validator and complete old-row preservation remain unchanged.

An accepted rebind retains its complete original certificate and all literal
product pins. Current consumers need its request and facts, so hosted admission
reads those operands only. The historical result, publication and operating
bodies remain provenance and route-bound, without being reopened. Cold seeds
and genuinely changed rebinds still read and validate all five product bodies.
No historical scientific result is regenerated or relabelled as a new execution.

### Qualified delta projection and the public boundary

After full candidate ledger normalization and source-authority/patch/rebind
qualification, the private delta uses validated native representation tags rather
than repeating native component validation for every cumulative row and new bound.
Duplicate identities, old projected-addition equality, current target/index/base
bindings, legacy geometry checks and exact effective hashes remain. In particular,
raw old-row equality cannot replace projected equality after a changed rebind.

The exported pure `deriveCoordinateDelta` still performs full component validation.
It snapshots only each sequence's outer iterated row references, then uses that
view for every lookup. A caller-controlled `.at()` or `entryAt` cannot substitute
a different primitive into the validated owner's bounds or hash. Declared counts
remain enforced; nested geometry and intervals retain their borrowed lifetime
guards. No public trust option, persistent cache or new capability is introduced.


### Exact qualified rows before candidate normalization

Candidate admission still authenticates and parses the complete current products.
Its private ledger admission checks the whole original scope, ordering and
all dispositions, then proves canonical equality of old raw rows and unchanged
whole authority entries against the genuine live baseline. Only rows satisfying
both identities reuse their already-established intrinsic semantics. Every new or
changed row receives the unchanged full public normalizer through a lazy residual
row/scope view; the complete current registry and v2 ledger binding are still
validated. The full normalized index borrows the candidate store, not a cache of
old geometry. No public skip option or new serialized authority is introduced.

Old-row and old-authority preservation demands stay after existing native-base
and scientific-route eligibility. Thus a valid changed old row is still rejected
for an otherwise eligible candidate, while an unsupported base preserves its
candidate-only cold fallback. Invalid new/changed rows still refuse before that
fallback. For a multiply malformed private candidate, the complete structural
scan may report a later scope/disposition error before an earlier geometry error;
both versions refuse. Public and cold/seed normalization remain unchanged.

Appended source qualification, exact original literals, patch union/disjointness,
current owner/target bindings, effective-reference digests, changed-rebind proof
and old projected-addition equality all remain required. Raw row identity alone
cannot approve changed projected legacy geometry. Baseline and successor handles
retain private invocation ownership; failed admission releases new stores while
leaving the baseline usable, and session release invalidates borrowed access.

For the retained seven-package transition this removes deep normalization of
5,180 old native and 93 old legacy effective rows. The 565 new native components
remain fully validated. The removed native pass covers 1,210,251 intervals and
527,088 base vertices (strict geometry plus canonical base hashing); parsing and
required whole-value equality/digests remain. These are static invocation and
cardinality counts, not measured time or memory savings.


### Reuse only the admitted private product digest

Derived checkpoint admission retains the complete canonical ledger/patch binding
comparison. The native store already computes those canonical digests while
admitting the whole authenticated body. A private invocation-local association
binds each frozen selected product view to that same live store, so recovering its
digest does not traverse every coordinate and interval again. This is not a raw
wire SHA substitution: whitespace, duplicate keys, numeric spelling and gzip
transport retain their separate whole-byte authentication and parsed semantics.

No caller-supplied digest or public value hash is trusted. New admissions still
parse and authenticate complete bodies, and changed/missing bindings refuse.
The association cannot outlive checkpoint release; failed candidates release only
their own stores. Public hashes still traverse their actual input and borrowed
cursors still refuse after their store closes. Catalogue seeds keep all existing
semantic qualification. Producer output bindings remain unchanged.

A bounded observation on the retained accepted #2445 baseline attributed 8.431
seconds to these two repeated canonical traversals (83,779,731 bytes) inside a
29.975-second admission on the accepted preimage. Hash instrumentation adds
observational overhead; this is not a paired speedup or an end-to-end estimate.
The parser's required canonical pass, native Float64 coordinates, edges/crossings,
retained metadata and exact output remain distinct size-dependent terms.

### Chunk-local native interval ingestion

A complete unsigned-decimal uint32 interval triple and its following delimiter
already present in the input's owned byte chunk can write the existing 12-byte
record directly. Its synchronous array visitor avoids a temporary three-element
JSON array, a tuple string and per-run promise dispatch. Overflow, signed zero,
exponents, decimal spellings, malformed tokens and chunk splits leave the parser
cursor untouched for the existing complete JSON grammar. Native domain errors
remain deferred until the final duplicate field wins; malformed syntax cannot be
erased by a later duplicate. Property names, strings and other metadata keep their
original parser. Producer-owned chunks are still snapshotted before use.

This changes neither storage format nor authority. Complete raw byte/hash
verification, required canonical passes, row order and owner bounds, ordinary
scratch cleanup and borrowed-store lifetimes remain. A bounded genuine control
with 64 rows and 448 additional local triples observed 448 fewer parsed arrays,
448 fewer tuple-string conversions and 4,480 fewer promise initializations;
those are allocation-event counts, not retained-byte or peak-memory savings.

One parser-only observation on accepted preimage `4d87bbff` admitted the retained
55,093,578-byte ledger and 28,686,153-byte patch in 20.731 seconds. Separately
measured canonical work accounted for 6.962 seconds; the 13.766-second residual
combines parsing, spooling and local Git transport. Instrumentation adds overhead,
and that residual is neither pure parser time nor a promised speedup. Both stores
retain disk-backed records and metadata; native Float64 geometry, edges/crossings,
current output and other eager inputs remain separate size-dependent terms.

### Private admitted component equality

The cumulative ledger parser already authenticates the complete input and records
an exact canonical SHA-256 for each component. Checkpoint admission now binds that
identity to each exact immutable component view in its private invocation session.
The old-row equality pass in transition normalization compares only these admitted
identities. A public digest field, another session, or an expired store cannot
supply this proof. A missing or changed row retains the existing full residual
normalization and append-only refusal; candidate body admission, authority and
route checks, and native comparison remain required.

A bounded observation on the authentic retained 2445 ledger (5,281 components)
measured the exact `valueSha` equality pass at 13.993 seconds and 1,271,006 reads,
versus 14.86 milliseconds and 5,292 component-descriptor reads for the already
admitted identities. Both passes agreed on every complete component. This is an
isolated equality-pass observation, not a whole qualification speedup claim.

### Preserve buffered writes at an unchanged logical end

The private native-store writer skips `reset(position)` only when `position`
already equals its complete logical end, including pending buffered bytes. This
is the first `runs` field of an ordinary row. Pending bytes still flush at the
existing capacity, canonical-readback and final-admission boundaries. A genuine
duplicate-key rewind still flushes and truncates, with the original write-error
and cleanup behavior. This changes neither stored formats nor admitted identities.

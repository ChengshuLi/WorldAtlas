# Prepare a delivery without rebuilding its coordination

`node scripts/prepare-delivery-handoff.mjs PHASE CONFIG DESTINATION [--resume]`
prepares immutable metadata in a managed checkout. The individual preparation phases
never run a scientific operator, accept a source, submit a review, commit, queue
or merge. Publish the real head, obtain
substantive independent review, then use the standard worker integration workflow.
Scientific source/native supervision, rebind, selected-reader and output checks remain authoritative.
Use Node 24 without loaders/preloads. Check storage with `local-workspace.mjs`
before preparation. Sparse checkouts need the two literal existing composition
and selected-neighbor helper paths imported by the command; no dataset directory
is required for the code. Missing immutable bodies fail with lazy fetch disabled.

## New finite resource profiles

New SOURCE/NATIVE issuance requires a `source-native-v2` request template and
explicit `requested_resources`, either at config level or per group:
`processing_allowance` contains positive safe integer `phaseBytes` and `rssBytes`;
`operating_limits` contains positive safe integer `rss_bytes`, `wall_seconds`,
`output_bytes`, `retained_bytes`, `log_bytes`, `monitor_bytes`, and `receipt_bytes`.
The requested values replace only these resource fields. No old 256 MiB reader,
1 GiB process, time, output, log or monitor limit is silently chosen by this tool.
The request's existing output reserve must be at least 131072 bytes and fit the requested reader phase; its sum with the 131072-byte operating margin must remain safe and fit the output limit. All other finite cross-bounds must fit. The
existing executing-code and supervisor descriptors, plus ordered
`operating_runtime.support_code` entries for `scripts/local-workspace.mjs` and
`scripts/worker-identity.mjs`, must match actual HEAD bytes. A new template must be
captured against the reviewed v2 operator/runtime; this command does not upgrade
old scientific code or claim that runtime/resource admission already happened.
The existing supervisor performs actual available-resource and runtime admission.

Historical examples explicitly select `compatibility: "literal-historical-v1"`.
That mode preserves the complete literal historical fields and forbids requested
resource overrides. It is for retained evidence/explicit compatibility, not the
default for newly issued work. Final v2 scientific execution remains separately
subject to the resource repair's acceptance and ordinary review.

## Configurations and explicit commit boundaries

Each config has `version: 1`. Input pins contain exact `commit`, `path`, ordinary
`mode: "100644"`, `git_blob_oid` (or the existing `blob` spelling), `bytes`, and
whole-file `sha256`. Git confirms the path/mode/OID before the bytes are consumed.
No proposed input is called accepted merely because a hash matches.

1. `requests`: `registry` is the existing accepted administrative-handoff registry.
   Each `groups` item names an `id`, `handoff_id`, pinned SOURCE `template`, exact
   `component_ids` and fresh operator `destination`. Top-level `component_ids`
   declares the complete delivery scope. Groups partition that scope without
   duplication. The whole accepted handoff determines filtered order. Each group
   stays inside its template's actual method/resource scope; the command preserves
   all other scientific, input, runtime and resource fields. It does not invent
   arbitrary batch sizes or classify a new scientific method. Outputs are ordered
   requests and their preparation index. Commit the requests before invoking the
   existing source supervisor separately.
2. `retain`: supply a committed `request` pin, actual local `terminal` receipt path
   and operator `output` directory. The command requires successful exit, no refusal,
   no remaining owned process or termination event, and the actual request binding.
   It verifies every publication product, including declared decoded gzip bytes,
   and joins published facts to that terminal/request. Actual JSONL records must
   match complete issued scope/order/counts; SOURCE targets and source-case bindings
   join the pinned whole handoff. Native retention requires the fixed complete asset
   roster, an independent effective-target join through the immutable SOURCE
   request and whole handoff, and actual inventory/ledger/patch/envelope agreement. For rebind output, also supply
   `custody` local paths for `code_source`, `issued_plan`, `stderr`, and `stdout`;
   raw code-source, issued-plan and stdout are joined to the immutable issued
   execution contract before provisional retention. These bodies remain provisional
   until the subsequent committed operating phase verifies full execution custody.
   Failed or partial runs remain
   failed. Originals are never overwritten. Commit retained bodies before the next
   phase; there are no fabricated future commit pins.
3. `native-requests`: each group has `id`, pinned native `template`, fresh
   `destination`, and `source` pins named `request`, `publication`, `facts`,
   `inventory`, and `operating`. Those are actual committed qualified SOURCE
   results. Native scope/baseline must agree with the source. Only these explicit
   source slots, source execution/runtime identity and destination are replaced;
   other template fields remain literal. Commit and use the existing native
   supervisor separately, then retain genuine results with the same phase.
4. `compose`: `registries` and `ledgers` are whole original pinned registry and
   v1-ledger arrays. It first verifies exact unique raw scope/row correspondence,
   then sorts only an in-memory composer view; original pins and issued request
   order remain untouched. The command unions consistent registry entries and calls the
   existing `composeRetainedLedgers` conservation implementation. It rejects
   duplicate original scopes and conflicting authorities. This makes metadata,
   not a qualification of a new source or a selected bank. Commit composition.
   For an already-qualified modern source-target delivery, instead supply pinned
   `selector`, original `rule_preimage` and `source_authority`, constructor-result `ledger`
   (`constructed-authority.json`, including `component_ids`, `ledger_rows` and
   `rule_sha256`), original `native_patch`, and `effective_release_id`. The selector
   discovers the actual prior cumulative metadata; no prior-role list or separately
   prepared singleton registry is needed. Compose forms the existing
   `retained-source-literal-additions` policy entry from those actual whole pins.
   The command preserves every inherited authority, literal row/exception, parent
   inventory, current rebind and target binding, rejects native-contract changes
   and any overlap with accepted additions, and emits `authority-registry.json`,
   `selected-ledger.json`, `patch.json` and `runtime-envelope.json` together.
   Flat public aliases come from the accepted envelope, not repository paths.
   This consumes retained qualified metadata; it does not repeat source/physical
   operators or prove actual current owner-zero. Commit those four products.
   To combine multiple independently qualified originals in that same operation,
   keep one `selector` and `effective_release_id`, and replace the singleton four
   pins with `authorities: [{rule_preimage, source_authority, ledger, native_patch},
   ...]`. The array must be nonempty; mixing it with singleton pins is rejected.
   Each original retains its own rule, source evidence and physical receipt joins.
   Checks reject duplicate authorities/components and overlap between new originals
   as well as the accepted patch. All original/source-evidence bodies share one
   aggregate preparation allowance. Registry and ledger conservation, one final
   interval union and one effective reference cover the complete combined result.
   Array order does not change the emitted bytes. No intermediate selector, new
   scientific qualification or source/physical rerun is introduced; final actual
   selected-reader and current-owner-zero acceptance remain separately required.
5. Existing rebind issuance and supervision remain separate. `rebind-operating`
   accepts actual `request`, `publication`, `terminal` pins and complete
   `execution_custody` pins (`code_source`, `terminal`, `stderr`, `stdout`,
   `issued_plan`), plus actual `facts` and `result` product pins. The existing
   `verifyCurrentRebindExecution` checks the complete joined custody against the
   independently pinned historical `CURRENT_REBIND_CODE` closure. Commit its
   operating output. `rebind-certificate` adds actual
   `facts`, `result`, and committed `operating` pins and produces the existing
   certificate shape only when the complete operating record equals the genuine
   terminal/custody and the shared execution validator accepts. It does not create a
   successful terminal or execute a rebind.
   Existing selected assembly is still a separate admitted execution.
6. `package`: supply composed `registry` and `ledger` pins, a `new_prefix` ending in
   `/`, optional `rebind` certificate, optional actual `selected_ledger`, and
   optional explicit final `outer_roles` pins. This promotes the working fixed-role
   constructor: new authority rule/binding, six original proof bodies, native proof
   and assets, source publication aliases, and three qualified source roles; then
   current rebind and external custody. It does not recursively append scientific
   replay operands or redeclare old authorities. Expected smoke cohorts/cells come
   from actual normalized ledger rows. `selected_ledger_sha256` remains null until
   the actual selected ledger conserves the rows and carries current bindings.
   Preserve prior package declarations. Compare against the actual completed reader
   inventory and run the existing package and consumer checks before delivery.
7. `finalize`: extend the package config with an immutable original `selector`
   (`data/ownership-selection.json`), accepted-baseline `package_inputs`
   (`.github/package-inputs.json`), real committed `sidecar`, `selected_ledger`
   and `rebind`. Choose the last known-good original selector; this phase preserves
   its base fields and nested insertion order rather than repairing an already
   reordered original. Sidecar registry/ledger, ledger rebind, patch and envelope
   descriptors must agree. Base-manifest and owner-roster hashes stay joined to the
   unchanged selector and its original native bounds. Encoded/decoded envelope
   descriptors must match; existing consumers still authenticate private graphs
   and scientific validity. The four final release roles are derived, not supplied
   through `outer_roles`. It stages `ownership-selection.json`,
   `package-inputs.json`, the fixed-role inventory and bound smoke expectations.
   To omit the separate sidecar construction/commit, supply `sidecar_output`
   (a fresh flat filename under `new_prefix`), committed `patch` and
   `runtime_envelope` pins instead of `sidecar`. Finalize retains base-manifest and
   owner-roster pins from the original selected sidecar and emits the new sidecar
   together with the selector/package/expectations. Its output identity has no
   invented commit. The modern composed `selected-ledger.json` pin serves as both
   `ledger` and `selected_ledger`; retain its actual `current_rebind` as `rebind`.
   With an original cumulative selector, finalize authenticates its sidecar and
   accepted registry, requires every inherited authority entry unchanged, and
   packages the exact added registry entries regardless of their original paths.
   Original rule/binding files need no receiving-prefix copies or preliminary
   input checkpoint. Their original paths still require exact accepted identities
   or authenticated local staging for issue-authorized adoption; `new_prefix` continues to constrain
   owned outputs. The complete accepted registry receives a retained 12x metadata
   carry charge before parsing. Standalone `package` and initial legacy finalize
   without an additive hook retain their existing prefix selection.
   It only replaces `additive_release` in the selector, preserving an already-final
   body's bytes. Keep the entire accepted package list verbatim as the prefix;
   append only genuinely new owned paths in stable sorted order. Existing paths
   retain their positions and must retain their exact accepted byte identities.
   Never use a globally sorted candidate list as the accepted baseline. The existing package definition
   validator rejects overlaps, missing optional declarations and unsafe paths.
   No tracked selector or package file is written: inspect and adopt these staged
   files in the delivery owner's ordinary commit/review flow. Repeating from the
   staged selector/package or using exact `--resume` must produce no changes.
   Scientific assembly, package builds and final delivery remain separate.

For finalization, use local staging by default:

```sh
node scripts/prepare-delivery-handoff.mjs finalize CONFIG .cache/delivery-handoff/final-UNIQUE
```

Adopt `ownership-selection.json` as `data/ownership-selection.json` and
`package-inputs.json` as `.github/package-inputs.json`. Adopt the emitted sidecar
and `selected-delivery-expectations.json` once at the configured receiving
`new_prefix`; retain the staged bundle locally for exact `--resume`. Do not also
commit that bundle under a `finalized/` directory. The delivery has one canonical,
current-ledger-bound expectations file. A duplicate authoritative copy is not a
prospective template and correctly retains full regression. This uses the existing
staging/adoption contract; it performs no automatic Git mutation.

Outputs use a fresh directory below `.cache/delivery-handoff/` or the caller's
issue-owned `coordination/engineering/<job>/`. All products are admitted before
mutation and created exclusively; `preparation.json` is written last. An explicit
`--resume` checks every product, the complete file inventory and original binding.
It never rewrites, repairs or blesses a partial directory. A changed config,
input, result, head or body needs a fresh vintage. Commit boundaries above are
intentional: immutable future pins cannot be predicted by bookkeeping.

## Reuse accepted methods; declare only consumed package roles

An ordinary data-only batch should reference applicable accepted helpers and their
immutable pins instead of copying unchanged executable scripts into a new packet.
Retain the new inputs/results and concise reproduction instructions; a new method
or changed executable still needs ordinary code review and its applicable tests.
Unchanged ordinary leaves reached through the existing fixed reader roles are
classified by exact accepted-baseline/candidate Git identity, regardless of suffix.
That test-selection decision does not replace whole-byte scientific validation or
current executed-code authentication.

`selected-delivery-expectations.json` is checkout-side test metadata read by the
existing smoke runner, not a runtime package input. Keep it in the reviewed packet,
but do not append it to `.github/package-inputs.json` merely because preparation
emitted it. Preserve prior declarations and append actual consumed roles using the
existing `finalizedPackageInputs` constructor, not a copied packet filename list.
New Markdown or text supporting evidence may use descriptive filenames in the
issue-owned scope. Selected-data eligibility still requires ordinary, bounded
UTF-8 text outside the actual reader/source roles and package inputs. Modified or
renamed files, executable/symlink modes, configuration text and consumed templates
retain full regression. Document titles do not establish or remove scientific
approval, and the final review/evidence gates still apply.

The existing `package` and `finalize` commands handle issued-rule and modern
`source-target-native-custody-v1` authorities, including mixed registries. After
completed selected assembly, use `finalize CONFIG DESTINATION` to produce the
selector, package definition, role inventory and smoke expectations directly;
no hand-written modern role list or separate package pass is needed.
Modern roles are the fixed whole-body reads of `qualifySourceTargetNativeAuthority`:
evidence/patch, catalogue, measured physical inputs/evidence/reproducer, native
latitudes/roster, declared family parts and optional membership index/lineage/parts.
All final sidecar assets are included. Nested GIS descriptors are not traversed,
and neither the physical reproducer nor scientific qualification runs here.
The existing direct or `additiveRelease`-wrapped envelope's flat public aliases
remain distinct from Git paths, with encoded/decoded identities preserved.
Smoke members use original-ledger `native_rows_sha256` for native-only components
and `geometry_sha256` for literal geometries. Existing accepted package policies,
selector ordering, custody/rebind, package/consumer and publication gates remain.

## Retained current13 metadata example

`coordination/engineering/delivery-handoff-20261011/current13-requests.json`,
`current13-native-requests.json` and `current13-package.json` pin the real accepted
whole GRC/COD handoffs, five original method/resource groups and current003 rebind.
They are historical construction examples, not execution instructions for today's
runtime or resource policy. The preparation checks need only their bounded exact
metadata bodies, not physical/GIS replay inputs. The package example leaves final
selection/assembly/reader checks pending. Do not call the prospective totals a
completed delivery. The separate `current13-finalize.json` example is pinned to
the corrected 79157664 selector, genuine release metadata, and accepted
9473d184 package baseline. The result preserves its exact 744-entry prefix and
appends 117 roles, reproducing the corrected d37abcd5 package. The old 79157664
sorted package remains historical build evidence, not an append-policy oracle.

```
node scripts/prepare-delivery-handoff.mjs requests coordination/engineering/delivery-handoff-20261011/current13-requests.json .cache/delivery-handoff/source-example-001
node scripts/prepare-delivery-handoff.mjs native-requests coordination/engineering/delivery-handoff-20261011/current13-native-requests.json .cache/delivery-handoff/native-example-001
node scripts/prepare-delivery-handoff.mjs package coordination/engineering/delivery-handoff-20261011/current13-package.json .cache/delivery-handoff/package-example-001
node scripts/prepare-delivery-handoff.mjs finalize coordination/engineering/delivery-handoff-20261011/current13-finalize.json .cache/delivery-handoff/final-example-001
node --test test/delivery-handoff.test.mjs
```

The metadata adapter uses the existing preparation byte/descriptor budget and
existing composition/ledger validators. Its JS fresh-directory writer provides the
same applicable ordinary-ancestor, exclusive-file and completion-last guarantees
as the Python `NewVintage` helper, with explicit byte-verified resume. Focused
controls cover that adapter; they do not establish geographic truth or operating
safety of a new scientific run. Unchanged original source/native/rebind validators
must still admit the final requests and results.

## Observed full-tree classifier limit

The current13 delivery merged separately as PR #1753 at
`ef834e2d90a9ca5d4cbd961a84a08dd156ae7944`. Its real 425-path tree passed
the path prefilter and runtime-role checks, but the complete selected-data
classifier reached its 16 MiB aggregate metadata admission bound while reading
added supporting JSON: 166 blobs and 16,638,841 bytes had been accounted. It
therefore used truthful full CI. The small finalizer/classifier controls here
prove their tested boundaries, not selected-data adoption by that complete tree.

Future handoffs should avoid copying unconsumed resource-control, preparation or
refusal JSON solely as bookkeeping; reference applicable retained immutable
evidence instead. Preserve every actually consumed role and required evidence.
Reducing unnecessary reads and making the trusted classifier allowance
configurable is a separately coordinated follow-on. This command does not
change that bound, its per-input security/identity checks, or the current delivery.

## What this automates and what still needs a decision

The accepted current13 metadata was replayed on the #1753 accepted ancestry:
ordered requests, native requests, composition, package projection, rebind
operating/certificate and finalization, plus genuine SOURCE/native/rebind
retention. Each phase completed and passed exact resume without executing an
operator. The earlier byte-equality checks remain applicable because these
command/test bodies and their immutable example inputs are unchanged.

- Request, retention and composition preparation: automated from explicit accepted
  whole pins and genuine terminal products. The caller supplies admitted method
  groups and finite resource profiles; no source acceptance is inferred.
- Package and selector finalization: automated, including literal accepted-prefix
  preservation, selector insertion order, collisions and exact resume.
- Review and integration use the actual PR/head, ordinary review comments and
  standard workflow dispatch. Delivery preparation creates no review packet or
  submission state and never approves itself.
- Grouping and parallel work: configs accept actual independent method/resource
  groups. Scheduling, source readiness and selecting which groups can run in
  parallel remain outside this command; it introduces no old-batch barrier.
- End-to-end speed: retained command timings show metadata preparation cost, and
  the delivery author used this CLI for two genuine v2 SOURCE request/retention
  handoffs. This is not a measured improvement in global gap closures per hour.

Actual immutable commit pins between phases, external scientific execution,
independent source/review authority and the existing serialized queue are manual
or existing-tool boundaries. No scheduler or automatic approval is hidden in the
preparation command. Its completed result establishes prepared outputs only, not
source acceptance, review, integration or publication.

## Recipe admission and exact-body materialization

Initial method admission is explicit. A `greedy-model` recipe supplies the
accepted registry locator, handoff IDs, admitted v2 SOURCE/NATIVE exemplar
locators, exact target-bank/native-operand mapping, physical locator metadata,
finite SOURCE/NATIVE resources, predecessor output allowances and the native
request byte allowance. It derives each ordered component scope from the whole
accepted handoff. It ignores old operational-batch labels. Whole encoded/decoded
inputs, code/modules, runtime/supervisor/support, both request copies and reserved
outputs/monitoring are modeled before splitting; singleton overflow refuses.
Native requests are modeled again after genuine SOURCE outputs replace reserved
predecessor slots. This prospective model does not replace current live memory,
installed runtime, acquisition or scientific operator admission.

`retained-groups` with `compatibility: literal-historical-v1` is explicitly a
historical replay. Its groups give immutable issued SOURCE/NATIVE exemplar
locators, never copied component lists. It preserves original destinations and
scopes. Newly rebound request preparation is shown separately from the original
requests that actually executed; retention and authorities always validate the
latter. A historical replay is not new source acceptance or a new execution.

Accepted source catalogues may be direct or nested under `original_source_custody`;
simultaneous aliases must agree. Physical locators may come from consumed inputs or
explicit `reused_whole_product_inputs` with `whole_body_consumed: false`. The original
handoff preserves that prior-consumption limit; generated ordinary acquisition pins
request later full-body reads. Conflicting source/product identities refuse.

The recipe index emits one transport/acquisition identity per whole encoded and
decoded body, with all compatible destinations.
The explicit `materialize` phase consumes its actual committed index:

```sh
node scripts/prepare-delivery-handoff.mjs materialize CONFIG DESTINATION
node scripts/prepare-delivery-handoff.mjs materialize CONFIG DESTINATION --resume
```

Its config contains `version: 1`, `recipe_index: {commit, path}` for the saved
`recipe-index.json`, and explicit finite `preparation_allowance: {phaseBytes,
rssBytes}`. It authenticates that whole index, reserves its deterministic completion
report/receipt, then shares the same budget across encoded/decoded inputs and
unique physical placements. Use the normal shared Git import/storage window for
actual acquisition. The existing exact-object prefetch importer retrieves missing
Git bodies once, consulting the existing `gh auth token` login ephemerally only
when a cold fetch occurs. Tokens are not persisted or printed; warm verification
needs no login lookup. Tracked source paths are never written. Only declared aliases
under `.cache/additive-native-gap-repair/delivery/<sha256>/` may be materialized.
Actual tree/OID/size/SHA and decoded identities are checked. Completed aliases are
reauthenticated and preserved on resume; corrupt or partially written aliases are
refused without repair. No source approval follows from successful acquisition.

The returned observation records actual fetch/import/write/resume counters and
acquisition milliseconds separately. The durable completion report is deterministic
and repeats byte-for-byte; it does not rewrite the first observation's counters.
Tests invoke actual local Git fetches with repeated immutable identities and
interrupted import/placement, as well as the plain-Node CLI. These small local
fixtures prove acquisition reuse, not a new fetch of the current13 GIS products.
Every scientific phase still authenticates and accounts for its complete inputs.
Physical-product paths come from the accepted handoff's original comparison or
its exact consumed locator metadata. Missing joins refuse, rather than guessing
from country names, old batches, or incomplete source records.

Run ordinary controls with `node --test test/delivery-handoff.test.mjs
test/delivery-handoff-advance.test.mjs`. The opt-in
`WORLDATLAS_DELIVERY_FIXTURE=1` explicitly registers the additional retained-fixture
suite rather than creating skipped tests in the default zero-skip regression. It
uses the already-retained immutable
current13 bodies for exact authority reproduction and the new 10+3 metadata
partition control. This requires only the named metadata commits/bodies, not a
scientific cache or GIS operands. Acceptance or revalidation relying on the
retained current13 proof must run `WORLDATLAS_DELIVERY_FIXTURE=1` and establish
zero skips; ordinary CI alone does not establish that proof. Absence of those
bodies is a fixture availability limit, never a successful replay.

## Typed measured evidence construction

```sh
node scripts/prepare-delivery-handoff.mjs evidence CONFIG DESTINATION
```

This uses the existing manifest and metric-binding schema. Supply a pinned
manifest `template` with baseline version 2 and empty `metrics`/`metric_bindings`,
plus nonempty `metric_sources`. Each source contains pinned `measurement` and
consumed `input`, the manifest's exact `input_file` selector, original
`evaluation_commit`, `vintage`, and explicit `fields` entries:

```json
{"id":"aus-native-zero_cell_components","field":"zero_cell_components","unit":"components","type":"integer"}
```

The fixed producer-field contract assigns components to `components`,
`source_compatible`, `assigned_components`, `zero_cell_components`,
`native_conflicts` and `source_exceptions`. Cell quantities use `native cells`;
elapsed values use seconds and byte quantities use bytes. Field-name substrings
never determine units. Optional unit/type assertions must match the fixed
contract. Unknown fields, missing/nonfinite/negative values, noninteger counts,
wrong units and conflicting input/result/evaluation bindings refuse before the
existing exclusive publication writer creates output. Original metric vintages
remain intact. This validates reporting, not the underlying geographic result.

## Explicit v2 subsets and immutable receipt qualification

The recipe constructor accepts `mode: "explicit-groups"`. Each group names
`id`, `handoff_id`, ordered `component_ids`, unique `target_ids`, and exact
`source_template` / `native_template` commit/path locators. The templates must
already be genuine `source-native-v2` requests with precisely that subset. The
whole accepted handoff remains pinned, while groups must be disjoint and their
target IDs must equal the accepted rows' stable target IDs. Unlike historical
`retained-groups`, a subset does not need to cover the entire accepted cohort.
There is no `compatibility` override. The existing resource model and issuance
checks still apply, including the actual HEAD code/support checks for new requests.

This mode preserves each template's source/native destination. For new science,
prepare templates with fresh candidate destinations and the admitted resource
configuration; the driver does not silently rename historical requests or rerun
operators. `destination_prefix` is used only by the existing greedy constructor.

### Inherited package read roles and committed restoration

Finalization derives package read roles from authenticated authority, original
custody and current release metadata. An out-of-prefix role already present at
the accepted package baseline must retain its exact ordinary mode, Git object,
size and SHA-256. Existing package declarations remain an unchanged prefix;
covered directory members are not redundantly appended.

Keep original cohort files at their canonical repository paths. Finalization emits
only flat delivery metadata products; it does not copy original bodies into its
local output tree. Whole-cohort retention keeps new owned originals available
without a second staging/adoption pass.

For historical or cross-prefix roles absent from the accepted package baseline,
supply an exact committed `restored_read_roles` snapshot:
`{"commit":"<exact commit>","paths":["<original role path>"]}`.
Declare the exact restored write paths in the ordinary issue scope. The snapshot
must preserve each original ordinary mode, Git object, size and SHA-256. Duplicate,
unbound, changed, nonordinary, missing or accepted-path-overwriting entries fail.
Absent roles without that explicit snapshot also fail. Original custody commits
remain unchanged; this readback grants no additional write scope.

Completion is written last. Exact `--resume` checks every flat output and its
configuration. Changed, foreign or incomplete output refuses. Historical completed
receipts retain their original bytes and consumers; use a fresh preparation
vintage after a changed output inventory rather than replacing an earlier run.

## Reusable source and modern native entries

The following entries replace per-cohort author programs. Unlike the metadata
phases above, `source` performs the existing source qualification and
`native-authority` executes the existing modern native constructor. Neither
changes the selected release, publishes a source approval, establishes current
owner-zero, or replaces independent scientific review and the final queue.
Archived original programs and receipts are preserved unchanged.

### Source cohorts using the retained Indonesia method

`node scripts/prepare-delivery-handoff.mjs source CONFIG DESTINATION [--resume]`
uses `scripts/qualify-source-cohort.py`; it does not generate a new Python
program. This is the retained Indonesia nine-family source method, **not** a
universal country classifier. Its complete IDN/MYS/PNG/TLS competitor-family
roster and native grid remain fixed. A different scientific method requires
separate review, rather than an arbitrary smaller family list in configuration.

The version-1 config contains `source`, `runtime_inventory` and the child
`processing_allowance` with positive `phaseBytes`/`rssBytes`. Omit the optional
parent `preparation_allowance` to use the existing finite fresh Node admission;
there is no second manually chosen cap to synchronize with the child. Explicit
parent limits remain supported and enforced. The declared complete output reserve
is admitted before the child starts. Actual parent RSS and aggregate metadata
checks remain active through publication; child resource limits remain separate.
This is a declared-output preflight, not a guarantee against later memory or I/O
changes. Actual products and the final preparation receipt are charged once at
publication; the preflight does not retain a duplicate aggregate charge.
`source` supplies exact scientific/current Git commits, complete whole-file
input pins and fixed-role paths; all target owner/ID/name/source-index/parent
and original metadata expectations; exact candidate-selector counts and its
whole pin; a retained physical-reproducer pin; resource limits and expected
runtime versions. The helper validates the complete source reconstruction,
lineage, native-centre membership and competing source/country witnesses.
Original topology/identity/geometry refusals and physical holds remain.

`runtime_inventory` names `python` and `files`, using absolute installed paths,
whole byte counts and SHA-256 hashes. The interpreter must be in that inventory.
Its configured virtual-environment path is retained while resolved file identity
is verified. Loaded file-backed Python modules and bundled scientific libraries
must be covered by the admitted inventory. This is not a hermetic OS-loader or
system-library closure. Keep this environment-specific input private and reuse
it only while the environment is unchanged; it is not a new per-cohort program.

`source` invokes the shared probe in fresh private staging, validates its complete
five-product inventory, then uses the existing immutable publication. Recorded
product links name the final destination, never the temporary staging directory.
Failure publishes no final output. The outputs are original-stage inputs,
cohort intervals/configuration, source qualification and execution receipt.
They retain source-only limits: successful source support is not physical or
native qualification. Checks are cooperative input/feature/time/output bounds;
no hard deadline or process-tree containment is claimed.

Explicit `--resume` verifies the complete output inventory, each whole product,
its execution/configuration binding, original immutable inputs and unchanged
shared entry/probe bytes. It reuses those original observations without rerunning
the source operator; changed or partial output is refused. Resume is custody
verification, not another scientific qualification or approval.

A replay can use a pinned `cohort-intervals-v1` retained cell set when the original
private `candidate-rows-v1` selector bytes are unavailable. The input records must
say which format was consumed. Equivalent cells/results do not establish the
original selector's byte identity, and new runtime/timing/path observations must
not replace the historical ones.

### Derive the canonical source-evidence baseline

`node scripts/prepare-delivery-handoff.mjs source-evidence CONFIG DESTINATION [--resume]`
replaces manual assembly of the accepted baseline block. The local configuration
contains `version: 1`, `selector: {commit, path}`, an explicit `source_evidence`
scientific payload, and optional ordinary `preparation_allowance`. The payload
uses the existing `source-target-native-evidence-v1` format; source/physical pins,
targets, geometry, exclusions and other scientific claims remain the operator's
explicit reviewed inputs.

The entry authenticates the selected sidecar, base manifest and runtime envelope,
then fills only `native_contract`, `native_latitudes`, `owner_roster` and
`base_reference`. Supplied versions of those fields must match exactly. The
normative contract is copied literally from the base manifest; Git mode/blob
metadata belongs only to separate custody pins. Raw and decoded latitude/owner
identities are verified before output. No template commit or scientific execution
is needed for this mechanical assembly.

Commit the emitted ordinary `source-evidence.json` once, then pass its immutable
locator to the existing `native-authority` command. This step does not qualify the
scientific claims or replace their review. Choosing a different same-body custody
commit can change evidence bytes and authority IDs: use normal qualification of
the new evidence, never relabel old constructor products. Exact resume uses the
existing configuration/output binding and safe writer.

### Modern native authority

`node scripts/prepare-delivery-handoff.mjs native-authority CONFIG DESTINATION [--resume]`
accepts exactly `version: 1`, `preparation_allowance`, `source_evidence` and
`native_patch`. The last two are exact `{commit, path}` locators, without
handwritten derived descriptors. It reuses `deliveryAuthorityReader` and
`constructOriginalAuthority`, including their existing admission, source/physical
joins and native coverage rules. It does not run the source or GSHHG producers.

Outputs are the original rule preimage, authority binding and
`constructor-result.json` containing every component and literal ledger row.
The result can be the modern composition input; it does not require an inline
constructor wrapper, separately assembled registry or copied physical/comparison
program. Current elapsed time, charged phase, process lifetime peak and native
cell count are emitted as observations, separately from deterministic products.
Native `--resume` repeats the existing qualification and refuses any changed
products/binding; it does not manufacture identical timing observations.

Use the shared modern `compose` and `finalize` entries after committing the actual
constructor outputs. This removes per-delivery executable creation; it does not
retroactively change an earlier mixed-code PR's CI profile. Source-only completion,
actual selected-consumer conservation, final package output and delivery timing
remain distinct claims.

### Read-only native coverage diagnostic

`node scripts/prepare-delivery-handoff.mjs native-diagnostic CONFIG DESTINATION [--resume]`
uses the same configuration and immutable input locators as `native-authority`.
It evaluates the existing authenticated source-target predicates and reports exact
requested, supported and held cells with reasons. Malformed or untrusted custody
still aborts. Outputs are only `native-diagnostic.json` and the ordinary
`preparation.json` receipt; no authority, ledger or qualification is emitted.
Exit status zero means screening completed, even if every requested cell is held.
Supported cells still require the unchanged qualification and delivery checks.

Use this entry to investigate an existing coverage refusal without creating a
bespoke producer or changing its predicates. It does not run source or physical
producers. Exact `--resume` repeats screening and verifies unchanged product bytes
through the existing safe publication path; timing observations can differ.

### Subsequent batch preparation

For an unchanged accepted command, change the scientific input pins/configuration,
not its executable implementation. Do not create and pre-review another constructor
wrapper, rebuild input descriptors by hand, split the returned receipt from its
ledger rows, or create a later join checkpoint. The complete constructor result is
already the `compose` input. Review the actual scientific inputs/results and final
delivery at their existing boundaries; changed code or method still needs relevant
independent review. Fresh resource admission and any selected execution contract
remain mandatory. Lightweight metadata follows shared Git/storage safeguards,
without acquiring a separate all-team GIS compute permission round.

For unchanged `compose` and `finalize`, reuse the original rule-preimage,
authority-binding, complete constructor-result and native-patch pins from the
qualified handoff. Run the stock phases without separate descriptor/config
attestation reviews, repeated whole-pin receipts or handoff acknowledgment gates.
The stock reader authenticates each ordinary commit/path, Git object, size and
whole-file hash; composition checks the original joins and conservation, and
finalization derives package read roles and checks canonical original identities.
Preserve the real commit boundaries between phases and every original scientific limit.

Keep one substantive independent actual-output scientific review for the delivery,
reusing original qualification reviews and applicable unchanged intermediate
evidence. Check the actual original-to-final scope, inherited and added rows/cells,
excluded holds and final metadata joins. Current-owner-zero, selected-consumer,
package/output checks, exact-head review and ordinary author/queue gates remain
required. A changed code path, scientific method or consequential input/result
claim still needs its relevant review; stock authentication alone is not that review.

Metadata `preparation_allowance` is optional: omission uses the existing finite
fresh Node admission, while an explicit phase/RSS request is freshly admitted and
enforced. Retain actual operating headroom, concurrent-growth reservations and
the command's byte/descriptor/RSS checks. Reuse applicable existing resource
evidence instead of producing another per-delivery role inventory or allowance
attestation; reassess bounds when changed inputs or execution make them inapplicable.
These defaults do not derive every external prospective runtime/OS/copy reserve
or grant future capacity. Scientific operator profiles and any required complete
resource accounting remain separate and unchanged.

The Tanjung191 input checkpoint at 2026-10-14T20:28:32Z and qualified checkpoint
at 20:40:59Z bracket 12m27s, while its preserved external execution lasted
1.581 seconds (20:35:53.305Z–20:35:54.886Z). That interval includes preparation,
coordination, review and preservation, not solely idle time; it is not a measured
saving from these commands. The original records and exact removable stages are
linked in issue #1920. A subsequent adopted package must establish actual delivery
elapsed and whether those intermediate stages were eliminated.

### Original physical source support

`node scripts/prepare-delivery-handoff.mjs physical CONFIG DESTINATION [--resume]`
uses the same admitted runtime, private staging, exclusive publication and resume
path as `source`, with a distinct physical phase in the shared Python helper.
It does not extend the Indonesia source classifier or create native authority.

The outer version-1 configuration has `physical`, `runtime_inventory` and
`processing_allowance`; omit optional `preparation_allowance` for fresh automatic
Node admission as described above. Explicit intentional parent limits remain
enforced and output reserve is checked before the child starts. `physical` contains exact
ordinary immutable `inputs` pins (commit, path, Git blob, bytes, SHA-256; compressed
pins additionally declare decoded bytes/SHA-256), `roles` for `stages`,
`transport`, `native_index` and `comparison`, and the metadata/native repository
prefixes. It also declares positive finite `resources.input_bytes`,
`resources.output_bytes`, `resources.deadline_seconds` and exact Python, NumPy,
Shapely and GEOS versions. The comparison method must match the preserved original
method SHA; configuration cannot introduce another scientific algorithm.

Authenticate every source metadata fragment before selection/ancestor closure.
Retain full dictionaries only for selected records and their complete ancestry,
rereading authenticated fragments for earlier ancestors when needed. Preserve
original duplicate-ID last-record and ever-match selection semantics, missing
parent handling, selected-cycle refusal and inclusive periodic bbox selection.
Do not infer a fixed memory bound from a small selected cohort.

Authenticate every native compressed/decoded fragment into one admitted complete
member buffer. No geometry is decoded until the whole member size/hash passes.
The native member remains whole; no source clipping, repaired polygon, altered
coordinates or sampled-byte substitute is introduced. Original comparison,
validity cache, query order and all unknown/support witnesses remain unchanged.
The old archived producers/helpers and previously qualified outputs stay intact.

The declared input-byte inventory still counts all authenticated inputs. Lower
live residency does not reduce logical bytes: the representative source/native
inventory exceeds 305 MB before target/code pins, even though measured optimized
peak is lower than the original implementation. Fresh same-process or separate
child admission must use the correct RSS credit; the shared Python launcher does
not credit resident Node bytes to its new child. Checks remain cooperative
boundaries, not an invented hard process-tree supervisor.

Outputs are `whole-target-support.json` with the original scientific schema and
`execution-receipt.json` binding actual inputs, program, runtime admission and
measured peak. The existing constructor can consume the committed support file
as `physical_evidence`, the unchanged target stages as `physical_input`, and the
actual executed shared helper as `physical_reproduction`. Its independent source,
native-cell and witness checks still apply. Exact whole-target support is not
country approval, native-cell qualification, ownership-zero proof or delivery.
`--resume` verifies complete original products, code/configuration and input pins
without repeating physical operations. Invalid or incomplete evidence refuses.

## Derived selected-delivery evidence

The existing `evidence` phase also accepts `delivery` instead of a full `template`: supply `version:1`, exact `baseline_commit`/`candidate_commit`, the owned `manifest_path`, `issue`, `worker_id`, exact `subject_ids`, original `qualified_constructor_pins` (`{id,pin}`), complete restoration-only `sources` with matching `id`/`original_pin`, and explicit `limits`. It derives the four actual ancestor selector/package/selected-ledger/registry baseline pins and the immutable candidate diff's whole-byte outputs, excluding the manifest itself. Every authenticated full constructor row/component roster must cover the exact added ledger rows without omission or duplication. Unmerged original constructors remain cited with their full pins; they cannot stand in for ancestor baseline hashes. Optional `pins` must exactly match the derived issue baseline map. Source citation terms, uncertainties, original authority metadata and any supplied `validation` controls remain explicit; omitted controls are not called passed. This mode permits `metric_sources:[]`, while supplied measurements and the original template path keep their existing typed contracts. It does not replace original source/native qualification or current-owner, conservation, scientific review, exact-head and integration gates. The byte inventory is limited reporting, not new scientific approval.

## Continue locally through the final evidence commit

An already-qualified modern delivery needs three actual local snapshots, but
not three pushes or separate operator waits. Run the existing commands and
ordinary scoped commits in one fail-fast shell sequence:

1. Run `compose CONFIG OWNED_COMPOSE_DIRECTORY` and commit its four sibling
   products. Retain the ordinary preparation receipt for exact resume; the next
   phase does not require it to be committed. Capture the actual local SHA with
   `compose_commit=$(git rev-parse HEAD)`.
2. For `finalize`, supply `version: 1` and exact `{commit, path}` locators for `selector`,
   `package_inputs`, `rebind` and `composition`; the last names the emitted
   `selected-ledger.json` at `$compose_commit`. Keep `new_prefix`,
   `sidecar_output` and explicit `preparation_allowance: {phaseBytes, rssBytes}`
   under the existing current resource admission.
   The compact route derives the fixed sibling pins; do not mix it with explicit
   derived product pins. Existing explicit configurations remain supported.
3. Run `finalize CONFIG .cache/delivery-handoff/final-UNIQUE` and use the existing
   [canonical staging/adoption contract](#configurations-and-explicit-commit-boundaries),
   including any [original-path restorations](#inherited-package-read-roles-and-committed-restoration).
   Finish intended candidate changes and commit the installed canonical tree.
   Capture `candidate_commit=$(git rev-parse HEAD)`. Run applicable checks at
   their ordinary working-tree or exact-commit boundaries.
4. Set `delivery.candidate_commit` in the existing evidence config to that SHA;
   retain the actual accepted baseline and explicit source citations, subjects
   and limits. Run `evidence CONFIG .cache/delivery-handoff/evidence-UNIQUE`,
   adopt its `evidence-quality.json`, then commit only the declared manifest.

The two SHAs can be passed by ordinary JSON serialization in the same shell.
Local Git bodies are sufficient; readers keep lazy fetching disabled. Keep the
generated evidence config and staging receipt local: evidence inventories the
preceding canonical snapshot and excludes only the manifest itself. Further
candidate edits require a new snapshot and refreshed evidence, without replaying
unchanged science.

Publish once after all three local commits. With the expected owned branch in
`branch`, retain and verify the actual final head:

```sh
final_head=$(git rev-parse HEAD)
git push origin "$final_head:refs/heads/$branch"
test "$(git ls-remote origin "refs/heads/$branch" | cut -f1)" = "$final_head"
```

Do not amend, flatten or rebase the pinned snapshots after deriving their
consumers. Preserve their ancestor chain and existing immutable-origin retention
requirements; a later integration squash does not establish retention. The
existing final exact-body fallback still needs its target, body and ancestry
checks. Normal substantive independent review covers the exact published final
head, followed by the existing integration flow.

On interruption, retain completed commits and staging, inspect actual Git state,
and use exact `--resume` with the unchanged configuration where applicable.
Changed or partial output still refuses; do not reset, overwrite or blindly
repeat the sequence. Existing commits and receipts provide recovery without a
new controller or journal.

In retained [MBD PR #1952](https://github.com/ChengshuLi/WorldAtlas/pull/1952),
the three stage publishers completed remote branch readback before exiting:
2026-10-15 04:39:18.907867Z, 04:46:46.809726Z and 04:50:26.217678Z.
The next finalizer admission was at 04:41:47.362Z. Local committed objects could
have fed the next steps without the intermediate remote readbacks. Separate
evidence-helper start and final-GET durations were not retained, so these records
do not establish minutes saved. Record subsequent adoption with the existing
delivery receipts; this sequence adds no reporting gate.

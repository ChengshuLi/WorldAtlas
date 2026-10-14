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
   `selector`, singleton `registry`, original constructor-result `ledger`
   (`constructed-authority.json`, including `component_ids`, `ledger_rows` and
   `rule_sha256`), original `native_patch`, and `effective_release_id`. The selector
   discovers the actual prior cumulative metadata; no prior-role list is needed.
   The command preserves every inherited authority, literal row/exception, parent
   inventory, current rebind and target binding, rejects native-contract changes
   and any overlap with accepted additions, and emits `authority-registry.json`,
   `selected-ledger.json`, `patch.json` and `runtime-envelope.json` together.
   Flat public aliases come from the accepted envelope, not repository paths.
   This consumes retained qualified metadata; it does not repeat source/physical
   operators or prove actual current owner-zero. Commit those four products.
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

### Inherited package read roles and explicit historical restoration

Finalization derives its package read roles from the authenticated authority,
original custody and current release metadata. An out-of-prefix role that exists
at the accepted package baseline must have the exact ordinary mode, Git object,
size and SHA-256 there. It need not already be listed in package inputs. Existing
package declarations are preserved as a prefix; covered directory members are
not redundantly appended. New output ownership is unchanged.

When an original consumed role is absent from that baseline, first reconcile its
exact restoration write path in the ordinary issue scope and commit the
unchanged original body. Then supply `restored_read_roles` in standalone finalize
configuration:
`{"commit":"<exact restoration commit>","paths":["<original role path>"]}`.
The finalizer checks each role against its original custody and that committed
snapshot; it does not restore files or grant write authority. Duplicate, unbound,
changed, nonordinary, missing or accepted-path-overwriting entries fail. Original
custody commits stay unchanged. All foreign-role identity failures are reported
together so the complete scope can be reconciled before retrying. This descriptor
is part of the immutable finalize input; changed input requires a fresh preparation
destination rather than replacing an existing completed product.

Standalone preparation retains its existing receipt/configuration contract.
Published legacy receipts remain supported by their existing consumers.

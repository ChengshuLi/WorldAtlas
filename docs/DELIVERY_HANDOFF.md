# Prepare a delivery without rebuilding its coordination

`node scripts/prepare-delivery-handoff.mjs PHASE CONFIG DESTINATION [--resume]`
prepares immutable metadata in a managed checkout. The individual preparation phases
never run a scientific operator, accept a source, submit a review, commit, queue
or merge. The optional automatic continuation below commits completed metadata. The later explicit `advance --submit-queue` option uses the existing
queue client only after genuine independent acceptance. The
existing issue claim, source/native supervisor, rebind issuer, selected reader,
evidence gate, independent reviewer and serialized queue retain their authority.
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
8. `review`: supply `repo`, `pr_number` and exact `head_sha`. Existing `gh` login is
   read once for read-only API calls. The command reads current PR, issue, claim,
   complete changed-file/rename scope and existing premerge evidence checks, then
   rereads current head/base/body/claim. The frozen packet carries required domains,
   complete inventory commitment, issue-contract and PR-body hashes, limitations,
   and existing queue/read-only resume command arguments. It is deliberately not a
   `worldatlas-review:v1` receipt and contains no approval or reviewer identity.
   A distinct reviewer inspects the exact head, current acceptance and evidence,
   and posts their own substantive receipt. Only then use the existing queue.

Outputs use a fresh directory below `.cache/delivery-handoff/` or the caller's
issue-owned `coordination/engineering/<job>/`. All products are admitted before
mutation and created exclusively; `preparation.json` is written last. An explicit
`--resume` checks every product, the complete file inventory and original binding.
It never rewrites, repairs or blesses a partial directory. A changed config,
input, result, head or body needs a fresh vintage. Commit boundaries above are
intentional: immutable future pins cannot be predicted by bookkeeping.

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
- Review handoff: current contract, complete scope, required domains and existing
  queue arguments are frozen together. The reviewer still performs substantive
  review and posts their own receipt. The command never asks again for authority
  it does not own, nor grants authority on behalf of that reviewer.
- Grouping and parallel work: configs accept actual independent method/resource
  groups. Scheduling, source readiness and selecting which groups can run in
  parallel remain outside this command; it introduces no old-batch barrier.
- End-to-end speed: retained command timings show metadata preparation cost, and
  the delivery author used this CLI for two genuine v2 SOURCE request/retention
  handoffs. This is not a measured improvement in global gap closures per hour.

Actual immutable commit pins between phases, external scientific execution,
independent source/review authority and the existing serialized queue are manual
or existing-tool boundaries. No scheduler or automatic approval is hidden in the
preparation command. The explicit continuation below binds these existing tools;
queue submission still needs the normal live authority and explicit option.

## Admitted recipe continuation (`advance` / `status`)

The same command can prepare the next supported metadata transition without
copying derived hashes, component IDs, or authority records between configs:

```sh
node scripts/prepare-delivery-handoff.mjs advance CONFIG DESTINATION
node scripts/prepare-delivery-handoff.mjs advance CONFIG DESTINATION --resume
node scripts/prepare-delivery-handoff.mjs status CONFIG DESTINATION
```

`CONFIG` has `version: 1`, an immutable `recipe: {commit, path}`, and optional
`observations`. Each invocation completes one available preparation stage or
reports the exact external input it is waiting for. Repeat the same command after
recording genuine publication/commit results. It never runs SOURCE, NATIVE,
rebind, assembly, builds, Git commits, or a reviewer. The finite sequence is recipe,
requests, SOURCE retention, native requests/retention, authority pairs/registry,
composition, rebind custody/certificate, package, finalization, live review
preparation and the existing merge queue. Actual operators and their required
per-phase input authentication remain separate.

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
decoded body, with all compatible destinations. `advance` only prepares this plan.
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

Observations supply only actual commit/path locators, not derived hashes:

- `template_commit`: actual commit containing generated recipe templates (new recipes).
- `sources` / `natives`: arrays of `{publication, terminal}` locators. Original
  facts determine request identity and saved group scope; unknown/duplicate groups fail.
- `authorities`: committed `{rule_preimage, source_authority}` locator pairs.
- `registry`: the committed registry input to composition. Keep this locator
  unchanged after the compose intent freezes, even when it contains only the new
  authorities and composition adds declared retained authorities.
- `composition`: the actual commit/path of the completed compose stage's
  `preparation.json`. Its authenticated receipt derives both combined-registry and
  composed-ledger pins and must match the original frozen input binding and whole
  output inventory. Commit the completed compose directory, then supply this one
  locator before rebind; no standalone composition command is needed.
- Historical configurations with an already-combined `registry` may retain their
  existing `composed_ledger` locator. It must match the saved composition bytes.
  If both forms are supplied, the legacy ledger must name the same derived pin.
- `operating`, `certificate`, `sidecar`: actual committed products. Each is joined
  to the deterministic preceding output.
- `rebind`: actual `publication`, `request`, `terminal` locators and complete
  `custody` locators for code_source, issued_plan, stdout and stderr.
- `review: {repo, pr_number}` is a top-level config field. The current head is
  read from GitHub, then the existing exact-head review packet is frozen.

For an already completed delivery, top-level `completed_delivery` supplies its
sidecar locator, composed-ledger locator and owned prefix. The command discovers
its original publications, authority pairs and current rebind custody from the
actual selected release. Every corresponding ordinary validator still runs.
The committed current13 recipe/config exercise this mode without scientific work.

The destination contains only immutable stage products and their ordinary
`preparation.json` receipts. For tracked `coordination/engineering/.../` products,
local runtime state lives separately under `.cache/delivery-handoff/runtime/`, in
a directory keyed by the exact product destination. Different recipes cannot
acquire independent ownership over the same products. Stage intents, completion
observations, timings, commit/queue identities, refresh records and locks stay in
that ignored runtime directory; none becomes a scientific input. Existing
`.cache/delivery-handoff/...` product destinations retain their co-located layout.

Current `advance --resume` automatically transfers an old tracked-prefix journal
once, under destination-wide cache ownership and the existing legacy lock. It
records and verifies the exact runtime inventory, copies raw bytes unchanged, and
retires only matching untracked originals. Published tracked journal records stay
unchanged at their original paths. Product paths, preparation receipts, timestamps,
operation IDs, commit objects and queue request IDs are preserved. Interrupted
copy/retirement resumes from the retained transfer inventory before any action.
The legacy lock is removed before the first action; cache ownership remains held,
so the stock clean executing-checkout boundary needs no manual runtime shuffling.
Continue migrated journals with the current driver: obsolete executables do not
understand the new cache lock. Preserve the runtime directory when moving or
releasing a workspace; it remains a local resume aid, never scientific authority.

An identical partial metadata write can resume only after its exact intent and
every existing byte agree. Foreign files,
changed recipe/observations, symlinks and altered completed bytes refuse. A crash
lock is recovered only when its same-host process is gone, with inspection and
new acquisition serialized by an exclusive short guard. A process killed inside
that guard leaves an explicit owner-reconciliation refusal; the guard is never
automatically reaped. A live or foreign owner is never displaced. `status` checks completed inventories without mutation.
Timings report preparation, acquisition, API wait, observed external wait and individual
operator-receipt durations separately. Parallel operator durations are not added
and called wall time; metadata speed is not global gap-closures/hour.

Queue preparation requires the existing live independent review/evidence gate,
including current scope/body/manifest/claim bindings and unresolved refusals.
Only explicit `advance ... --resume --submit-queue` invokes the existing queue
client. Its submission ID is durably written before POST. Every invocation with
an existing submission intent is observation-only, including a crash before an
uncertain POST. Missing registration never authorizes another submission. Follow
`MERGE_QUEUE_CLIENT.md` for explicit reconciliation; no approval is inferred from
local records, an unchanged head, or successful metadata preparation.

Optional `preparation_allowance: {phaseBytes, rssBytes}` in either command config
requests a finite metadata phase allowance, checked against current available
memory by the shared guard. Inputs, decoded representations, journal reads,
outputs and the completion receipt share admission. The authority reader carries
still-live outer metadata into its existing bounded qualification phases. There
is no separate 4KiB receipt cutoff; the ordinary whole-member bound and configured
aggregate budget apply to receipts as to other metadata. A receipt does not grant
approval regardless of its size.

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

## Optional same-target PR base metadata refresh

For a genuine refresh of an existing PR, set `review.refresh_base_metadata: true`
alongside its existing `repo` and `pr_number` in the advance config. The same
`advance` invocation then compares GitHub's reported PR base to one actual
`refs/heads/main` snapshot before freezing a new review packet. An already-current
base needs no write. A stale base permits one ordinary `PATCH {base: "main"}` only
for a complete open same-repository PR already targeting main. Exact head SHA,
head/target branch and repository identities, body and draft/ready state are
checked immediately before the call, in an independent readback and throughout
review freezing. This option cannot mark a draft ready, edit source branches,
change main or authorize the existing independent review/queue gates.

The existing advance journal writes `pr-base-refresh.json` before the external
call and records its outcome in its ordinary observations. Every invocation with
that intent is observation-only, including interruption before dispatch or loss
of the response. A complete readback may establish the intended state even when
the PATCH response was lost; it does not prove which actor changed the metadata.
Missing readback, state drift or a changed captured main refuses without another
PATCH. Preserve the original journal and reconcile the external outcome before
deciding on any new attempt. `status` remains read-only and reports the retained
intent and last observed outcome. Removing the opt-in does not turn an existing
intent into permission to retry.

A completed review packet is never silently rebound by this option. Its ordinary
frozen bindings and live queue checks still apply; a changed review vintage needs
fresh preparation and any required independent review. The PR API has no atomic
multi-field compare-and-swap guard, so the before/after checks rely on the existing
cooperative owner protocol and cannot exclude an out-of-band writer in between.

The retained PR #1762 fixture exercises the actually observed stale metadata
shape, plus exact draft preservation, denied/uncertain responses, interruption,
foreign targets, state drift and frozen-packet preservation. These controls do
not mutate a live PR or measure delivery throughput. Record adoption only when
the option handles the next genuinely required refresh.

The fresh-composition control uses the actual retained five new authority entries
and thirty predecessor entries as separate immutable inputs, then commits the
ordinary composer output and derives both pins from its genuine completion
receipt. The combined output preserves all original rows and exact accepted
registry bytes. This is metadata-transition proof, not another scientific run.
The need was found by tracing the current AUS continuation; no actual AUS refusal
was run, and its already-supported standalone compose route remains valid.

## Automatic mechanical continuation

```sh
node scripts/prepare-delivery-handoff.mjs advance CONFIG OWNED_DESTINATION --automatic
node scripts/prepare-delivery-handoff.mjs advance CONFIG OWNED_DESTINATION --automatic --resume
```

Add `automation: {"issue_number": YOUR_ISSUE}` to the existing config. The
existing recipe and observations remain authoritative. Automatic mode requires
the current chat's ready managed author workspace, exact engineering branch,
canonical unexpired claim, ready issue/dependencies and declared output ownership.
Use an issue-owned `coordination/engineering/.../` destination; `.cache` products
are never silently committed as repository evidence.

One invocation prepares and commits available stages, derives actual immutable
locators, and continues. Generated observations are `template_commit`, authority
pairs, registry, composition, operating and certificate. Explicit contradictory
observations refuse. SOURCE/NATIVE/rebind terminals and assembly still require
genuine outputs from their admitted existing tools; no future receipt, scientific
acceptance or operator execution is invented. The command reports the exact
missing input. A commit pause with available authenticated metadata is handled
automatically, rather than returned to the operator.

Commits contain only the complete authenticated stage products and preparation
receipt. Lock files and evolving journal observations are excluded. A durable
intent binds the parent, tree, complete ordinary-file inventory, Git identity and
operation ID before an atomic branch-ref update. Interruption after intent,
object creation or ref advancement resumes the same commit. Foreign branch/index
movement, hidden index edits, changed outputs and undeclared tree changes refuse;
unrelated files are preserved. The ordinary author claim is revalidated before
mutation. No worktree reset, automatic conflict resolution or credential/setup
change is performed.

Before the publication/review boundary, automatic mode fetches main with blobs
excluded and performs a cheap inherited-tree check. A needed refresh is an
ancestry-preserving two-parent merge whose tree must retain every author-changed
postimage, including deletions and modes. Conflicts, missing immutable objects,
untracked collisions and changes to an owned postimage stop publication. Exact
refresh intent/result and elapsed time are retained. A resume requires that same
captured main and head; changed targets require a fresh vintage or explicit
reconciliation. This is separate from the optional PR base-metadata PATCH.

Publication must use the actual refreshed head. If a PR is supplied but still
names an older head, review freezing refuses before evidence traversal. Creating
or updating the PR, installing final selection outputs and scientific operators
remain outside this metadata continuation. Independent substantive reviewer
acceptance remains mandatory; automatic continuation never approves itself.
Use the existing explicit `--submit-queue` only after that acceptance. An existing
queue submission ID still makes every resumed invocation observation-only.

Timing includes each automatic invocation's start, measured elapsed duration,
prepared-stage count and observed commit count, plus commit/refresh work and
explicit barrier reasons. API time is measured separately for each stage.
Unobserved interphase wall time remains unclassified, not proven idle. Do not add
overlapping wait/operator durations or infer gap closures per hour from controls.
Actual later batch adoption and end-to-end elapsed outcomes must be recorded on
the original issue.

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

## Claim and accepted-review stability

Claim mutation rereads compare parsed canonical reservation and blocker authority,
readiness/work contract, dependency state, linked PR identity/head/state/target,
and applicable geography ownership. Cosmetic timestamps, ordinary comments and
PR presentation fields do not invalidate a stable decision. A refusal names the
changed categories; it does not guess which field caused an older incident.
Fresh transition guards still enforce exclusivity and all existing readiness.

The accepted-review step uses the canonical scoped reservation, including
engineering `owned_paths`, with shared readiness/dependency/blocker validation
before and after evidence traversal. Revoked, foreign, expired or replaced claims
and changed scope/readiness fail. A benign renewal does not replace ownership.
The actual independent receipt, exact head/body/manifest and unresolved-review
gates remain authoritative.

### Explicit v2 subsets and immutable receipt continuation

`advance` also accepts a recipe with `mode: "explicit-groups"`. Each group names
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
The ordinary automatic entry commits recipe/request metadata, then waits for the
real external SOURCE and NATIVE terminals as before.

For stages already prepared by the standalone commands, `prepared_stages` in the
advance config can map an existing stage ID to:

```json
{
  "config": {"commit": "EXACT_ORIGINAL_CONFIG_COMMIT", "path": "original-config.json"},
  "receipt": {"commit": "EXACT_RECEIPT_COMMIT", "path": "original-stage/preparation.json"}
}
```

Use the actual original raw config, including its original local output paths.
The receipt's config hash is a hash of those bytes, not a newly serialized or
repinned substitute. The driver authenticates every immutable product and runs
the ordinary metadata constructor to establish applicability to the current
transition. It compares the entire output inventory and bytes, then records only
a reference in its local continuation journal. It neither copies the retained
products nor commits a duplicate stage. Resume rereads the same receipt; changed
or removed inputs, product drift, foreign stages and changed reuse bindings fail.
Missing stages continue through the existing constructor. Review and queue
decisions cannot be adopted. This route can reuse SOURCE/NATIVE retention receipts
before composition, without launching any scientific operator.

A retained stage whose regenerated metadata would differ is rejected, rather than
called complete. This includes changed consumed code for request issuance and
changed descriptor identities. Preserve the old evidence, supply its exact
original observations when still applicable, or prepare only the affected stage
in a fresh continuation. An explicitly supplied byte-identical commit alias for
a reused output is authenticated but kept exactly as supplied; it is not silently
repinned to the receipt's later commit.

For an already finalized standalone delivery, set `resume_finalized` to the same
config/receipt locator pair, referencing the existing `finalize` stage. Use an
explicit-v2 recipe whose templates name the actual original issued requests;
include its exact `selector`, `package_inputs`, `new_prefix` and retained registry
locators. This route verifies the complete new subset against the retained
SOURCE/NATIVE authorities, preserved registry entries, original composed rows,
genuine rebind execution custody and every final output. It then enters the
ordinary publication/independent-review boundary directly. No preceding stage
files or scientific evidence are minted. Do not combine it with `prepared_stages`
or the older `completed_delivery` discovery/replay option.

Neither receipt route establishes new science, CI acceptance, review acceptance
or actual subsequent delivery adoption. The frozen Norway B PR #1804 was checked
read-only as a real compatibility fixture; it was not changed or replayed. The
opt-in retained-object control is:

```sh
GIT_NO_LAZY_FETCH=1 WORLDATLAS_DELIVERY_V2_FIXTURE=1 node --test \
  --test-name-pattern='frozen Norway B' test/delivery-handoff-advance.test.mjs
```

It requires the referenced immutable Git objects locally, performs no fetch or
operator execution, and includes adverse scope/product controls. Default CI uses
bounded synthetic and actual-Git orchestration fixtures. Real later automatic
batch adoption and measured delivery timing remain open on issue #1785.

### Continue completed original SOURCE/NATIVE custody

A completed historical pair is not a new issuance recipe. The `advance` entry
also accepts a committed recipe with `mode: "completed-original-custody"`,
`version: 1`, an `id`, and the existing exact `selector`, `package_inputs`,
`retained_registries` and `new_prefix` context. Its nonempty `groups` contain only
`id`, ordered `component_ids`, `target_ids`, and exact commit/path locators named
`source_publication`, `native_publication` and `native_operating`.

Each continuation invokes the unchanged original-authority constructor on the
complete original publications, issued requests, facts, inventories, operating
custody and native assets. Declared component and target scopes must equal the
qualified original ledger. A literal historical request keeps its complete
source rule, original cohort roster, issued subset, resource/code identities,
geometry scope and remainder. There is no v1-to-v2 conversion, singleton source
fabrication or inference of whole-gap completion.

This route enters directly at real authority metadata preparation. It neither
issues SOURCE/NATIVE requests nor marks recipe, request or operator stages as
completed. It uses the existing interruption-safe journal and automatic commit
path for metadata actually prepared, then shares the ordinary authority registry,
composition, genuine current rebind, package/finalize, independent review and
queue barriers. It cannot be mixed with `resume_finalized`, `completed_delivery`
or `prepared_stages`; execution observations cannot replace its pinned custody.
Original qualification alone is never current selection approval.

The opt-in `WORLDATLAS_DELIVERY_ORIGINAL_FIXTURE=1` control reads the genuine
retained Native102 singleton within its original69-member corpus and preserves
its supported fragment, two original cells and nonempty remainder. Run with
`GIT_NO_LAZY_FETCH=1` and the exact objects already present. It performs no
SOURCE/NATIVE/rebind execution and claims no subsequent-batch adoption. Default
CI retains its bounded contract controls without fetching historical science.

### Inherited package read roles and explicit historical restoration

Finalization derives its package read roles from the authenticated authority,
original custody and current release metadata. An out-of-prefix role that exists
at the accepted package baseline must have the exact ordinary mode, Git object,
size and SHA-256 there. It need not already be listed in package inputs. Existing
package declarations are preserved as a prefix; covered directory members are
not redundantly appended. New output ownership is unchanged.

When an original consumed role is absent from that baseline, first reconcile its
exact restoration write path in the ordinary issue/claim scope and commit the
unchanged original body. Then supply `restored_read_roles` in standalone finalize
configuration, or `observations.restored_read_roles` for automatic continuation:
`{"commit":"<exact restoration commit>","paths":["<original role path>"]}`.
The finalizer checks each role against its original custody and that committed
snapshot; it does not restore files or grant write authority. Duplicate, unbound,
changed, nonordinary, missing or accepted-path-overwriting entries fail. Original
custody commits stay unchanged. All foreign-role identity failures are reported
together so the complete scope can be reconciled before retrying. This descriptor
is part of the immutable finalize-stage input; an already failed stage must keep
its original intent and use a truthful new preparation vintage for changed input.

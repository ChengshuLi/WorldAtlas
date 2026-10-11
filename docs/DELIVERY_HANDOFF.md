# Prepare a delivery without rebuilding its coordination

`node scripts/prepare-delivery-handoff.mjs PHASE CONFIG DESTINATION [--resume]`
prepares immutable metadata in a managed checkout. It never runs a scientific
operator, accepts a source, submits a review, commits, queues or merges. The
existing issue claim, source/native supervisor, rebind issuer, selected reader,
evidence gate, independent reviewer and serialized queue retain their authority.
Use Node 24 without loaders/preloads. Check storage with `local-workspace.mjs`
before preparation. Sparse checkouts need the two literal existing composition
and selected-neighbor helper paths imported by the command; no dataset directory
is required for the code. Missing immutable bodies fail with lazy fetch disabled.

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
   and joins published facts to that terminal/request. For rebind output, also supply
   `custody` local paths for `code_source`, `issued_plan`, `stderr`, and `stdout`;
   these genuine bodies are retained for the subsequent committed operating phase.
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
   `issued_plan`). Commit its operating output. `rebind-certificate` adds actual
   `facts`, `result`, and committed `operating` pins and produces the existing
   certificate shape. It does not create a successful terminal or execute a rebind.
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
7. `review`: supply `repo`, `pr_number` and exact `head_sha`. Existing `gh` login is
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
completed delivery.

```
node scripts/prepare-delivery-handoff.mjs requests coordination/engineering/delivery-handoff-20261011/current13-requests.json .cache/delivery-handoff/source-example-001
node scripts/prepare-delivery-handoff.mjs native-requests coordination/engineering/delivery-handoff-20261011/current13-native-requests.json .cache/delivery-handoff/native-example-001
node scripts/prepare-delivery-handoff.mjs package coordination/engineering/delivery-handoff-20261011/current13-package.json .cache/delivery-handoff/package-example-001
node --test test/delivery-handoff.test.mjs
```

The metadata adapter uses the existing preparation byte/descriptor budget and
existing composition/ledger validators. Its JS fresh-directory writer provides the
same applicable ordinary-ancestor, exclusive-file and completion-last guarantees
as the Python `NewVintage` helper, with explicit byte-verified resume. Focused
controls cover that adapter; they do not establish geographic truth or operating
safety of a new scientific run. Unchanged original source/native/rebind validators
must still admit the final requests and results.

# Trusted evidence and independent premerge review

This is a preventive gate, not proof that every fact is true. Read `EVIDENCE_QUALITY.md` and, for geographic measurements or generators, `EVIDENCE_GEOGRAPHY_HELPERS.md`. CI reads immutable Git blobs with trusted base code and a read-only token; it never executes a packet's reproduction commands. The integration workflow repeats applicable scientific byte checks using trusted main. Every PR still needs a separate worker's substantive review of its exact head. Existing regional approval, import and publisher gates remain in force.

## Ordinary engineering and scientific evidence

All PRs use the actual Git diff, applicable tests and a substantive PR review
or comment naming the exact head and distinct reviewer. Scientific work also
requires substantive source, geometry and release review where applicable.
Ordinary code, documentation, tooling and tested delivery metadata need no
`evidence_quality` declaration or synthetic scientific manifest. Neither path
requires a duplicate machine-format review receipt, file/hash inventory, prose
hashes or frozen review packet. The submitting operator reads the current head and
review, resolves every
outstanding objection and verifies the actual acceptance claims before dispatching
the standard integration workflow. There is no general comment parser or automatic
review approval; byte-check
success does not establish independent review, and an arbitrary comment does not
qualify. Shared-account reviewers are distinct agents, not distinct
authenticated GitHub principals.

Scientific source, geometry and release claims still need their actual supporting
records, original identities/vintages, consumed-input/result bindings and substantive
source interpretation. Declare a scientific manifest when the issue's result uses
those bindings; engineering code changes do not acquire one merely by changing
files. Unknown or changed consumed inputs still get the actual applicable checks.
An explicitly declared manifest remains checked, including retained engineering
contracts. Do not drop a scientific declaration to hide failed or missing proof.

`.github/evidence-policy.json` preserves the original activation/legacy rules for
geography and history work. Their new issues declare this field in the existing
`worldatlas-work:v1` scope; older issues retain their original scopes unless they
explicitly adopt it. Historical evidence and rollout inventories remain unchanged.

```json
"evidence_quality": {
  "version": 1,
  "manifest_path": "coordination/engineering/{job}/evidence-quality.json",
  "subject_ids": [],
  "pins": {},
  "review_kind": "code"
}
```

The example is a field fragment, not a replacement for max_prs, dependencies, mode or scope. `subject_ids` lists the exact geographic subjects if applicable; `pins` maps named release/scope/input hashes to actual baseline files. `review_kind` is `code`, `source`, `geometry` or `release`. Use geography's declared owned directory or history's campaign directory for those lanes. Engineering's `{job}` resolves to the branch ID, allowing a new owned manifest for each PR. The issue declares these scientific bindings before implementation; an as-yet unwritten manifest is not required to begin authoring. Missing issue creation timestamps cannot claim legacy status.

## Preparing declared scientific evidence

Start with `coordination/templates/evidence-v1.json`, replace placeholders, and retain an immutable baseline. Run the shared byte validator and checks relevant to changed acceptance claims. Bind actual scientific inputs, sources and claimed results. Git already supplies the complete immutable code/test/doc diff: those files need no duplicate output descriptors merely because they changed. Source restoration instructions remain explicit limits. Do not overwrite original sources; make a new vintage. The manifest adds:

- `change_receipts` is optional legacy bookkeeping, not required for new manifests. If supplied it must remain complete and truthful: one row per GitHub changed file, with `path`, GitHub `status`, and `previous_path` for renames. Non-added rows record `original_sha256` of the exact PR-base file; deletions additionally explain preservation in `reason`. Include renamed source paths in review scope. Baseline descriptors for retained original evidence use `role: "original-source"`.
- `metric_bindings`: one row per numeric metric with `metric_id`, actual output `path`, and RFC 6901 `json_pointer` to its value. Generated results must agree with the ledger and summaries. A current metric uses the actual PR-base commit; older frozen results must be labeled baseline or archived, not current. Prose interpretation requires human/worker review.
- Outputs containing generated tables declare `role: "generated-table"` and a `rendered_tables` row inventory: `path`, and rows with `metric_id`, one-based `line`, exact line `template` containing `{value}`, `decimals` (0–12), and optional `scale` (1 or 100 for a fraction expressed as percent). The checker verifies the actual rendered lines against the ledger. Review must catch undeclared tables and unsupported prose; this is not a universal natural-language fact parser.
- Every method declares kind `code`, `source`, `geography`, `generator` or `measurement`. Geographic methods use `helper_version: "worldatlas-evidence-geometry-v1"` and the exact shared helper method policy. Generator methods use `kind: "generator"` and `helper_version: "worldatlas-evidence-preparation-v1"`. Measurement methods use `kind: "measurement"`.
- `validation` is optional retained control evidence, not a requirement to create JSON wrappers for tests. Applicable positive/adverse tests still establish changed behavior and independent review checks their substance. Cite actual test output in the PR/review; reuse applicable unchanged tests. Repeat a full execution only when needed for a changed repeatability claim, invalidated evidence or explicit acceptance. If supplied, each row has `method_id`, `kind`, `outcome: "passed"`, and `evidence_path` referring to a hashed JSON output with the same first three fields. Reproducibility outputs also record equal `run_one_sha256` and `run_two_sha256`. Review must assess whether checks are meaningful; typed receipts cannot prove an experiment was honestly performed. Omitting optional metadata never authorizes hiding a failed check or claiming unverified correctness.

The gate checks scientific file hashes, subjects, supported vintages, method policy and result bindings; complete Git change accounting and exact-head review remain required. Existing v1 scientific manifests remain supported, including validation of their supplied optional scientific fields. Exact reviewed encoded/decoded lengths establish finite per-file and complete-packet bounds, with safe-integer/overflow admission before reads or decompression. Actual lengths and hashes must match, and fresh complete immutable Git trees must agree with the manifest before hosted acquisition. Descriptors remain bounded to 512. Actual memory, storage, provider and job limits still apply; large data may require streaming or a reviewed execution approach. The 272 MiB in-memory cache, timeouts and legacy unplanned-reader/manifest-envelope operating guards remain unchanged. Git prefetch streams the admitted exact-object inventory to disk without an aggregate byte cutoff; whole-body type/length/OID verification and exact per-body buffers remain mandatory. A premerge manifest cannot certify a deployment or geographic approval. Initial research may be complete with unresolved facts; it cannot close a correction that remains unresolved.

### Multiple historical file vintages

For an immutable packet whose original inputs and later retained evidence cannot
be represented by one commit, use the opt-in `baseline.version: 2` format in
[EVIDENCE_QUALITY.md](EVIDENCE_QUALITY.md#historical-files-from-multiple-commits).
The trusted gate verifies each distinct commit against the actual PR base before
loading its files. Review the original issue pins, exact `(commit, path)` bindings,
subject/record references and metric input selectors separately from evaluation
vintages. Preserve the old helper and additionally inventory actual executed code;
a descriptor alone does not prove execution. Missing ancestry, ambiguous bindings
or an unlisted executed helper must be repaired without replacing original pins.
This changes evidence representation only, not scientific or production approval.

### Identity-only source subjects already recorded in prior evidence

For a geography reproduction packet scoped to native source IDs, a new registry must not
be called an ancestor baseline. The ordinary `baseline.subject_files` path still requires
the actual subjects in pinned baseline GeoJSON. An alternative is a **limited prior-evidence
inventory**, where an existing ancestor-main record already lists the exact native roster:

```json
"subject_inventory": {
  "version": 1,
  "basis": "prior-evidence",
  "path": "data/regional-review/EXISTING-PACKET/cd-assessments.json",
  "json_pointer": "/exact_subjects",
  "id_prefix": "StatisticsCanada:2021:CD:",
  "source_property": "CDUID",
  "source_id": "statcan-2021-census-geography",
  "registry_path": "research/geography/OWNED-PACKET/source-subject-registry.geojson"
}
```

This field belongs inside `baseline`, instead of `subject_files`. Pin the original record
in `baseline.files` at a truthful ancestor commit; cite `source_id` in the source inventory.
The pointer must resolve to unique native string IDs whose prefixed roster exactly equals
the issue's subjects. List the new registry as a candidate output. Its features must be
identity-only (`geometry: null`), with the exact prefixed `id`, matching `properties.id`,
`source_value`, and `source_property`. Invented/duplicate subjects, mixed authority paths,
unlisted inputs/outputs and geometric registries fail. Normal hashes, byte limits, change
receipts, result-vintage checks, ancestry and independent review remain required.

The checker always reports a limitation: this verifies agreement with **retained prior
evidence**, not independent membership or geometry in the original source. A reviewer must
retain that limit and verify the prior record's source role/vintage; this option must not
be described as certified source extraction or regional approval. Do not use it to silently
replace an original-source geometry claim. Oversized originals remain lawful restoration
or independently reviewed partitioning work; no size limit is widened here.

For PR #678 / issue #667, the pre-existing record is
`data/regional-review/bc-administrative-remainders-followup-2026/cd-assessments.json`
at `24629e5918a144a1979db80ba7012baea42036e7`, with native IDs under `/exact_subjects`.
The GEO owner must retain all original evidence, move newly created copies/extracts/registry
out of `baseline.files` into candidate source/output descriptors, bind baseline pins only
to real files at the ancestor, and refresh affected metric vintages/bindings honestly.
If the actual reviewed metric inputs differ from the chosen ancestor, retain those results
as archived with their true evaluation commit; do not merely relabel them current. Then run
the trusted hosted gate and obtain a fresh exact-head review including its new limits.

Local self-check:

```sh
node scripts/evidence-quality.mjs PATH/TO/evidence-quality.json
node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs
```

The trusted CI `evidence` job publishes `evidence-check.json`, stating checked scope and unavailable evidence. It runs with read-only rights. Its success is mechanical validation, not an independent review.

## Independent reviewer

Request one coherent PR review from a distinct worker. A reviewer must inspect actual changes, sources, methods, applicable tests, linked acceptance criteria and preservation/release implications; green CI or an author's claims are insufficient. Do not claim the author's issue or edit its scope. If no reviewer is available, the merge waits. Implementation review and source/factual review are separate domains. Limited primary-source access must appear in both the reviewer limits and accepted-with-limits source outcome.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, check storage before generation/installations, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

Before accepting a consequential claim, follow it to the final evidence using
[AUDIT_FAILURE_PREVENTION.md](AUDIT_FAILURE_PREVENTION.md#follow-a-claim-through-the-final-evidence).
Independently inspect the report and control writers, actual comparison records,
combined budgets and inherited evidence as applicable; acceptance of a main
computation does not cover those boundaries automatically. In the existing domain
scope, identify actual entry points/altered inputs and observations, separating
executed bounded checks from unavailable full-source/GIS experiments. Required
unverified completion claims remain unaccepted. Do not require irrelevant probes
or turn source-only CI into full regression.

### Arrange the reviewer

The engineering, geography and history prompts authorize review delegation. When sub-agents are available, launch a distinct review agent, preferably with fresh/minimal context rather than the author's full reasoning history. Supply the PR URL, exact head SHA, issue URL, evidence-manifest path, and this guide. A reviewer can inspect diffs/immutable blobs through GitHub APIs or Git without a checkout. When local reproduction/tests need one, use the bounded detached review slot described in LOCAL_WORKSPACES.md and release it after posting the result, preserving unique outputs first. The reviewer independently reads repository guidance, diffs and original evidence; the author's explanation is context, not validation. Do not select a different model from the user's choice without authorization.

A review sub-agent in the author's chat is permitted. It provides a separate examination, but is weaker separation than a different reviewer chat and is not an authenticated independent security principal. Do not describe it as a separate chat. The reviewer does not reserve the author's issue, edit its branch, merge, deploy or import anything.

Copy-ready task (replace placeholders):

> Review PR URL at exact HEAD_SHA for ISSUE_URL. Read AGENTS.md, docs/WORKER_COORDINATION.md, docs/LOCAL_WORKSPACES.md, docs/AUTHOR_PREFLIGHT.md, docs/AUDIT_FAILURE_PREVENTION.md and docs/PREMERGE_EVIDENCE_REVIEW.md from current main, plus relevant lane/data contracts. Follow consequential claims through their actual inputs, computation, report/control writers and final evidence. Select independent bounded probes for applicable field/unit transfer, comparison products, writer safety, combined budgets and inherited/source claims; distinguish executed checks from unavailable full-source/GIS proof in the existing domain scope. Use API/blob inspection without a checkout when sufficient; when local execution is needed, use the managed sparse detached review slot, include all required inputs, check disk before reproduction, and release the slot when the review is durably posted. Inspect every changed file and renamed original, linked acceptance criteria, actual sources/methods/controls, evidence manifest MANIFEST_PATH, checks and identity/history/release preservation. Inspect author claims and CI evidence independently. Reuse applicable retained tests instead of repeating unchanged expensive executions or creating ceremonial control files; renew relevant review for changed inputs/behavior. Use a unique reviewer worker ID distinct from AUTHOR_WORKER_ID. Do not claim the issue or edit/merge/deploy/import. Report specific findings and actual validation limits. Post one substantive PR review or ordinary comment naming the exact head and distinct worker. For scientific work inspect the declared manifest, original inputs/results and applicable domains; retain every actual validation/source limit in the review. Use accepted-with-limits only where policy permits it. If access or evidence prevents acceptance, report the blocker without claiming approval.

The author addresses findings and requests review of any updated head before using the normal merge queue. Authors reconcile the latest current-head review from every reviewer before submission; acceptance by one reviewer cannot override another reviewer's unresolved objection. A new head requires renewed relevant review of earlier objections, not merely reliance on their previous-head reviews becoming ineligible. Scoped resolution comments do not replace the required whole-PR acceptance. If no review sub-agent is available, ask another available worker on the PR. Record unavailable review/access on the linked issue; continue independent work within the existing owned scope if possible, otherwise leave a durable checkpoint and safely release or hand over. Do not ask the user to manually launch a reviewer when an available review agent can do it. No reviewer means no merge, not an exception or a self-review under another ID.

The submitting operator verifies that the actual review is substantive, names the
current head and a worker distinct from the author, covers the consequential
implementation/source/geometry/release claims and retains applicable evidence
limits. Resolve every reviewer's outstanding objection; a green byte-check job,
arbitrary comment or stale-head review cannot substitute for that examination.
Scientific manifests still bind original inputs and results mechanically. The
standard queue rereads the head, checks, issue contract and scientific bytes before
a SHA-guarded squash merge; it does not certify the operator's review judgment.

The separate physical-water exception in [GEOGRAPHIC_GAP_ADJUDICATION.md](GEOGRAPHIC_GAP_ADJUDICATION.md)
retains its structured exact-dossier source decision, latest-decision checks and
full review binding. Voluntary legacy partition review contracts likewise retain
their recorded bindings. Those specialized approval records are not additional
general PR-review receipts. Preserve historical comments and evidence unchanged.
No provider changes, deployment or live import occurs as part of premerge review.

## Activation proof and limitations

Activation must follow a merged reporting implementation, actual hosted report results, positive and negative real-format fixtures, and an inventory of current claimed/open work. Record the timestamp, decision and checks in the activation PR; the earlier implementation PR uses `Refs #627`. The final activation PR may use `Closes #627` only after these checks. Unit tests use synthetic data and mocked read-only API responses, never production merge mutations. Neither this gate nor moderator review eliminates all factual errors: unavailable sources and unexecuted reproduction remain explicit limitations.

Regression controls reflect concrete moderator findings: #579's malformed hierarchy pin, #580's swapped longitude/latitude transform, #600's conflicting narrative/generated figures, #614's overwritten timestamp-dependent extracts, and #619's inferred containing-file inventory. The manifest and shared-helper tests cover their failure patterns without special country rules. #591's restoration-pin mismatch additionally motivates independent provenance review: a hash alone cannot establish which upstream release exists. These safeguards do not close the individual source/correction issues.

## Acceptance and disposition

Read ISSUE_LIFECYCLE.md. Review the original acceptance and PR completion/continuation/wait independently of implementation acceptance. Before a final allowed partial PR, check where actual unfinished obligations go; an explicit original-issue wait is valid and no duplicate follow-up is forced. Initial research may close with permitted unknowns; correction/production acceptance may not.

Review substantive acceptance, scope and completion/continuation changes directly;
request renewed relevant review when they change. Ordinary progress comments do
not invalidate a review. No duplicate issue/PR-body hashes or file-inventory
commitments are required. The exact commit already identifies the reviewed code;
scientific manifests bind the actual inputs and results. Preserve historical
comments and records without copying their obsolete bookkeeping into new work.

Read docs/AUDIT_FAILURE_PREVENTION.md on current main before the next job or review. Identify the consequential acceptance claims and independently test applicable consumed-input/code, identity/join, source/method, safe-reproduction, nonvacuous-control and operating-limit invariants. Use shared evidence helpers or an explicitly reviewed equivalent; reviewers derive expectations from original acceptance and independent records before relying on author tests. Exercise real entry points and adjacent paths for corrective PRs; record unexecuted proof as a limit. Keep exact-head review, original evidence, scientific/publication gates and focused research CI. Adoption requires actual subsequent handoffs, not just this prompt edit.

## Author preparation

Read [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) for the author's preparation and
actual local-versus-hosted check boundaries. Reviewers still derive expectations
from original acceptance and independent reference records; author controls and
byte-only local success do not replace substantive exact-head review. Select only
applicable failure families and preserve focused source-only CI.

Ordinary code and source authoring do not require an expiring GitHub lease. Scientific manifests retain their actual author identity, and their exact-head reviewer must be a distinct worker. Shared-account worker IDs provide cooperative attribution, not authenticated personal identities; the operator verifies the independent review. Issue linkage, declared paths, source/result bytes and domain review remain required.

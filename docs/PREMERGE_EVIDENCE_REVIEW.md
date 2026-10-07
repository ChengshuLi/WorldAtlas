# Trusted evidence and independent premerge review

This is a preventive gate, not proof that every fact is true. Read `EVIDENCE_QUALITY.md` and, for geographic measurements or generators, `EVIDENCE_GEOGRAPHY_HELPERS.md`. CI reads immutable Git blobs with trusted base code and a read-only token; it never executes a packet's reproduction commands. The merge queue repeats byte checks using trusted main, then requires a separate worker's review of the exact head. Existing regional approval, import and publisher gates remain in force.

## Issue creation and rollout

`.github/evidence-policy.json` is authoritative. Initially `report-only` reports failures without changing existing merge rules. Activation changes it to `enforce-new` with an explicit UTC timestamp. Issues created before that timestamp retain their original scopes unless they explicitly adopt `evidence_quality`. This exception preserves completed evidence and currently claimed work; it does not endorse legacy findings. The inventory records current claims, open PRs and decisions; deficiencies remain bounded corrective work under #624, not silent invalidation or blanket geographic approval. New issues must declare this additive field inside their existing `worldatlas-work:v1` JSON:

```json
"evidence_quality": {
  "version": 1,
  "manifest_path": "coordination/engineering/{job}/evidence-quality.json",
  "subject_ids": [],
  "pins": {},
  "review_kind": "code"
}
```

The example is a field fragment, not a replacement for max_prs, dependencies, mode or scope. `subject_ids` lists the exact geographic subjects if applicable; `pins` maps named release/scope/input hashes to actual baseline files. `review_kind` is `code`, `source`, `geometry` or `release`. Use geography's declared owned directory or history's campaign directory for those lanes. Engineering's `{job}` resolves to the branch ID, allowing a new owned manifest for each PR. A claim checks this declaration before implementation; it does not require an as-yet unwritten manifest. Missing issue creation timestamps cannot claim legacy status.

## Preparing each PR

Start with `coordination/templates/evidence-v1.json`, replace placeholders, and retain an immutable baseline. Run the shared byte validator and scientific controls. List every changed ordinary file, including code, tests and documentation, as an output or newly retained source (the manifest itself is excluded from its own hash). Source restoration instructions remain explicit limits. Do not overwrite original sources; make a new vintage. The manifest adds:

- `change_receipts`: one row per GitHub changed file, with `path`, GitHub `status`, and `previous_path` for renames. Non-added rows record `original_sha256` of the exact PR-base file; deletions additionally explain preservation in `reason`. Include renamed source paths in review scope. Baseline descriptors for retained original evidence use `role: "original-source"`.
- `metric_bindings`: one row per numeric metric with `metric_id`, actual output `path`, and RFC 6901 `json_pointer` to its value. Generated results must agree with the ledger and summaries. A current metric uses the actual PR-base commit; older frozen results must be labeled baseline or archived, not current. Prose interpretation requires human/worker review.
- Outputs containing generated tables declare `role: "generated-table"` and a `rendered_tables` row inventory: `path`, and rows with `metric_id`, one-based `line`, exact line `template` containing `{value}`, `decimals` (0–12), and optional `scale` (1 or 100 for a fraction expressed as percent). The checker verifies the actual rendered lines against the ledger. Review must catch undeclared tables and unsupported prose; this is not a universal natural-language fact parser.
- Every method declares kind `code`, `source`, `geography`, `generator` or `measurement`. Geographic methods use `helper_version: "worldatlas-evidence-geometry-v1"` and the exact shared helper method policy. Generator methods use `kind: "generator"` and `helper_version: "worldatlas-evidence-preparation-v1"`. Measurement methods use `kind: "measurement"`.
- `validation`: methods of these kinds require positive and negative controls. Generators also require two-run reproducibility. Each row has `method_id`, `kind`, `outcome: "passed"`, and `evidence_path` referring to a hashed JSON output with the same first three fields. Reproducibility outputs also record equal `run_one_sha256` and `run_two_sha256`. Review must assess whether controls are meaningful; typed receipts cannot prove an experiment was honestly performed.

The gate checks hashes, files, subjects, supported vintages, method policy, change accounting and result bindings. Ordinary input/decompressed files are bounded to 32 MiB, declared bytes to 256 MiB and descriptors to 512; remote Git trees must be complete. Larger datasets need reviewed partitioning rather than disabled checks. A premerge manifest cannot certify a deployment or geographic approval. Initial research may be complete with unresolved facts; it cannot close a correction that remains unresolved.

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

Request one coherent PR review from a distinct worker. A reviewer must inspect actual changes, sources, methods, controls, linked acceptance criteria and preservation/release implications; green CI or an author's claims are insufficient. Do not claim the author's issue or edit its scope. If no reviewer is available, the merge waits. Implementation review and source/factual review are separate domains. Limited primary-source access must appear in both the reviewer limits and accepted-with-limits source outcome.

Read [LOCAL_WORKSPACES.md](LOCAL_WORKSPACES.md). Allocate isolated checkouts through `scripts/local-workspace.mjs`; keep bounded work/review slots, include exact required sparse inputs, check storage before generation/installations, and release finished slots after preserving unique work. Do not retain a full checkout per task or review revision. Existing chats must refresh their saved instructions.

### Arrange the reviewer

The engineering, geography and history prompts authorize review delegation. When sub-agents are available, launch a distinct review agent, preferably with fresh/minimal context rather than the author's full reasoning history. Supply the PR URL, exact head SHA, issue URL, evidence-manifest path, and this guide. A reviewer can inspect diffs/immutable blobs through GitHub APIs or Git without a checkout. When local reproduction/tests need one, use the bounded detached review slot described in LOCAL_WORKSPACES.md and release it after posting the result, preserving unique outputs first. The reviewer independently reads repository guidance, diffs and original evidence; the author's explanation is context, not validation. Do not select a different model from the user's choice without authorization.

A review sub-agent in the author's chat is permitted. It provides a separate examination, but is weaker separation than a different reviewer chat and is not an authenticated independent security principal. Do not describe it as a separate chat. The reviewer does not reserve the author's issue, edit its branch, merge, deploy or import anything.

Copy-ready task (replace placeholders):

> Review PR URL at exact HEAD_SHA for ISSUE_URL. Read AGENTS.md, docs/WORKER_COORDINATION.md, docs/LOCAL_WORKSPACES.md and docs/PREMERGE_EVIDENCE_REVIEW.md, plus relevant lane/data contracts. Use API/blob inspection without a checkout when sufficient; when local execution is needed, use the managed sparse detached review slot, include all required inputs, check disk before reproduction, and release the slot when the review is durably posted. Inspect every changed file and renamed original, linked acceptance criteria, actual sources/methods/controls, evidence manifest MANIFEST_PATH, checks and identity/history/release preservation. Treat author claims and green CI as unverified until inspected. Use a unique reviewer worker ID distinct from AUTHOR_WORKER_ID. Do not claim the issue or edit/merge/deploy/import. Report specific findings and actual validation limits. When the required review domains are accepted, post the worldatlas-review:v1 receipt on the PR tied to the exact head and manifest hash; use accepted-with-limits only where policy permits it. If access or evidence prevents acceptance, report the blocker without fabricating a receipt.

The author addresses findings and requests review of any updated head before using the normal merge queue. Authors reconcile the latest current-head receipt from every reviewer before submission; acceptance by one reviewer cannot override another reviewer's unresolved changes-requested receipt. A new head requires renewed relevant review of earlier objections, not merely reliance on their previous-head receipts becoming ineligible. Scoped resolution comments do not replace the required whole-PR acceptance. If no review sub-agent is available, ask another available worker on the PR. Record unavailable review/access on the linked issue; continue independent work within the existing claim if possible, otherwise leave a durable checkpoint and safely release or hand over. Do not ask the user to manually launch a reviewer when an available review agent can do it. No reviewer means no merge, not an exception or a self-review under another ID.

Post one `worldatlas-review:v1` JSON comment on the PR, using the template below. Repository owner/member/collaborator comments qualify. All workers may share one GitHub account: distinct worker IDs are cooperative accountability, not authenticated independent security principals. Never invent a second ID for self-review. Relevant geometry/release/identity changes and the issue's review_kind require substantive domain reviews even when the author labels a PR differently. Posting a receipt does not itself certify regional approval.

```text
<!-- worldatlas-review:v1
{
  "version": 1,
  "pr_number": 123,
  "head_sha": "REPLACE_WITH_CURRENT_40_CHARACTER_HEAD",
  "manifest_sha256": "REPLACE_WITH_RAW_MANIFEST_FILE_SHA256",
  "author_worker_id": "actual-reservation-worker",
  "reviewer_worker_id": "distinct-review-worker",
  "inspected_files": ["every changed file and renamed original path"],
  "evidence_hashes": ["every unique baseline/source/output whole-file SHA256"],
  "outcome": "accepted",
  "limits": [],
  "domains": {
    "implementation": {"outcome": "accepted", "scope": "Describe actual inspected code/acceptance", "limits": []},
    "source": {"outcome": "accepted-with-limits", "scope": "Describe citations/primary evidence checked", "limits": ["Actual limits"]},
    "geometry": {"outcome": "accepted", "scope": "Describe methods/control/source support", "limits": []},
    "release": {"outcome": "accepted", "scope": "Describe identity/history preservation and gates", "limits": []}
  }
}
-->
```

Only needed domains are required; do not claim a review you did not perform. The latest receipt from each worker for the current head is authoritative; any unresolved changes-requested outcome blocks. New commits invalidate reviews even if they only update main. The queue rereads the head, current checks, issue contract, actual files/bytes and receipts before a SHA-guarded squash merge. It preserves the soft 1,000 non-test-line review target. No provider changes, token rotation, deployment or live import occurs as part of this gate.

## Activation proof and limitations

Activation must follow a merged reporting implementation, actual hosted report results, positive and negative real-format fixtures, and an inventory of current claimed/open work. Record the timestamp, decision and checks in the activation PR; the earlier implementation PR uses `Refs #627`. The final activation PR may use `Closes #627` only after these checks. Unit tests use synthetic data and mocked read-only API responses, never production merge mutations. Neither this gate nor moderator review eliminates all factual errors: unavailable sources and unexecuted reproduction remain explicit limitations.

Regression controls reflect concrete moderator findings: #579's malformed hierarchy pin, #580's swapped longitude/latitude transform, #600's conflicting narrative/generated figures, #614's overwritten timestamp-dependent extracts, and #619's inferred containing-file inventory. The manifest and shared-helper tests cover their failure patterns without special country rules. #591's restoration-pin mismatch additionally motivates independent provenance review: a hash alone cannot establish which upstream release exists. These safeguards do not close the individual source/correction issues.

## Acceptance and disposition binding

Read ISSUE_LIFECYCLE.md. Review the original acceptance and PR completion/continuation/wait independently of implementation acceptance. Before a final allowed partial PR, check where actual unfinished obligations go; an explicit original-issue wait is valid and no duplicate follow-up is forced. Initial research may close with permitted unknowns; correction/production acceptance may not.

For PRs created on or after `.github/evidence-policy.json` review_contract_activation_time, add `issue_contract_sha256` and `pr_body_sha256` to the existing worldatlas-review:v1 receipt. Calculate them with `reviewContractBinding(issue, pr)` from scripts/premerge-evidence.mjs using the current GitHub issue and PR. The hash binds normalized issue acceptance prose and canonical work contract plus normalized PR body. Inspect the actual acceptance/disposition before accepting; a hash alone is not semantic approval. Source/geometry/release gates are unchanged. Ordinary issue/PR progress comments do not invalidate these bindings. Substantive body/scope/linkage/closure changes require a renewed exact-head receipt. Older PRs preserve existing receipt compatibility; voluntarily bound receipts are always rechecked. No new handoff form is required.

Read docs/AUDIT_FAILURE_PREVENTION.md on current main before the next job or review. Identify the consequential acceptance claims and independently test applicable consumed-input/code, identity/join, source/method, safe-reproduction, nonvacuous-control and operating-limit invariants. Use shared evidence helpers or an explicitly reviewed equivalent; reviewers derive expectations from original acceptance and independent records before relying on author tests. Exercise real entry points and adjacent paths for corrective PRs; record unexecuted proof as a limit. Keep exact-head review, original evidence, scientific/publication gates and focused research CI. Adoption requires actual subsequent handoffs, not just this prompt edit.

## Author preparation

Read [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) for the author's preparation and
actual local-versus-hosted check boundaries. Reviewers still derive expectations
from original acceptance and independent reference records; author controls and
byte-only local success do not replace substantive exact-head review. Select only
applicable failure families and preserve focused source-only CI.

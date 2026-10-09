# Geography research handover

Use [the geography worker prompt](prompts/GEOGRAPHY.txt) with current `main` in https://github.com/ChengshuLi/WorldAtlas. Models are chosen by the user; geography research can run on Luna. The lane defines file ownership and responsibilities, not model cost or identity.

Geography workers research territorial boundaries, hierarchy purpose, source suitability and granularity. Engineering implements executable migrations, shared schema/UI changes, canonical-grid preparation, integration and publication. History workers research dated attributes of approved territories. GitHub Issues remains the queue and dated work record; do not create a competing TODO document.

Claim one reviewed `type:geography`, `kind:work-item`, `status:ready` issue with a PR planning estimate through [WORKER_COORDINATION.md](WORKER_COORDINATION.md). Umbrellas cannot be claimed. Branch from fresh `origin/main` as `geography/<job-id>` in an isolated checkout. Require confirmed `accepted: true` before implementation.

Every geography issue declares an exact `owned_paths` array in its machine block. Permitted prefixes are `data/regional-review/<packet-id>/` and `research/geography/<campaign-id>/`. The current regional packets retain their existing evidence directories. Use the declared directory even when a later PR needs a fresh branch name. No undeclared, shared hierarchy, original-source, grid, application, hosted, schema, other worker or history-campaign edits are permitted. Ordinary files only: no symlinks or submodules. Engineering consumes these evidence files but preserves them.

An issue-creation role verifies disjoint ownership before readiness. Declared ownership is retained in the canonical claim. Do not expand it while claimed; preserve work, coordinate scope, release and reclaim if a new reviewed scope is necessary. Git checks protect committed paths; they are not production authorization or isolation for arbitrary scripts. Local reproductions must write only to the owned directory or a private temporary/cache directory and must not modify the baseline or call live mutation APIs.

For regional reviews, read [MACRO_FOUNDATION_APPROVAL.md](MACRO_FOUNDATION_APPROVAL.md), [TOP_DOWN_GEOGRAPHY_WORKFLOW.md](TOP_DOWN_GEOGRAPHY_WORKFLOW.md), the issue's exact JSON subjects/release pins, and `data/macro-foundation/regional-handoffs.json.gz`. Verify every declared location and parent purpose against sourced administration, settlements or physical geography. Source metadata, administrative numbers and structural checks alone cannot certify semantics. Record vintage, role, license, original bytes or lawful retained extracts, retrieval dates and hashes, inspected facts, uncertainty, recommendations and unresolved findings.

Workload packets are not new geographic units. Review only your declared subset of shared areas/provinces; combine evidence once during engineering integration. Preserve macro envelopes, stable identities and original history. Propose sourced, bounded correction/restoration children with exact affected IDs and crosswalk requirements; never alter the shared hierarchy or independently publish a correction. Initial reviews can finish with findings; they cannot close a whole region's umbrella or enable historical imports.

If evidence reveals an inter-region inconsistency, open/link one coordinated proposal covering all affected neighboring regions. Do not silently move the outer boundary or approve one side alone. Engineering implements the reviewed joint change, validates and publishes it, updates affected certificates/release pins, and revalidates content scopes and factual territorial applicability. Preserve obsolete inputs and approvals as history; do not silently transfer facts or repin bundles.

M geography, N engineering and P history workers can proceed alongside issue creation. Independent UI/performance/infrastructure engineering and historical source-only collection do not wait for regional completion. Geography evidence/proposals lead to bounded engineering corrections and a validated published complete branch; only then may its history workers import permitted attributes.

Each PR targets main, contains exactly one `Refs #N` or `Closes #N`, and meets the existing size/budget rules. Save the actual issue JSON for the local geography ownership check:

```sh
gh api repos/ChengshuLi/WorldAtlas/issues/ISSUE-NUMBER > /tmp/geography-issue.json
node scripts/check-handoff-scope.mjs --branch geography/JOB-ID --base origin/main --pr-body-file /tmp/pr-body.md --issue-file /tmp/geography-issue.json
```

Trusted CI reads ownership from GitHub, not a PR-authored declaration. Submit validated PRs through the serialized squash merge queue. Release the completed claim after merge and start a fresh branch for the next unclaimed geography issue. Post milestone/source/validation evidence to the issue and report every 30 minutes during sustained work. A blocker requires a durable issue handover with exact branch, inputs, findings and next action; do not silently abandon or broaden the scope.

Public source research and local proposals need repository/public-internet access, not Site or Neon credentials. Geography does not perform live imports, execute migrations, publish, update branch certificates or rewrite research gates. Location-attribute imports still require engineering's complete published regional certificate with exact permitted subjects and current release pins; this lane introduces no additional import authorization.

## Issue lifecycle accuracy

Read [ISSUE_LIFECYCLE.md](ISSUE_LIFECYCLE.md). Authors reconcile original acceptance and next actions before moving on; reviewers check closure/continuation independently of merging. Dependency owners maintain direct dependents. Between jobs review up to three neglected unclaimed same-lane readiness problems. Use shared read-only readiness checks before readying and claiming; preserve scientific/publication gates and canonical ownership. Existing chats refresh before their next job; Main handles exceptional decisions.

Read docs/AUDIT_FAILURE_PREVENTION.md on current main before the next job or review. Identify the consequential acceptance claims and independently test applicable consumed-input/code, identity/join, source/method, safe-reproduction, nonvacuous-control and operating-limit invariants. Use shared evidence helpers or an explicitly reviewed equivalent; reviewers derive expectations from original acceptance and independent records before relying on author tests. Exercise real entry points and adjacent paths for corrective PRs; record unexecuted proof as a limit. Keep exact-head review, original evidence, scientific/publication gates and focused research CI. Adoption requires actual subsequent handoffs, not just this prompt edit.

## Prepare for the first review

Follow [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) before the next job and before
requesting its first review. Select the checks implicated by the original acceptance
and changed behavior from the start; preserve source-only focused CI. Resolve quick
ownership/evidence errors before review, while long regressions and substantive
independent review may proceed in parallel. The guide supplies practical helper and
command details, meaningful adverse cases and existing-chat refresh text; author
preflight does not replace independently derived reviewer expectations.

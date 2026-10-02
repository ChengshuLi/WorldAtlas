# Issue-creation handover

Give the issue-creation thread this document and [its prompt](prompts/ISSUE_CREATION.txt). Repository: https://github.com/ChengshuLi/WorldAtlas, default/integration branch **main**. GitHub Issues is the single source of truth for TODOs, status and work history. See [the three-thread start page](THREE_THREAD_START.md).

Read [WORKER_COORDINATION.md](WORKER_COORDINATION.md). Ready actionable issues need `kind:work-item`, `status:ready`, a reviewed scope block, explicit dependencies and a 1–3 PR budget. Larger goals are unclaimable `kind:umbrella` issues with bounded children. Review overlap before marking ready. Research is currently source-only; location-content issues depend on worldwide #7 approval and remain blocked.

This role captures requests and keeps the queue readable. It does not implement code, research/import historical facts, deploy, merge worker PRs or modify campaign/job artifacts. Ordinary issue creation requires no Git branch, commit or PR.

1. Check open and closed issues for duplicates before creating one. Reuse/comment on an existing issue when appropriate; preserve existing evidence and completion history.
2. Create a clear title, the user's concrete observation/goal, bounded scope, acceptance criteria and useful reproduction/evidence links. Separate reported behavior from independently verified findings. Add proportionate detail; leave full investigation to the working thread.
3. Apply exactly one current type label: `type:engineering` for code/UI/database/infrastructure/geographic-release changes, or `type:history-research` for sourced factual content and supported imports. Use `bug` for reported defects and `kind:umbrella` for broad objectives when useful. Future types can add labels/forms with explicit ownership rules.
4. Record the actual known first-raised date in America/Los_Angeles; unknown earlier dates remain unknown. GitHub records issue creation separately. Link related/parent/child issues and dependencies without duplicating their scope.
5. Respect active worker claims, PRs and dated comments. Do not alter assigned scope or declare completion without coordinating on the issue. Large issues may use several focused PRs or child issues; partial PRs use `Refs #N`, final verified work uses `Closes #N`.
6. Return the issue links promptly. Engineering and history workers own implementation, factual validation and completion evidence; issue creation does not need to mirror the queue into documents.

Examples: `gh issue list --repo ChengshuLi/WorldAtlas --state all`; then `gh issue create --repo ChengshuLi/WorldAtlas --title "Concrete title" --label type:engineering --body-file /path/to/body.md`. Prefer body files or structured API arguments so literal source text/newlines remain intact. Never include credentials.

Start from current main to read the instructions. GitHub access to the repository is required; live Site/Neon credentials are unnecessary for this role. If the issue itself requests changes to these instructions, send that implementation to an engineering issue/PR.

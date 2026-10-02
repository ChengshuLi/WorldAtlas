# Start the three WorldAtlas threads

Repository: https://github.com/ChengshuLi/WorldAtlas. Start every new thread from current **main**. Give it the matching handover document and copy-ready prompt below; no earlier chat/workspace is required. GitHub Issues holds the queue, current status, dated progress and completed work history.

| Thread | Handover document | Copy-ready prompt | Responsibility |
| --- | --- | --- | --- |
| Issue creation | [ISSUE_CREATION_HANDOFF.md](ISSUE_CREATION_HANDOFF.md) | [ISSUE_CREATION.txt](prompts/ISSUE_CREATION.txt) | Capture/classify requests and link duplicates/dependencies in GitHub Issues |
| Engineering | [ENGINEERING_HANDOFF.md](ENGINEERING_HANDOFF.md) | [ENGINEERING.txt](prompts/ENGINEERING.txt) | Work through engineering issues; code, UI, infrastructure and geographic releases |
| History research | [HISTORY_HANDOFF.md](HISTORY_HANDOFF.md) | [LUNA_HISTORY.txt](prompts/LUNA_HISTORY.txt) | Work through research issues; internet sources, factual content, supported imports and receipts |

The issue-creation thread changes Issues only and needs no Git branch. Working threads use separate checkouts/worktrees, inspect active claims/PRs, post scope on the issue, and branch from fresh `origin/main`. Each focused PR addresses one issue or a part of it. Large issues may have multiple PRs; partial work references the issue and final verified work closes it. Maintainers squash-merge validated PRs serially, using the PR title as commit title. After each merge, start a fresh branch for the next focused PR. Provider migrations and Site deployment do not run merely because a PR merges.

Workers continue with the next unclaimed issue in their type queue after each completed PR, until the user asks them to stop, the agreed scope is complete, or a real access/resource/dependency blocker requires handover. Post milestones/blockers/evidence on Issues and report progress every 30 minutes during sustained work. Do not close a worldwide objective after one campaign. Research owns only its campaign directory; engineering preserves research and other jobs. See [PARALLEL_WORK_PROTOCOL.md](PARALLEL_WORK_PROTOCOL.md) for database/geographic maintenance safety.

## Access and cloud setup

All threads need repository access; creating issues/PRs or merging requires the corresponding GitHub permissions. Engineering and research use Node 24 (`npm ci` for a fresh checkout). Geographic preparation uses Python 3.12 and pinned `requirements.txt`; install those dependencies only when needed. Never run automatic baseline restoration, production migration, dataset regeneration or deployment as environment setup.

Public source research and local bundle preparation can start without production credentials. Live Site imports, deployment and owner maintenance require the documented authorized private mechanisms in that new thread. GitHub's `NEON_API_KEY` Actions secret is not a research import token; repository secrets cannot be read back. Credentials cannot be inherited from another thread's workspace or committed into prompts, Git or logs.

The current attached cloud runtime was inspected on 2026-10-02 (America/Los_Angeles): Node 24.19.0, Python 3.12.14, enforced unrestricted HTTP policy through the managed proxy and working GitHub access. No configured runtime secrets/outbound identities were reported. Direct TCP destinations were empty; do not assume direct PostgreSQL access. Runtime observation does not inspect the saved environment editor's latest draft or prove fresh-thread private Site access. Receipt: `data/validation/three-thread-readiness.json`.

For the saved Codex environment named WorldAtlas, verify repository `ChengshuLi/WorldAtlas`, select main when launching tasks, retain Node 24, and use a non-mutating setup such as `npm ci` after checkout. Keep internet access available for public research, package installation and authorized service calls. Preserve managed proxy/CA settings. GitHub Actions database credentials remain server/Actions secrets, not blanket credentials for every research thread. No runtime setting change was needed for the checks above; saved configuration editing is unavailable to this runtime inspection tool.

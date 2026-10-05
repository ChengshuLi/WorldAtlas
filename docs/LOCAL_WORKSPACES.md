# Bounded local workspaces

Whenever an author, premerge reviewer, Auditor or publisher needs a new local checkout, use `scripts/local-workspace.mjs`
for new local checkouts. Fresh branches do not require accumulating fresh directories.
Use Node 24 from any checkout of the same primary repository. One shared Git object
store and registry serve all its worktrees. Each unique worker ID has at most one
`work` slot and one `review` slot. Release a finished slot before allocating its
replacement. A reviewer remains isolated from the author's files and reasoning. Review slots are optional: inspect exact diffs and immutable evidence through GitHub APIs or Git blobs without allocating a checkout when no filesystem reproduction/test is needed.

## Allocate and inspect

```sh
node scripts/local-workspace.mjs report
node scripts/local-workspace.mjs check
node scripts/local-workspace.mjs allocate --worker YOUR-WORKER-ID --slot work \
  --branch geography/YOUR-FRESH-JOB --include data/regional-review/YOUR-PACKET \
  --include data/hierarchy.json --reserve-gib 1
node scripts/local-workspace.mjs allocate --worker YOUR-REVIEWER-ID --slot review \
  --commit EXACT_40_CHARACTER_REVIEW_HEAD --include data/regional-review/YOUR-PACKET
```

Replace placeholders and retain the returned path and ownership token locally.
Work allocation fetches `origin/main` and pins its commit before creating a fresh
lane branch. Review allocation detaches the exact locally available reviewed
commit; fetch the PR head first if necessary. Do not allocate one review directory
per revision: finish/release the previous review slot and allocate its replacement.
Publisher/Auditor inspection that needs local execution also uses the detached review slot; API/blob-only inspection needs no checkout. Any
publisher work branch remains subject to its normal claim/operation protocol.

Sparse checkout is the default. It includes root files, documentation, scripts,
tests, application/backend code, workflow configuration and evidence templates.
Explicitly include every required packet, original source, manifest and data input
as literal `data/`, `research/` or `coordination/` paths. Include new owned packet
paths too. Scope is a storage choice, not permission to omit required evidence or
weaken a check. Resolve pinned baseline bytes with Git when a reproducer supports
that; otherwise include their exact paths. Verify required inputs are present.
Use `--profile full` only when the actual build/test needs it, with an adequate
`--reserve-gib` estimate. There is no allocation-time limit bypass.

## Storage admission and ongoing checks

Allocation is serialized across this repository by an exclusive local directory
lock. It requires at least **50 GiB free after the new reservation**, and at most
**50 GiB total checkout usage/reservations**. Usage includes all registered legacy
worktrees, even outside the managed root. The primary checkout's Git store is
included conservatively. Each managed slot counts the greater of measured usage
and its reserved future size; allocation reserves at least the selected Git input
size and defaults to 1 GiB. Reserve for dependencies, downloads, decompression,
generated data and build output before starting, rather than estimating source
size alone. Missing paths or unknown measurements block allocation.

Run `check` before downloads, installations, reproductions/builds and at work
milestones. A failure means stop new generation/installation and inspect `report`;
release completed work, or record a storage blocker. Do not fall back to a full
clone, unmanaged worktree, `git archive` extraction or another `/tmp` directory.
Keep bounded scratch inside the slot so it is measured. Do not duplicate retained
datasets for baseline experiments: use pinned Git inputs and small derived output.

These are cooperative admission/milestone gates, **not filesystem quotas**. A
running generator, another application or a worker bypassing the tool can exceed
the budget between checks. No daemon kills processes or deletes files under disk
pressure. Disk free space accounts for other repositories/apps; the checkout
budget inventories this repository only. Unregistered historical archives must
be inspected during migration; the helper does not infer their ownership.

Reuse existing package download caches and browser binaries; install dependencies
only for checks that need them. Share immutable dependency environments keyed by
lockfile hash, runtime version and architecture, with one installation writer;
never mutate another worker's environment. The helper does not implement a new
package/environment cache or silently symlink dependencies. Local credentials,
cache paths and ownership tokens stay out of committed evidence.

## Finish and release

After posting a completed review, or after a verified merge and durable issue/PR
handoff, stop processes using the slot and run:

```sh
node scripts/local-workspace.mjs release --worker YOUR-WORKER-ID --slot work \
  --token EXACT_RETURNED_TOKEN
```

Release preserves the current commit at a local `refs/worldatlas-local-recovery/`
ref, then asks Git to remove the exact owned worktree without `--force`. Branches
and the shared Git store remain. It rejects uncommitted, untracked **and ignored**
files: first commit/push necessary evidence, preserve unique scratch outputs, and
remove only verified regenerable artifacts. A review checkout must be clean too.
Release does not decide whether acceptance is complete or a process is finished;
the holder must establish that before calling it. It does not delete remote refs,
original repository evidence, other workers' work or production data.

The token changes on every allocation. Wrong/stale tokens, symlink directories,
changed Git identity and an occupied slot fail closed. A failed/interrupted
allocation remains `preparing` in the registry and consumes its reservation. A
crash may leave the local lock. Neither expiry nor a timeout authorizes deletion
or lock breaking: inspect processes, `git worktree list`, the registry and actual
files, preserve work and reconcile under one operator. There is intentionally no
automatic stale-lock recovery or broad destructive sweep.

## Existing chats and legacy directories

Repository changes guide new work but do not rewrite saved chat goals. Refresh
existing author/reviewer/Auditor/publisher instructions to read this guide before
their next allocation. Finish active legacy jobs in place; do not move their live
files. After a job is finished, inspect and preserve unique work before removing
its completed legacy checkout with Git. `report` lists legacy usage; it never
automatically deletes it. A breached budget may therefore block new allocations
until legacy cleanup is safely completed. Managed paths and the registry are
local execution state, not another issue/status ledger.

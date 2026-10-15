# Bounded local workspaces

Whenever an author, premerge reviewer, Auditor or publisher needs a new local checkout, use `scripts/local-workspace.mjs`
for new local checkouts. Fresh branches do not require accumulating fresh directories.
Use Node 24 from any checkout of the same primary repository. Keep one stable worker ID for each chat across successive issues; a new job is not a new worker. Distinct reviewer agents keep their own worker IDs. One shared Git object
store and registry serve all its worktrees. Each unique worker ID has at most one
`work` slot and one `review` slot. Release a finished slot before allocating its
replacement. A reviewer remains isolated from the author's files and reasoning. Review slots are optional: inspect exact diffs and immutable evidence through GitHub APIs or Git blobs without allocating a checkout when no filesystem reproduction/test is needed.

## Chat identity

Worker identity belongs to the chat, not the issue, branch, goal, checkout or GitHub account. In Codex, use the exact current CODEX_THREAD_ID as the author worker ID and keep it across successive jobs. Never copy an ID from another chat, a reservation, a checkout registry, a handoff or inherited/forked context. A fork/new chat has its own identity. Before starting work or allocating, compare the chosen ID with this chat’s actual ID; if another chat owns the work/slot, leave it untouched and do not treat it as your work or blocker. New author work-allocation commands reject mismatches when CODEX_THREAD_ID is available. Outside Codex, establish one unique persistent ID for that chat; the tools cannot verify chat identity when the environment does not supply it. Do not unset or override CODEX_THREAD_ID to bypass the check.

Active legacy work keeps its recorded worker ID only for finishing, renewing and releasing that exact claim/checkout. Do not rename an active claim, take over another chat’s slot or start new work under the legacy ID. After verified merge/handoff and safe release, use this chat’s ID for the next job and allocation. Independent reviewer agents keep their own stable distinct reviewer IDs (actual agent identity when available); an inherited parent CODEX_THREAD_ID does not identify a sub-agent. Never invent a second ID for self-review. Review allocation is exempt from the author-ID check because review sub-agents may inherit their parent’s environment; review identity remains cooperative and must be checked by the reviewer.

New author allocation requires the current chat’s worker ID; the release command instead uses the recorded worker, slot and saved token to select its target, without changing the operator’s identity.

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
It also includes ordinary `.mjs`, `.js`, `.cjs`, `.py` and `.sh` source files
under `coordination/engineering/`, including nested helpers used by shared entry
points. The same exact-tree code selection is inspected, sized and materialized;
missing code blobs still require coordinated acquisition before allocation.
Adjacent catalogues, scientific inputs, outputs and archived evidence are not
included by this code-only category. It is not a complete scientific dependency
closure or permission to run a producer.
Explicitly include every required packet, original source, manifest and data input
as literal `data/`, `research/` or `coordination/` paths. Include new owned packet
paths too. Scope is a storage choice, not permission to omit required evidence or
weaken a check. Resolve pinned baseline bytes with Git when a reproducer supports
that; otherwise include their exact paths. Verify required inputs are present.
Use `--profile full` only when the actual build/test needs it, with an adequate
`--reserve-gib` estimate. There is no allocation-time limit bypass.

Allocation reads tree metadata before sizing only the selected blobs in bounded
no-lazy-fetch batches. Native `rev-list --missing=print --ignore-missing` probes
disable fetch before object parsing, including on Git 2.39, before `cat-file`
sizes locally present selected blobs. Excluded partial-clone blobs need not be present and are not
hydrated for sizing. Missing selected blobs fail before a reservation, branch or
checkout is created; acquire only the explicitly required inputs through the
coordinated import path, then retry normal allocation. This also applies to full
profiles, which select every file.

## Refresh a stale checkout without changing its files

The helper that starts an allocation runs before the new checkout exists. Running
an old primary checkout's script can therefore keep using a previously repaired
allocator. Before a new job, refresh `origin/main` with blob filtering, pin its
commit, and read that pin's `AGENTS.md` and this guide. Do not pull, reset, switch
or overwrite a checkout holding active work.

The following code-only bootstrap loads both allocator modules from one exact
locally available main commit. It uses an exclusive temporary directory inside
the shared Git store, retains the original repository as the current directory,
and removes only its generated helper copies afterward. A failed main refresh or
commit lookup stops without using a cached older pin. Missing helper blobs
stop before execution; acquire those exact pinned objects through the coordinated
route below rather than falling back to an old executable. Use Node 24.

```sh
(
git -c fetch.negotiationAlgorithm=noop fetch --no-tags --no-recurse-submodules \
  --no-auto-maintenance --filter=blob:none origin main || exit
base=$(GIT_NO_LAZY_FETCH=1 git rev-parse --verify 'origin/main^{commit}') || exit
GIT_NO_LAZY_FETCH=1 python3 - "$base" inspect --commit "$base" \
  --include data/YOUR-REQUIRED-PATH <<'PYTHON'
import os, re, subprocess, sys, tempfile
from pathlib import Path
base, *args = sys.argv[1:]
if not re.fullmatch('[a-f0-9]{40}', base):
    raise SystemExit('Exact accepted commit required')
env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1')
def git(*args, **kwargs):
    return subprocess.check_output(['git', '--no-replace-objects', *args], env=env, **kwargs)
common = Path(git('rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()).resolve(strict=True)
sources = {}
for name in ('local-workspace.mjs', 'worker-identity.mjs'):
    row = git('ls-tree', '-z', base, '--', 'scripts/' + name).rstrip(b'\0')
    metadata, member = row.split(b'\t')
    mode, kind, oid = metadata.decode().split()
    if mode not in ('100644', '100755') or kind != 'blob' or member != ('scripts/' + name).encode():
        raise SystemExit('Ordinary pinned helper required')
    present = git('-c', 'core.commitGraph=false', 'rev-list', '--objects', '--filter=tree:0',
                  '--missing=print', '--ignore-missing', '--no-walk=unsorted', '--no-object-names',
                  '--stdin', input=oid.encode() + b'\n').decode().strip()
    if present != oid:
        raise SystemExit('Pinned helper missing; coordinate exact-object acquisition')
    status = git('cat-file', '--batch-check=%(objectname) %(objecttype) %(objectsize)', input=oid.encode() + b'\n').decode().split()
    if len(status) != 3 or status[0] != oid or status[1] != 'blob' or not status[2].isdigit():
        raise SystemExit('Pinned helper missing; coordinate exact-object acquisition')
    sources[name] = git('cat-file', 'blob', oid)
with tempfile.TemporaryDirectory(prefix='worldatlas-helper-', dir=common) as directory:
    for name, body in sources.items():
        with (Path(directory) / name).open('xb') as output:
            output.write(body)
    result = subprocess.call(['node', str(Path(directory) / 'local-workspace.mjs'), *args], env=env)
sys.exit(result)
PYTHON
)
```

Keep every original `--include` value, including new owned output paths. Replace
`inspect --commit "$base" ...` with the documented `check`, `allocate` or `release`
arguments when needed. The current helper still enforces the shared registry,
ownership, locks and storage policy. A later main refresh during author allocation
may add required inputs; inspect its new exact head rather than reusing old OIDs.

## Inspect and acquire only required missing objects

`inspect --commit EXACT_HEAD --profile sparse --include EXACT_PATH ...` is
read-only: it does not fetch, reserve space, create a branch/checkout or take the
allocation lock. It uses the allocator's actual selection and returns every
selected path/OID/available size plus one `missing` row per absent OID with all its
selected paths. `selectedBytes` is null while any selected size is unknown;
`availableBytes` is only the known per-path subtotal. An empty missing list does
not establish storage admission or complete test/scientific dependencies.
`--profile full` inspects every file and retains submodule refusal.

An unavailable exact commit or missing tree metadata stops inspection with the
commit or known tree OIDs and no complete selected inventory. Descendant paths
cannot be inferred from absent metadata; coordinate that metadata first and
inspect again. Permission, corruption and other Git diagnostics remain failures,
not missing-blob rows. No object acquisition is automatic. On older Git,
`GIT_NO_LAZY_FETCH=1` alone can produce a fatal promisor error instead of a
`cat-file` missing row; the presence probes avoid that lookup entirely.

For a coordinated acquisition, authenticate each missing path/OID/type/size
against the same immutable GitHub tree. Use the relevant subtree's metadata when
needed; refuse truncated, conflicting or unknown descriptors. Run `check` before
downloading and allow for the missing object bytes, the planned checkout
reservation and other build/dependency needs above the existing free-space floor.
Only the verified `missing[].oid` list from this exact scope may be imported:

```sh
# Standard exact-object transport, with verified missing OIDs on stdin.
git -c fetch.negotiationAlgorithm=noop fetch --no-tags --no-write-fetch-head \
  --no-recurse-submodules --no-auto-maintenance --filter=blob:none --stdin origin
```

Use bounded batches and verify acquired blob type, exact OID and byte size
against those descriptors. Re-run inspection
and normal allocation with the same complete scope. Do not replace this with all
repository OIDs, global `ls-tree -l`, a full clone or automatic lazy fetching.
This reuses the exact-object transport used by geography acquisition; its
geography-specific CLI/declaration limits are unchanged and are not a universal
workspace prefetch interface. Inspection does not resolve an undeclared required
path: sparse inputs must still cover the actual checks, or use an adequately
reserved full profile.

Immutable object reads and private transport stores need no manual chat grant,
start announcement or release acknowledgment. Ordinary exact-OID shared-store
imports also need none when their exact remote/filter is already registered and
no strict-origin inventory interval, shallow rewrite or maintenance is active.
Coordinate shared configuration setup, mutable ref/FETCH_HEAD decisions, shallow
changes, maintenance and strict-origin whole-store before/fetch/after inventories.
Keep checkout/index/output ownership, the allocator lock, storage admission and
all exact-byte checks.

## Storage admission and ongoing checks

Allocation is serialized across this repository by an exclusive local directory
lock. It requires at least **10 GiB free after the new reservation**. There is no
fixed cap on combined checkout usage or on an individual reservation. Reservations
must be positive, finite and represent safe integer byte counts. `report` still
inventories all registered legacy worktrees, even outside the managed root, and
the primary checkout's Git store. Each managed slot counts the greater of
measured usage and its reserved future size; allocation reserves at least the
selected Git input size and defaults to 1 GiB. Reserve for dependencies, downloads,
decompression, generated data and build output before starting, rather than
estimating source size alone. Missing selected inputs or unknown selected input sizes
block allocation. Allocation checks real free space without traversing registered
checkouts. `check` also reads filesystem free space directly and returns only
`freeBytes` and `limits`; filesystem free space already reflects actual usage by
all worktrees, the Git store and other applications. Missing worktree paths,
unknown checkout measurements and invalid registry records still block `report`,
which remains the inventory diagnostic, but do not block the floor-only `check`.
Allocation and release retain their existing registry, ownership and isolation checks.

Run `check` before downloads, installations, reproductions/builds and at work
milestones. A failure means stop new generation/installation and inspect `report`;
release completed work, or record a storage blocker. Do not fall back to a full
clone, unmanaged worktree, `git archive` extraction or another `/tmp` directory.
Keep bounded scratch inside the slot so it is measured. Do not duplicate retained
datasets for baseline experiments: use pinned Git inputs and small derived output.

These are cooperative admission/milestone gates, **not filesystem quotas**. A
running generator, another application or a worker bypassing the tool can exceed
the budget between checks. No daemon kills processes or deletes files under disk
pressure. Disk free space accounts for other repositories/apps; the usage
report inventories this repository only. Unregistered historical archives must
be inspected during migration; the helper does not infer their ownership.

Reuse existing package download caches and browser binaries; install dependencies
only for checks that need them. Share immutable dependency environments keyed by
lockfile hash, runtime version and architecture, with one installation writer;
never mutate another worker's environment. The helper does not implement a new
package/environment cache or silently symlink dependencies. Local credentials,
cache paths and ownership tokens stay out of committed evidence.

## Finish and release

Cleanup is the primary lifecycle rule. After a fresh PR API read verifies actual
merged state, the exact reviewed head and its squash commit, explicitly release
the owned managed author slot. `gh run watch` and the native merge workflow do not
perform local cleanup. Preserve the run URL, request ID, head and merge commit on
the original issue before release. Stop local servers/reproduction processes,
push required evidence, preserve unique scratch and leave the slot clean. Continue
from the primary checkout to reconcile the original issue and allocate the next job.
Settle any retained live-operation reservation through its existing workflow.
A release failure does not invalidate an already verified merge. Legacy/unmanaged
checkouts are retained for explicit inspection.

Reviewers must release their local review slot immediately after durably posting
the review; no waiting for the author to merge. Failed/blocked tasks first preserve
their checkpoint and unique work. For a manual finish/release, stop processes using
the slot and run:

```sh
node scripts/local-workspace.mjs release --worker RECORDED-WORKER-ID --slot work \
  --token EXACT_RETURNED_TOKEN
```

With explicit user authorization to delete an exact retired checkout, an operator may release that selected slot after verifying its backup and confirming no live process or live operation depends on it, while leaving `CODEX_THREAD_ID` unchanged. Use the normal release guards; this does not authorize automatic cross-chat cleanup, new work under the recorded worker, registry edits, forced removal or releasing another holder’s live-operation reservation.

Release preserves the current commit at a local `refs/worldatlas-local-recovery/`
ref, then asks Git to remove the exact owned worktree without `--force`. Branches
and the shared Git store remain. It rejects uncommitted, untracked **and ignored**
files, plus index trust flags that can hide edits (`assume-unchanged` or materialized `skip-worktree`): first commit/push necessary evidence, preserve unique scratch outputs, and
remove only verified regenerable artifacts. A review checkout must be clean too.
Release does not decide whether acceptance is complete or a process is finished;
the operator must establish that before calling it. It does not delete remote refs,
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

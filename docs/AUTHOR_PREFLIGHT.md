# Author preflight: prepare evidence that survives independent review

Read [AUDIT_FAILURE_PREVENTION.md](AUDIT_FAILURE_PREVENTION.md) and
[PREMERGE_EVIDENCE_REVIEW.md](PREMERGE_EVIDENCE_REVIEW.md) first. Use this
workflow before starting the next job and before requesting its first review.
It uses the existing issue, PR explanation and evidence manifest; do not create
another checklist ledger or handoff form. Refresh active work at its checkpoint
without changing ownership or repeating completed implementation.

## Before implementation

Read the original acceptance criteria and current claim. Identify what this PR
will establish, which facts remain unknown and what will happen after merge.
Choose only the checks implicated by those claims and changed behavior:

| Work you are doing | Prepare from the start |
| --- | --- |
| Collecting or interpreting a source | Retain the actual supporting content, exact citation, source date and role, limitations and truthful coverage. A reachable URL or matching hash does not establish support. Do not invent a numerical value when the source leaves it unknown. |
| Computing rows or a numerical table | Pin the independent scope/reference records. Check raw duplicates before constructing dictionaries, exact identities and actual joins. Bind every generated numerical claim to its output, unit and vintage. Derive units from the actual source/schema and calculation, not a substring in the field name. |
| Running a generator or project helper | Consume authenticated bytes, including auxiliary inputs and imported project code. Admit the complete input phase and destination before calculation. Use fresh owned run names and preserve earlier evidence. |
| Making a geographic measurement | Record native CRS, datum, axis order and units; perform a documented conversion when needed. Preserve original validity separately from diagnostic repairs. Use the complete pinned index for global claims or state the subset limit. |
| Changing a wrapper, importer, retry or cleanup operation | Trace the producer and consumer together. Check row and byte bounds, the remaining deadline and complete inventories. A correction must cover adjacent entry points, not just one reported example. |
| Documentation or instructions only | Check the referenced interfaces, commands and responsibilities against actual code. Do not manufacture scientific experiments for unchanged behavior. |

Before choosing tests, follow each consequential changed claim through its actual
inputs, computation, intermediate records, report/control writer and final evidence.
Use the boundary examples in [AUDIT_FAILURE_PREVENTION.md](AUDIT_FAILURE_PREVENTION.md#follow-a-claim-through-the-final-evidence).
Check that measured fields, identities and units survive into the final table;
controls read actual comparison products; all writers preserve prior evidence;
and multiple readers share a complete execution budget. Separate copied results
from new computation and verify the actual supporting citation. Prepare bounded
actual-input changes at the implicated boundary before requesting review. Missing
full GIS/source access does not excuse executable small reporting/control checks;
those checks do not establish the unavailable geographic result. Describe this in
the existing PR explanation, without a new checklist or manifest schema.

Use Baseline.pinned_bytes/materialized_bytes and declared load_modules for
consumed project inputs; consume the returned bytes rather than reopening a
checked path. load_modules requires explicitly named pinned project modules, rejects
relative imports and requires from-import syntax for declared dotted modules. Dynamic
reads and installed dependency versions remain separate evidence obligations. Use exact_rows/join_rows/finite_metrics for applicable record
contracts. Construct NewVintage before computation, then publish the complete
product set with its final receipt. Use publish_bytes for plain CSV/JSONL/GeoJSON
or gzip products: publish takes JSON values; publish_bytes takes complete bytes,
including already encoded gzip. The owned prefix ends in a slash; each run name is
fresh. File and decoded-file limits are 32 MiB; the complete phase is 256 MiB and
the completion receipt is capped at 4,096 bytes. ZIP members require their own decoded admission. See the shared
guide for limits and interface details.

When changing a shared helper, inspect existing consumers and their authenticated
code closures before adding a module dependency. Exercise the affected consumer
entry points, not only the helper in isolation. Retained execution receipts
describe historical bytes: validate their complete authenticated code bindings at
the declared immutable execution vintage rather than silently refreshing old
hashes to match current code. Keep ordinary candidate-byte checks for current
outputs and preserve the original evidence.

Use the helpers where their invariant applies. If an interface does not suit the
producer, explain the equivalent tested guarantee in the existing PR explanation;
independent review must examine that exception. Neither the helpers nor CI grant
scientific approval or publication authority.

Control runners are producers too. Admit their complete fresh fixture and result
locations before any mkdir, write or expensive probe; use exclusive creation for
fixture files. Reject existing targets and dangling symlinks without changing
sentinels, original evidence or publishing a success receipt. A new hard-coded
suffix avoids one collision but does not make a rerun safe. Preservation checks
must capture the original sentinel before execution, not hash it after a write.
Test both the producer and its control writer when fixing output admission.

When original inputs and later retained evidence require different Git commits,
use the versioned historical-file format in EVIDENCE_QUALITY.md. Preserve every
original pin; declare each file's commit and disambiguate repeated paths or input
hashes. Bind subject lookups, prior rosters and record comparisons to their actual
reference vintage. Local ancestry checks do not replace the hosted PR-base check.

A retained helper is not necessarily the executed helper. Bind provenance to the
bytes actually consumed or executed. If using a custom adapter instead of the
shared helper, document and independently test its equivalent complete guarantees;
do not attribute execution to a pinned file that the entry point never loads.

Author preflight prepares evidence for review. It does not replace the reviewer's
independently derived expectations, source inspection or adverse fixtures.

## Before the first review request

1. For executable behavior, run the actual documented entry point in an isolated, credential-free environment
   with bounded inputs and a fresh owned destination. Run again with another fresh
   name when claiming reproducibility. Confirm originals are unchanged and that the
   complete receipt matches every output. Use faithful local fixtures or mocks for
   provider wrappers/importers; never invoke a live operation as a review experiment.
   Documentation-only work checks interfaces; source collection checks supporting
   content. A failed attempt stays failed.
2. For an applicable executable safeguard, construct a meaningful adverse case. For a join,
   change a real parent/source field while keeping the candidate internally coherent;
   for scope, test a duplicate or missing actual record; for authentication, alter an
   actually consumed file/helper; for reproduction, use a collision or symlink. A
   changed expected digest or a true/false assertion alone does not test semantics.
3. Reconcile source content, method, results and prose. Refresh descriptors only after
   results are final. Record unavailable experiments as limits, not successful checks.
4. Check the existing evidence manifest locally. From the repository root, replace
   the manifest path below with the issue-declared path:

   ```sh
   node scripts/evidence-quality.mjs PATH/TO/evidence-quality.json
   ```

   This checks byte descriptors and ledger/summary consistency. It does not check
   metric/table bindings, control receipts or changed-file accounting, prove factual truth or
   run optional structured record checks. When the manifest declares record_checks,
   additionally run the following read-only check:

   ```sh
   node --input-type=module - PATH/TO/evidence-quality.json <<'JS'
   import fs from 'node:fs';
   import {repositoryReader} from './scripts/evidence-quality.mjs';
   import {validateRecordChecks} from './scripts/premerge-evidence.mjs';
   const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
   const checked = validateRecordChecks(manifest, repositoryReader(process.cwd()));
   console.log({record_checks_checked: checked});
   JS
   ```

   Zero declarations establish no structured claim. Choose independent pinned
   references; candidate outputs cannot serve as their own reference. The hosted
   trusted premerge gate additionally checks metric/table bindings, control receipts,
   changed-file accounting and issue/claim bindings. After independent review, the
   normal merge queue rechecks the exact-head review receipt and its issue/PR contract
   bindings. Before review, inspect
   those declarations against actual outputs and changed files; the local byte-only
   success is not full premerge acceptance. Read the quick hosted ownership/evidence
   results and resolve their machine-reported errors before requesting review. Long
   regression tests and substantive independent review can proceed in parallel.
5. Run focused tests for the code you changed and its affected producer entry point.
   For changes to shared evidence safeguards, the representative suites are:

   ```sh
   node --test test/evidence-prevention.test.mjs test/premerge-evidence.test.mjs
   ```

   Check that each named test file exists and the test report contains the intended
   controls; a successful exit alone may silently omit a mistyped test path.

   When changing the foundational immutable reader, also exercise the existing
   trusted geography runner and affected retained-execution validator. Their
   compatibility is a changed-behavior obligation, not a new research-wide test.

   Use Node 24 and a Python environment containing the project's pinned scientific
   dependencies; set both PYTHON and WORLDATLAS_TEST_PYTHON to that executable when
   running these wrappers. Use PYTHONDONTWRITEBYTECODE=1 to avoid bytecode artifacts
   in wrappers that do not select Python's -B option.
   If the affected entry point runs Python with -I, verify those dependencies import
   in that isolation mode too; a user-only installation may be invisible there.
   Source-only geography/history work retains focused CI. These shared suites are
   not a new mandatory full regression for every research packet.
6. In the existing PR description, explain acceptance advanced, supporting evidence,
   adverse controls, limits, remaining work and the next action. Use Refs #N for
   partial work. Use Closes #N only when all original acceptance, including required
   production acceptance, is proven. Request independent review of the final head.

Judge completion against the owning issue's original promise. A bounded
read-boundary or output-safety repair can finish while the original geography
remains unapproved; its independent source questions keep their existing owners.
Do not silently inherit unrelated parent obligations into the correction or treat
an integrity check as scientific approval. Required province assessments, sources
or production acceptance on the owning issue still prevent its completion. If the
contract and continuation disagree, resolve that on the original issue before
requesting closure or expanding scope.

## When review finds a problem

Determine whether it is an incorrect result, a missing rejection safeguard, an
unsafe operation, unmet acceptance or unresolved research. Preserve original
bytes and claims. Fix the underlying invariant and check neighboring paths; do
not repeatedly change only the first failing fixture. A legitimate unknown can
remain explicit when acceptance permits it. Required unverified proof cannot
support completion.

Every new commit, including documentation-only commits, requires a new exact-head
receipt. Substantive acceptance/PR disposition changes also invalidate contract
bindings and require renewed relevant review. Ordinary progress comments do not invalidate review.
Before resubmitting to the queue, inspect the latest receipt from **each reviewer**
for the current head and reconcile every substantive objection. One reviewer's
acceptance does not clear another reviewer's changes-requested receipt. Ask the
objecting reviewer to recheck the repair; do not repeatedly submit an unchanged
head or treat queue rejection as a transient error. Review of a previous head is
not acceptance of a new head. The final accepting receipt must cover the required
whole-PR domains; a narrow finding or resolution comment is not a full acceptance.
When a new head addresses earlier objections, request renewed relevant review and
make the resolution explicit rather than relying on old receipts dropping out of
the current-head gate. The trusted queue remains the final safeguard.

After merge, reconcile the issue and direct dependents, preserve the checkpoint,
and release the owned checkout before taking the next fresh job.

## Existing-chat refresh text

Read current-main docs/AUTHOR_PREFLIGHT.md, docs/AUDIT_FAILURE_PREVENTION.md and
docs/PREMERGE_EVIDENCE_REVIEW.md before your next job. Preserve your current claim,
checkpoint and completed evidence. Select the checks needed by your actual
acceptance claims before implementation; use authenticated consumed inputs/code,
independent reference records, safe fresh outputs and meaningful adverse controls
where applicable. Run the documented focused preflight before the first review
request and resolve quick ownership/evidence failures. Apply fresh-output admission
to control fixtures and result writers too. Before queue submission, reconcile all
reviewers' outstanding findings and obtain renewed relevant exact-head review;
one acceptance does not override another objection. Record limits honestly.
Source-only research keeps its focused CI. Obtain a distinct review of the exact
final head, use the normal queue, reconcile the issue/dependents and release the
owned checkout afterward. This refresh changes neither scope nor scientific or
publication authority.

For existing chats, also refresh the final-evidence boundary guidance: prepare
applicable report/control, combined-budget and inherited-citation checks before
review. Preserve ownership/checkpoints; select faithful bounded probes rather than
rerunning every geography computation. Reviewers record observed checks and limits
in their existing domain scopes.

## Avoid repeated proof and paperwork

Apply WORKER_COORDINATION.md's delivery policy. Use the smallest evidence manifest
that binds the actual inputs and results being claimed. Changed code, tests and docs
are already in Git's exact diff; no duplicate change_receipts or output descriptors
are required just because those files changed. Keep actual metric, source and
preservation bindings. Cite test logs directly instead of writing new passed-control
JSON. If such receipts are retained, they must still agree with their actual bytes.

Before an expensive repeat, identify what changed or which acceptance requirement
needs the run. An unchanged producer does not need another two-run demonstration for
each batch or reviewer. Verify new batch results and current selected ownership;
reuse applicable prior source/method and safety tests with their limits. Do not relabel
changed inputs as unchanged or remove a failing declared control to claim success.

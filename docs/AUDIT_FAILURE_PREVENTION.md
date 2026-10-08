# Test the claim independently before merge

This extends PREMERGE_EVIDENCE_REVIEW.md. Hash agreement establishes byte identity;
two identical runs establish repeatability. Neither independently establishes a
correct source join, complete scope, scientific method or safe reproduction.
The #726 investigation found these recurring failures in research and engineering.
Use shared safeguards at the actual execution boundary, rather than adding another
packet-specific boolean. This guide introduces no new task ledger or handoff form.

## Author and reviewer responsibilities

In the existing PR explanation, identify the original acceptance criteria advanced,
the consequential claims and their actual supporting evidence, remaining obligations
and next action. Include all numerical claims in the existing metric/table bindings,
with actual units and vintages. Reconcile source citations, results and prose.
Unknown research may be complete when its original acceptance permits it; unresolved
correction or production acceptance cannot be closed on the strength of a hash.

Before reading the author's proposed tests as proof, the independent reviewer reads
the acceptance criteria, actual diff and referenced source records, then determines
which failure families apply. For each applicable family, exercise the real entry
point with an independently constructed adverse fixture or record a precise limit.
Author controls are useful evidence, not the reviewer's independent expectation.
Capture the actual altered complete input, entry point, observation and unchanged
originals. Do not invent a pass receipt for an experiment that was not performed.
These details belong in the existing review comment/domain scope and linked evidence.

| Claim/failure family | Independent expectation and adverse case |
| --- | --- |
| Immutable execution | Trace every consumed scope/snapshot/crosswalk/source and project import. Alter an actually consumed file/helper while immutable pins remain unchanged; reject drift or execute the captured immutable bytes. |
| Exact identities and joins | Read the authoritative raw roster and actual rows independently. Missing, duplicate, fabricated IDs and wrong parent/source/alias fields must fail even when all candidate hashes and summary counts are refreshed coherently. |
| Complete inventory | Use all paths in the pinned index, including supplemental files. An incomplete scan or absent stored point cannot prove worldwide absence; explicitly limit regional/subset claims. |
| Source and scientific interpretation | Inspect retained supporting content, dates, actual license declaration/native CRS, units and geometry validity. HTTP 200, a matching hash or similar coordinates cannot substitute for those facts. Test wrong datum/units, missing cited content and relevant geometry edge cases. |
| Safe reproduction | Execute the documented CLI twice into fresh owned run names. Test existing ordinary files, broken symlinks, traversal, escaped destinations and failures after computation. Admission failures create nothing; originals remain unchanged; partial runs have no valid completion receipt. |
| Nonvacuous verification | Remove a required input, comparison target, required metric or expected source record. Empty responses and absent checks must fail; count actual experiment executions. |
| Operating limits | Test producer-to-consumer bytes AND row bounds, retries against remaining job time and complete cleanup at realistic index size. Successful individual components do not establish end-to-end compatibility. |

Do not run every family on every PR. Select those implicated by changed behavior and
the acceptance claims. A correction requires examination of adjacent execution paths:
producer/control writer, wrapper/imported helpers, scope/row joins or builder/consumer.
Test the invariant that failed, not only the first reported fixture. Preserve successful
parts of earlier repairs and do not reset another issue's PR allowance.

Missing required proof prevents the corresponding completion claim. Limited evidence
may still advance a partial research PR when its acceptance permits those limits.
Passing these checks grants no scientific approval, import or publication authority.
New exact heads, evidence or substantive acceptance/disposition changes require renewed
relevant review under the existing receipt binding; progress comments do not.

## Follow a claim through the final evidence

A valid computation can still feed an incorrect report or a control that never
checks it. For each consequential changed claim, trace the actual consumed input
through the computation, intermediate records, report/control writer and final
claimed evidence. Include reused results when the PR relies on them. This is a
review method, not a new form: explain the relevant paths and observations in the
existing PR description and review domain scope.

At each applicable boundary, compare actual records with independently read
references before trusting hashes or summaries. Select bounded probes that can
expose the particular loss, substitution or false success:

- **Report transfer:** follow a required measured field from the intermediate
  record into the final row, including identity, units, CRS and vintage. A renamed
  field must not silently become null/zero or disappear. Try a missing required
  field, foreign identity or duplicate while keeping the rest of the fixture
  coherent. Document permitted unknowns separately from required measurements.
- **Controls and comparisons:** read both runs' actual products and derive counts
  and success from their records. Alter one comparison product or remove a real
  contact/row; a stored equality hash, hard-coded count or unconditional `passed`
  must not hide the change. A control may report that a probe was rejected, but
  must actually invoke the claimed rejection path.
- **Every output writer:** inspect reporting and control writers as well as the
  main producer. Test their existing-file and dangling-symlink destinations with
  sentinels captured before execution. Successful producer admission does not
  cover a later standalone writer; retained evidence must remain unchanged.
- **Complete resource accounting:** inspect the union of actual inputs, decoded
  representations and outputs across all reader/helper instances in the same
  execution phase. Splitting a file into chunks or assigning another reader does
  not reset the phase or decoded-file limit. A lightweight size inventory can
  establish a budget violation without rerunning the expensive computation.
- **Inherited results and citations:** distinguish new computation from copied
  predecessor rows. A repaired helper does not validate results produced by the
  old helper. Check the actual cited content and distinguish printed page numbers
  from PDF indices; a declared page list must cover the supporting content.

Unavailable full sources, GIS dependencies or memory admission limit those
experiments, not every experiment. Independently check small retained JSON/CSV
reporting and control boundaries when they faithfully exercise the claim; a
synthetic fixture proves only that boundary, not the original geographic result.
Keep these limits distinct in the review. If required proof remains unavailable,
use the existing partial-work disposition or request changes rather than claiming
completion. Source-only work with no executable/reporting claim does not acquire
irrelevant reproduction requirements.

The later #726 findings illustrate the boundaries: #1489 (report/control truth),
#1491 (actual comparison products), #1401 (output inventory/writer), #1496 (measured
field transfer), #1497 (combined budgets), and #1499/#1462 (citations/inherited
results). These links identify reported defects and existing repair owners; they
are not blanket independent confirmation of every scientific finding. Review
current fixes before repeating a historical failure claim.

## Shared execution tools

New evidence producers use these shared helpers for applicable invariants. Review any
exception explicitly, including why the helper is unsuitable and the equivalent tested
guarantee. Do not silently leave a legacy standalone writer in a new wrapper.

- `Baseline.pinned_bytes(path)` returns the actual authenticated immutable input.
  `materialized_bytes(path)` verifies and returns the captured checkout bytes; consume
  those returned bytes, rather than reopening the file after checking another copy.
  Include scope, issue snapshots, auxiliary data and every consumed project helper.
- `Baseline.load_modules({module_name: pinned_path})` executes captured pinned project
  code and its declared project imports. Local undeclared imports fail. This is
  cooperative provenance tooling, NOT a sandbox: dynamic file reads still need the
  byte reader, and installed dependencies require truthful runtime/version evidence.
  No credentials, provider writes or unreviewed code execution are authorized.
- `Baseline.subjects(ids)` reads the complete immutable world index, rejects duplicate
  raw IDs/parts and conflicting indexed identities, and returns actual containing-file
  descriptors. Raw and decoded unique inputs count toward the complete 256 MiB phase;
  ordinary/decoded files retain the 32 MiB cap. Splitting a descriptor list while
  executing the same oversized phase is not bounded partitioning.
- `exact_rows`, `join_rows` and `finite_metrics` in `evidence/contracts.py` derive
  uniqueness, coverage, correspondence and required finite fields from real records.
  References must be independent pinned source/baseline records, not the candidate's
  own result or booleans. Unknown fields do not establish affirmative support.
- `require_source_text` checks already extracted supporting text, not a URL/status.
  A text match does not authenticate authority, currency or legal reuse. `source_crs`
  parses native CRS and rejects an incompatible expected frame. Select and document
  a real conversion or explicitly reviewed approximation before WGS84 measurements;
  relabeling a CRS is not a transformation.
- Construct `NewVintage(baseline, owned_prefix, fresh_run_name, filenames)` BEFORE
  calculation. It validates the complete destination set without mutation. `publish`
  admits all payload sizes, exclusively reserves the fresh run and writes its
  `publication.json` last. Accept a run only after validating that complete receipt
  and every listed whole-file output. Partial failed runs are preserved as failed
  attempts; never reuse them or infer success from some files being present.
  Research and engineering evidence namespaces are supported. The legacy single-file
  `write_new_vintage` interface remains available; whole-run producers use NewVintage.
  `publish_bytes` applies the same safeguards to complete CSV/JSONL/GeoJSON and other
  plain named products, including actual bounded gzip decoding. ZIP/archive producers
  must separately admit all decoded members; a small transport never waives those caps.

The existing manifest can optionally include versioned `record_checks` for structured
claims. Each v1 check declares `path`, `json_pointer`, `id_key`, an independent pinned
`reference_path`, `reference_json_pointer`, `reference_id_key`, and `fields` mapping
candidate fields to reference fields. The trusted byte gate reads the actual files
without executing candidate code; it rejects empty, duplicate, missing/fabricated rows
and incorrect mapped values. Paths must be inventoried output and baseline files.
This extension is compatible with existing v1 manifests and is not a handoff schema.
Use it for an applicable structured completeness/join claim; absence of declarations
is a review question, never proof of zero consequential claims. Factual prose and
source authenticity still require independent review.

## Focused CI and audit feedback

The trusted evidence job keeps its read-only token and never runs candidate producers.
Candidate tests/reproduction are isolated without GitHub credentials. Shared safeguard
changes run their focused regression suite; producer changes exercise affected actual
entry points. Source-only geography/history retain their existing focused CI profile.
There is no universal full-world run or full regression on each research PR.

Auditor continues owning existing follow-ups and #726's four-column table. Findings
distinguish incorrect results, rejection gaps, unsafe operations, unmet acceptance and
unresolved research. Exact byte differences and meaningful numerical disagreement are
different findings. Search both open/closed follow-ups and later repairs before creating
another issue. Reuse current owners; create a shared repair only when genuinely needed.
Recurring findings feed a compact regression and the shared invariant, not another
mandatory ledger or generic instruction to be careful. Main handles exceptions only.

## Existing-chat refresh

Copy before the next job: Read current-main docs/AUDIT_FAILURE_PREVENTION.md and
docs/PREMERGE_EVIDENCE_REVIEW.md. Preserve your current ownership/checkpoint. For your
next PR, independently identify its consequential claims and applicable failure
families, use shared admission/record helpers or an explicitly reviewed equivalent,
and test the actual entry points with meaningful adverse fixtures. Reviewers derive
expectations from acceptance and independent sources, not the author's own outputs.
Keep scientific/publication limits, exact-head review, focused CI and the normal queue.
Auditor distinguishes defects from unknowns and reuses scoped follow-ups. Do not start
another ledger or background monitor. Refresh is adopted only when subsequent actual
author/reviewer handoffs demonstrate these behaviors.

## Prepare for the first review

Follow [AUTHOR_PREFLIGHT.md](AUTHOR_PREFLIGHT.md) before the next job and before
requesting its first review. Select the checks implicated by the original acceptance
and changed behavior from the start; preserve source-only focused CI. Resolve quick
ownership/evidence errors before review, while long regressions and substantive
independent review may proceed in parallel. The guide supplies practical helper and
command details, meaningful adverse cases and existing-chat refresh text; author
preflight does not replace independently derived reviewer expectations.

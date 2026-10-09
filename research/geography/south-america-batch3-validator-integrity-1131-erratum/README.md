# Batch 3 validator integrity erratum

This additive packet repairs the execution boundary around the unchanged
validator from PR #1131. The historical #1122, #444 and #940 files, outputs,
dates and source claims remain byte-for-byte unchanged. This packet does not
approve geography, validate source-derived IoU, or authorize an import.

## Scope and retained findings

The exact frozen roster contains 230 IDs: 53 Argentina ADM2 and 177 Chile ADM3
features, joined to the baseline feature files pinned at
`0799920a604df931acaf4e32c3234da16d665ab5`. It spans 29 parents. Reproduction
reconciles all 230 comparison and assessment records, the retained 116 justified,
113 correction-needed and 1 insufficient-evidence dispositions, 228 matched
rows, and 242 geometry components from the pinned baseline. Two old comparison
rows lack a recorded component count; the omissions remain exactly
`gb:ARG:ADM2:61730980B63808307170695` and
`gb:ARG:ADM2:61730980B85851407891039`.

These are counts for the issue's declared subset. They do not imply complete
Argentina or Chile coverage. The retained source inventory scoped 53 of 54
Argentina South ADM2 candidates and 177 of 252 Chile Central ADM3 candidates;
neighboring candidates remain in their existing issues. No cross-border or
regional-interior conclusion is made.

## Reproduction and safeguards

Use Python 3.12.14, Shapely 2.1.2 and GEOS 3.13.1, and run from the repository root. The
wrapper validates a raw six-row pointer ledger before any identity mapping,
then runs the unchanged validator as a real `__main__` entry point. It intercepts
only the seven exact legacy output writes and their subsequent reads, so the
historical packet is not modified. A unique run directory is reserved before
the validator runs; each output is created exclusively and a publication
receipt is linked into place only after all seven products are complete.
Failed runs remain without a success receipt.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/south-america-batch3-validator-integrity-1131-erratum/controls.py
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/south-america-batch3-validator-integrity-1131-erratum/partial_write_control.py
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/south-america-batch3-validator-integrity-1131-erratum/pair_failure_controls.py
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/south-america-batch3-validator-integrity-1131-erratum/compare_runs.py --pair-id <fresh-lowercase-slug>
node scripts/evidence-quality.mjs research/geography/south-america-batch3-validator-integrity-1131-erratum/evidence-quality.json .
```

The `verified-pair-04` run starts two separate Python processes against the same
unchanged source and ledger. Each run has a unique execution ID, UTC timestamp,
code SHA-256, complete source-ledger SHA-256, Python/Shapely/GEOS versions, seven
product hashes and an exclusive publication receipt. All seven products matched byte-for-byte. Only
after that comparison, the pair packet replaces the inherited one-run
`reproducibility.json` claim with a receipt binding both executions and the
six regenerated products. The original generated one-run reproducibility file
is retained inside each raw run directory for audit, but is not the pair's
passed receipt.
The earlier complete `verified-pair-03` reproduction is retained as a prior
paired run; `verified-pair-04` also records the GEOS runtime explicitly.

`pointer-destination-controls.json` records actual CLI rejection for duplicate
records at the first, middle and last positions; missing and foreign IDs; wrong
path and vintage; wrong LFS OID and size; existing file/directory destinations;
a dangling symlink; and a path escape. Rejected ledgers do not create run
directories. The retained exact duplicate-last fixture is 7,992 bytes with
SHA-256 `e7c9001573ce8657a3fac4c1e52d993f9aca48d66af5a5e3ca1b1dde10278c01`.
The partial-write control injects a failure in the actual exclusive publisher
after the first product: the partial file remains, and no success receipt is
published. The full entry point also retains the original false-parent control
(old checker accepts; current validator rejects) and all nine existing
meaningful negative controls. `pair-failure-controls.json` additionally drives
the actual pair orchestration through a failed second-process result and a
one-file mismatch; neither case publishes a completion receipt. The associated
`runs/*control-run-*` files are synthetic mismatch fixtures with no publication
receipt, not successful validator executions. Existing-file and directory
sentinels remain untouched as collision controls.

## Inputs, dates, licenses and remaining uncertainty

The current #1350 issue and all comments were retrieved from the authenticated
GitHub REST API on 2026-10-09 UTC; exact response bytes and hashes are recorded
in `source/issue-retrieval-receipt.json`. The 16 issue-declared source/code/input
pins and additional actually read pointer/API files are bound to immutable
main `664dfe7a682fb3838ce827600792c832235a238a`. The six retained GitHub
Contents API responses and Git LFS pointer files identify upstream commit
`9469f09592ced973a3448cf66b6100b741b64c0d`. The repository API bytes
authenticate the Git pointer blobs and declared OID/size, not the raw geometry
payloads.

The Argentina and Chile ADM2/ADM3 records retain the geoBoundaries 2020 source
labels and exact paths, but neither 69,702,323-byte nor 171,783,952-byte raw
LFS geometry was downloaded or independently hashed. The prior raw-SHA claims
do not match the authenticated pointer OIDs, while their byte sizes do. The
historical packet's CC BY 3.0 IGO text is not independently reverified. Restore
each raw object only from its exact pinned LFS path, verify the stated pointer
OID and size, and independently establish license terms before any reuse.

The 2026-10-05 IGN ANIDA capture and 2023-08-03 Subdere DPA archive are not
retained or re-retrieved here. Their source vintages, complete content and reuse
terms remain unverified; the Subdere archive exceeds ordinary evidence-file
limits. The cited Argentina Law 1186 text, Subdere change log, Marchihue /
Marchigüe name evidence, and WGSRPD release were not re-retrieved. Therefore
source completeness, territorial meaning, boundary agreement, licensing,
regional coverage and current-source IoU remain unresolved and owned by their
existing follow-up issues. The validator repair establishes record and output
integrity only.

See `evidence-quality.json` for exact baseline and output hashes, source
restoration notes, issue bindings, method receipt and explicitly unresolved
findings.

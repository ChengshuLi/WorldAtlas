# Exact reviewed evidence byte bounds

Issue #2069 replaces the generic JavaScript scientific-manifest gate's arbitrary
32 MiB file / 256 MiB packet cutoffs with finite, overflow-checked bounds derived
from its existing exact whole-file descriptors. This is the user-approved
operating-policy simplification, not a new scientific approval system.

## Complete reader chain

Before body acquisition, `evidenceBytePlan` validates safe integer encoded and
paired decoded sizes and checks the complete descriptor sum. Whole-file size and
SHA256 remain exact. Declared gzip expansion is bounded by that exact decoded
size, then checked for exact length and SHA256; valid empty expansion remains
supported. Undeclared legacy gzip keeps its existing finite operating fallback.
Subject JSON, record joins, metric JSON, generated tables and control JSON carry
their existing descriptors through their actual rereads.

The hosted reader admits a finite union of all actual baseline/source/output and
optional old change-receipt paths against complete immutable trees. Each planned
body must have the exact declared size before prefetch. The initial manifest
remains separately bounded at 1 MiB; its actual body is part of the complete
execution inventory. Immutable REST wrappers forward exact expected blob sizes
and finite base64/envelope response allowances through nested wrappers and Git
fallback. Mode/type, full OID/content authentication, ancestry, inventory count,
source identity, hashes, semantic bindings and timeout/quota behavior remain.

The 272 MiB / 512-entry immutable cache and Git prefetch cache do not grow. A
packet exceeding that optimization uses authenticated REST fallback. Unplanned
legacy raw readers retain their previous 32 MiB operating guard. There is no new
universal scientific file ceiling: actual runtime memory, disk, provider and
response limits still apply, and exceptionally large bodies may need streaming
or another separately reviewed implementation.

## Actual frozen Vietnam packet

The unchanged PR #2062 head is
`6ef487cd8f29e714dd10ae963d9fd58c41fd1b54`; its actual PR-base snapshot is
`71d95f45ea0457d60d4b8263bf36ab78316cf0cc`. The manifest is 150,564 bytes with
SHA256 `baebb765c7dafd65a88625fe650cd709e702d6439c4e1f5d3b6163b9a4586557`.
The original 36,065,990-byte source is retained intact.

- 257 whole-file descriptors: 274,678,915 encoded + 22,336,586 declared decoded
  bytes = 297,015,501 descriptor-accounted bytes.
- The optional original/base change bodies add 15,936 bytes to the encoded path
  inventory: 274,694,851 bytes, plus the separately acquired manifest.
- Direct actual `validatePremergeManifest` passed all 257 bodies, 249 change
  receipts and 14 metric bindings in 11.14 seconds, retaining all 11 limits.
- The actual `checkPremergeEvidence` entry point also passed through two nested
  immutable REST wrappers using the read-only local Git adapter retained here.
  Its genuine output records 243 unique OID/body requests and 274,806,024 actual
  transported bytes including the manifest; shared identical OIDs explain the
  smaller value than the complete path inventory. See
  `frozen-vietnam2062-premerge-check.json` for the actual time and limits.

The adapter uses already authenticated immutable Git objects with network
disabled. It exercises production wrapper, size-forwarding and premerge logic,
not a live GitHub HTTP round trip. The production HTTP bounded-response and Git
fallback paths have their own focused controls. No scientific producer,
constructor, geographic consumer, selector composition, deployment or acceptance
was repeated or claimed. Current cumulative selections need their separately
coordinated additive composition before data delivery.

## Reproduction and controls

`focused-tests.log` records 74 passing focused tests, zero skips. Run:

```sh
node --test --test-concurrency=2 \
  test/evidence-byte-bounds.test.mjs test/evidence-quality.test.mjs \
  test/premerge-evidence.test.mjs test/historical-evidence.test.mjs \
  test/evidence-family-record-binding.test.mjs \
  test/immutable-git-blobs.test.mjs test/git-blob-transport.test.mjs
```

Controls include real 36,065,990-byte candidate/Git/REST reads, a packet above the
old aggregate cap, exact gzip expansion above the old cap, empty expansion,
wrong encoded/decoded hashes and lengths, malformed/overflow bounds rejected
before body I/O, real large table/control rereads, nested forwarding and stale
tree rejection, and unchanged cache-overflow fallback. Existing source/subject,
ancestry, path/mode, record, metric and historic-vintage controls also run.

For a locally acquired complete immutable PR #2062 packet, obtain fresh ordinary
GitHub PR/issue/full-files JSON snapshots without modifying the frozen head, then:

```sh
node coordination/engineering/reviewed-evidence-byte-bounds-20261016/check-frozen-premerge.mjs \
  actual-pr2062.json actual-issue2061.json complete-pr2062-files.json
```

This engineering change satisfies only the generic transport-bound acceptance.
It does not rewrite scientific execution-helper operating limits or manufacture
qualified scientific receipts, factual approval, selected counts or publication.

# Worker evidence quality, version 1

The manifest is a reproducible evidence receipt, not a certificate of historical truth. `scripts/evidence-quality.mjs` checks actual inputs and result ledgers without executing submitted packet scripts. Source/method review remains independent work. The versioned schema is a discovery aid; the executable validator also checks hashes, scope, bytes and semantic relationships.

New packets can copy `coordination/templates/evidence-v1.json`, replace every placeholder, and keep the completed `evidence-quality.json` inside their declared owned directory. Never replace an older manifest/source/output in another worker's packet. Older packets are legacy evidence; this first implementation does not retroactively enforce a new gate or authorize imports. Activation is tracked separately in #627.

## Inputs and identity

Record the exact baseline commit and actual containing file paths. Hash raw whole-file bytes with SHA-256; `hash_kind` must be `file-bytes`. Per-entry hashes are different evidence and must never substitute for file hashes. For compressed inputs record both compressed and uncompressed bytes/digests. `baseline.pins` maps named pins to hashes and `baseline.pin_files` binds every pin to an actual baseline file descriptor. The verifier reads baseline files from the immutable Git commit, not whatever main currently contains.

Subject IDs are sorted before JSON serialization and hashing (`subjectsHash` in the shared module). Every geography subject additionally maps through `baseline.subject_files` to its actual containing GeoJSON file; the validator verifies presence there. A value may remain a path string when the source feature already has the canonical identity in `Feature.id` or `properties.id`. When an authentic source feature stores its identity in multiple string properties, use an explicit version 1 descriptor instead of rewriting the source row:

```json
"subject_files": {
  "gb:AGO:ADM2:16411231B14510444140190": {
    "version": 1,
    "path": "research/geography/EXACT-PACKET/contacts.geojson",
    "id_template": "gb:{shapeGroup}:{shapeType}:{shapeID}",
    "properties": ["shapeGroup", "shapeType", "shapeID"]
  }
}
```

The property list must exactly match each template placeholder once and in order. Every source feature must have a non-empty string value for each property, and the resulting identities must be unique; all declared subjects must resolve within the pinned file. Template strings are literal formatting only, never executable expressions. Subjects mapped to one file must use one identical binding. This verifies structural identity against retained bytes; it does not establish source authority, geometry accuracy or legal/geographic approval. Track containing paths as you read the world index; never infer filenames from an absent feature property. Regional frozen scopes, adjacent-tier chains and historical territorial applicability still need their existing release/certificate gates; this receipt does not replace those checks.

## Complete original family records in gzip JSONL parts

A mixed source-research scope can include an original family record alongside
real component/contact features. Use a version 2 `gzip-jsonl-record` subject
binding for a complete original `gap-source-batch:` record, while real GeoJSON
subjects retain their existing direct/composed bindings. This is identity custody
only; it does not approve source authority, geometry, physical class, dates,
cause, rights, ownership or publication.

```json
"subject_files": {
  "gap-source-batch:65911e15791d12ebb2ccacf5": {
    "version": 2,
    "kind": "gzip-jsonl-record",
    "path": "coordination/engineering/global-actionability-routing-20261007/results/families-005.bin.gz",
    "commit": "c9122b55d20c4992fca5b0332e4faacbc08b139a",
    "record_offset": 2281306,
    "record_bytes": 6281,
    "record_sha256": "4b9610e86b7d6517b6c32fdead65bd6c3f73e868ac3413e6a506947071097c1b"
  }
}
```

The referenced `baseline.version: 2` file must declare its complete encoded and
uncompressed byte lengths and SHA-256 values. The original commit must remain an
ancestor of the actual PR base. Offsets and lengths refer to the decoded original
bytes and include the final newline. The reader authenticates the entire source,
then verifies the complete record's boundary, full bytes/hash and native `id`.
It rejects duplicate family IDs among complete records in that containing part.
Original leading/trailing stream fragments cannot bind a subject; this binding
never certifies completeness of the larger concatenated source stream.

The complete encoded baseline, retained-source and output inventory plus unique
record-source decoded bytes must fit the 256 MiB budget before any body read or
decompression. Each ordinary encoded/decoded file and record retains the 32 MiB
limit. Later whole-file checks, exact accounting, 512 descriptors and the existing
ancestry gate still apply. A small compressed body cannot waive the decoded cap.
Candidate-generated registries cannot replace independent original source records.

## Historical files from multiple commits

Use `baseline.version: 2` only when the original evidence requires files from
more than one immutable commit. The enclosing manifest and issue evidence contract
remain version 1. `baseline.commit` remains the evaluation snapshot; it does not
select the bytes for version 2 file descriptors. Every `baseline.files` descriptor
must additionally declare its own full 40-character `commit`. Preserve the original
path, size, hash, compression descriptors and named pins.

For example, this field fragment binds an old input and a later retained result
without pretending they existed together. Replace the placeholders with verified
commits and existing whole-file descriptors:

```json
"baseline": {
  "version": 2,
  "commit": "EVALUATION_COMMIT",
  "files": [
    {"path": "original-input.json", "commit": "ORIGINAL_COMMIT", "bytes": 123, "sha256": "ORIGINAL_SHA256", "hash_kind": "file-bytes"},
    {"path": "retained-result.json", "commit": "LATER_COMMIT", "bytes": 456, "sha256": "RESULT_SHA256", "hash_kind": "file-bytes"}
  ],
  "pins": {"original": "ORIGINAL_SHA256", "retained": "RESULT_SHA256"},
  "pin_files": {
    "original": {"path": "original-input.json", "commit": "ORIGINAL_COMMIT"},
    "retained": {"path": "retained-result.json", "commit": "LATER_COMMIT"}
  }
}
```

The example sizes are illustrative, not generated findings. A historical reference
may remain a path string only when that path has exactly one declared vintage.
For repeated paths, `pin_files` and `subject_files` use `{path, commit}` objects.
A composed subject binding keeps its version, properties and identity template,
and adds `commit` to select a historical file when needed.
A prior-evidence `subject_inventory` selects its retained roster with `commit`;
a structured `record_checks` row selects its reference with `reference_commit`.
Missing, duplicate or ambiguous identities are errors. Candidate sources and
outputs still use candidate bytes and must not declare historical commits.

A metric's `input_sha256` authenticates its input independently of its
`evaluation_commit`. In version 2, use `input_file: {path, commit}` when the same
hash identifies multiple declared files. For a candidate input, the commit is the
literal `candidate`; historical inputs use their immutable SHA. Unique hashes
need no extra selector. Archived metrics keep their true evaluation vintage;
current metrics still use the actual PR base. Do not refresh old results merely
to satisfy a descriptor.

All historical file commits and the evaluation snapshot must be ancestors of the
actual PR base in the trusted hosted gate. The local reader checks ancestry against
checkout HEAD; local validation alone cannot establish PR-base ancestry. Custom
readers must provide a synchronous `assertAncestor(commit)` that throws on failure.
There are at most 16 distinct historical/evaluation commits, with the existing file,
phase and descriptor budgets unchanged. Verification never executes packet code.

Without `baseline.version: 2`, files continue to come from the single baseline
commit. Per-file commits, versioned references and explicit metric selectors are
rejected rather than silently ignored. Valid legacy manifests remain supported.
If a runner executes a newer helper than an original pinned helper, inventory the
actual executed helper at its own commit as well; preserve the original helper pin
and independently verify the execution binding. Two versions of the same path do
not establish which one executed by themselves.

## Sources and methods

Each source needs a stable local ID, canonical HTTPS URL, role, vintage, retrieval date, reuse terms and verification status. Immutable upstream tags/commits and original restoration hashes belong in the source description/restoration record. Lawfully retained source bytes need `license.status=redistributable` and file descriptors. Restricted/unknown-terms sources use `restoration-only`, instructions and an explicit verification limit. Do not copy a restricted PDF merely to satisfy CI. A failed access attempt is a gap, not evidence for a geographic assertion.

Record software versions, units and method descriptions. Geographic methods explicitly record longitude/latitude order, CRS, area and distance method. Correct-looking values cannot validate a coordinate transform; independent controls and the shared scientific helpers are needed. All reproduction commands are descriptive strings; the validator never executes them.

## Results and honest progress

Maintain one numeric ledger (`metrics`); machine-readable summaries reference its exact IDs/values/units. Derive displayed README tables from it and review prose manually. Fractions record numerator/denominator. Every metric identifies an input hash, evaluation commit and `current`, `baseline` or `archived` vintage. Current/baseline metrics must use the declared baseline commit. An archived pre-restoration omission screen cannot be relabeled current merely because its source bytes remain intact.

Conclusions cite known sources and say `supported` or `unresolved`. This linkage does not prove the source supports the fact: a reviewer must inspect it. Separate research, implementation and geographic-approval stages. Geography/source-only workers cannot assert implemented/published/approved geography. Completing an initial evidence packet with unresolved findings never approves a region or authorizes historical imports.

Run from the repository root:

```sh
node scripts/evidence-quality.mjs PATH/TO/evidence-quality.json
node --test test/evidence-quality.test.mjs
```

`bytes-verified` means the listed bytes and mechanical relationships match. `limited` means bytes/source evidence remain unverified; inspect the returned limits. Neither outcome means geographic accuracy, valid licenses, successful deployment or correct ancient history. Missing required bytes, wrong hashes, malformed pins, unsafe paths, unsupported stage claims and inconsistent summaries are errors. Default budgets are 32 MiB per input/decompressed output and 256 MiB total declared input bytes; exceptionally large lawful data needs an explicitly reviewed approach rather than disabling limits.

Engineering provides shared tooling; geography/history workers populate their own manifests. Corrective packets retain superseded outputs and dates. Do not run generators against current main before pin checks, overwrite originals, silently repin a baseline, or grant unsupported exceptions. GitHub Issues tracks adoption and implementation status, not this document.

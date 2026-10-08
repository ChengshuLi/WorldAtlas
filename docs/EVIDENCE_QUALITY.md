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

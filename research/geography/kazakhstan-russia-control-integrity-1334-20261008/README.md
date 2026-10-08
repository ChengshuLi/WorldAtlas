# Kazakhstan–Russia #1334 control-integrity correction

Issue: [#1491](https://github.com/ChengshuLi/WorldAtlas/issues/1491)

This additive packet repairs the bounded evidence-control layer around the
retained #1334 assessment. It does not alter or rerun the original geometry
producer, rewrite the #1322 packet, recalculate scientific classifications,
certify boundaries, or resolve the existing Kazakhstan/Russia source-count,
license, territorial-role or physical-evidence questions.

## Reproduction

Use Python 3.12 and the exact preserved main baseline recorded in
`evidence-quality.json`. From the repository root run the actual new control
entry point twice with different fresh names:

```sh
python3.12 research/geography/kazakhstan-russia-control-integrity-1334-20261008/control_integrity.py \
  --baseline 016fa2c0cce935382d0995a503bfc09d3e7ac513 --vintage controls-reviewed-one
python3.12 research/geography/kazakhstan-russia-control-integrity-1334-20261008/control_integrity.py \
  --baseline 016fa2c0cce935382d0995a503bfc09d3e7ac513 --vintage controls-reviewed-two
python3.12 research/geography/kazakhstan-russia-control-integrity-1334-20261008/test_control_integrity.py
```

The CLI loads the exact baseline-pinned `scripts/evidence/immutable.py` bytes,
authenticates the retained freeze, producer and input-manifest hashes, and admits
the full three-file output vintage before parsing report/source bytes. For both
retained complete runs it compares each actual output's size and SHA-256 to the
actual output manifest and run receipt, enforces the complete four-product
inventory, and joins the candidate, family and contact records against the
original complete handoff. It parses the full and simplified 2017 Kazakhstan
GeoJSON source products and compares their unique native `shapeID` sets. Every
new successful vintage uses exclusive byte publication and writes
`publication.json` last.

The preserved candidate roster retains the original 28 compatible and 24
partial/unbound source-relative classifications. The control checks these
counts from actual candidate rows on both retained runs; they remain processing
labels rather than geographic findings.

The positive receipt is identity/output-custody evidence. Eleven actual negative
controls mutate complete product bytes or remove products, falsify a product
manifest hash, omit/duplicate/rebind contacts,
duplicate a family with an empty membership, alter family membership, and change
an actual parsed source ID. The test suite exercises these predicates, runs the
documented CLI twice, and checks output collisions, directories, dangling and
live links, symlinked ancestors, escaped vintage names, and a late final-receipt
write failure. A failed new vintage remains a failed attempt without a completion
receipt; originals and occupied targets are left unchanged.

## Preserved limits

- The original producer and source comparison executables are authenticated by
  their recorded frozen code bytes, but this correction does not rerun either
  original executable. The four products from both actual retained runs are
  independently read and byte-compared.
- The full Kazakhstan source identity comparison is executed (174 IDs in each
  retained product). The 120,489,189-byte full-resolution Russian source exceeds
  the repository's 32 MiB file cap and was not loaded or replayed; its preserved
  prior identity result is not upgraded here.
- The retained input manifest represents over 1 GiB of source/physical inputs.
  This bounded control authenticates the frozen manifest and producer receipts,
  but does not reopen every oversized or unrelated physical source input.
- A matching identity set is not geometry equivalence. This work establishes no
  current legal boundary correspondence, source completeness, source-rights
  clearance, physical truth, geographic approval, import eligibility or
  publication authority. Original #1334 remains incomplete for those findings.

All newly written files are confined to the issue-declared directory. Earlier
assessment inputs, receipts, failed attempts, source bytes, pins and uncertainty
remain in the original packet unchanged.

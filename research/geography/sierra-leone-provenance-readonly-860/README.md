# Sierra Leone provenance receipt verifier, superseding 2026-10-05

This packet addresses only the retained-receipt overwrite behavior reported in [issue #1062](https://github.com/ChengshuLi/WorldAtlas/issues/1062). It adds a verifier in this new owned directory. The original #746/#784 packet, source files, verifier, and 789-byte `verification-results.json` are preserved byte-for-byte. Do not run its old `verify.py` directly: that program attempts `Path.write_text` on the retained receipt. Use this packet's checker.

## Read-only reproduction

From the repository root, with Python 3.10 or newer:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 research/geography/sierra-leone-provenance-readonly-860/verify.py
node scripts/evidence-quality.mjs research/geography/sierra-leone-provenance-readonly-860/evidence-quality.json
```

The checker verifies four predecessor files against their exact hashes and the PR-base Git blobs, executes the predecessor verifier twice while intercepting its one `Path.write_text` attempt per run in memory, and compares both attempted byte streams with the existing retained receipt. Any unexpected write target or changed/mismatched input fails. Its separate subprocess control feeds an existing sentinel mismatch to the same comparator, requires exit code 1, and checks that both the sentinel and expected receipt remain byte-identical. The normal command only reads repository evidence and writes its control scratch files under the operating system temporary directory.

`--record-new` is a one-time evidence-generation command. It creates the explicitly named `vintages/20261005-readonly-check/` directory and all four result/control files with exclusive creation; an existing vintage or file causes failure. Ordinary verification does not use this flag and never rewrites those files.

## Scope and inherited geographic evidence

The exact Sierra Leone scope is the twelve IDs in issue #1062, listed in the retained result and in `evidence-quality.json`; the predecessor packet also checks 37 Togo ADM2 context rows. The prior source assessment identifies the Sierra Leone source layer as ADM2 “Districts” and the Togo context layer as ADM2 “Prefectures.” The issue asks us to preserve the country-bound license provenance comparison, not to assert that these generalized source units are legal boundaries, complete current districts, or equivalent neighboring administrative tiers.

The inherited geoBoundaries metadata snapshots were retrieved on 2026-10-04 and represent 2017. Sierra Leone metadata attributes the source to Government of Sierra Leone and OCHA ROWCA and declares CC BY 3.0 IGO; Togo metadata attributes OpenStreetMap and Wambacher and declares CC BY-SA 2.0. Their exact compressed hashes, byte sizes, restored hashes, and Git restoration paths remain in the original packet's `license-provenance.json`, `issue-contract.json`, and `evidence-quality.json`. Restore using the exact `git show f92b1774aedcaaaf72ac0fe4cc45857dd641d7d1:<path>` instructions there. The current repository retains those bytes under `data/regional-review/regional-review-9d08839e1cdb0c8f/sources/`; no source was recopied here.

The exact pinned predecessor receipt records that all twelve subject IDs, names and direct parents, plus all 49 Sierra Leone/Togo parent chains, match the pinned canonical partition and hierarchy. In the Atlas mapping these subjects currently sit under the existing Eastern, Northern or Southern province wrapper, then the Sierra Leone area and West Tropical Africa region; this is an inherited crosswalk observation, not proof that the wrappers have current legal or statistical purpose. These are structural checks against the pinned Atlas partition/hierarchy. They do not establish statutory status, territory completeness, source legality, positional accuracy, adjacent-country legal boundaries, or regional suitability. The earlier positive research finding is the metadata-declared license mismatch for all 12 SLE records and matching metadata declarations for 37 TGO context records. License reuse remains legally unadjudicated. This narrow follow-up neither reopens the broader #746 scientific audit nor changes any geographic feature, ID, parent, boundary, or release pin.

## Evidence

`vintages/20261005-readonly-check/verification-results.json` records the inherited scope, exact predecessor pins, equal repeated outputs and limits. Separate positive, negative and reproducibility controls are bound by the version-1 evidence manifest. The evidence is a verification handoff only; it does not certify geography, a region, publication, or historical import readiness.

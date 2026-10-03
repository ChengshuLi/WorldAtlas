# Bouvet–Tristan immutable baseline correction (#643)

This packet repairs a provenance and reproduction defect in the #399 extract. It does **not** revise the geographic assessment, verify the accuracy of inherited source claims, alter a footprint, or imply regional approval.

## Corrected result

At the original source baseline `3d2c5cee2fa748a7eff90051088b6998c9c84968`, a scan of all 34 ordinary `data/geography/part-N.json` files finds each in-scope feature exactly once, both in `data/geography/part-28.json`:

| Exact ID | Name | Actual containing file | Occurrences |
| --- | --- | --- | ---: |
| `SHN-4865` | Tristan da Cunha | `data/geography/part-28.json` | 1 |
| `atlas:coverage:BVT+00?` | Bouvet Island | `data/geography/part-28.json` | 1 |

The older extract listed `data/geography/part-0.json`, because it inferred the part from an absent `properties.part` value. Its bytes and the other six files in the original #399 packet are inventoried and hash-pinned in `correction-spec.json`; they remain unmodified. The old packet's listed `part-0.json` is retained as a historical claim, not treated as the containing-file result.

The two geometry hashes, names, and parent identities reproduce the old extract at the original immutable baseline. Complete parent chains, source projection rows, region envelope references, and review-group membership rows are emitted as corroborating structural context, not as geographic validation.

## Vintage and integrity boundary

- Geography, hierarchy, release manifest, source inventory/projection, and regional handoff inputs are read only from baseline commit `3d2c5cee2fa748a7eff90051088b6998c9c84968`.
- The original #399 issue metadata, including its exact member list and frozen-scope/release expectations, is separately snapshotted at `4909f04e6e035ffc003d237db68323d005ccdb89`. It is identified as a scope snapshot, not passed off as source geography from the earlier baseline.
- `correction-spec.json` binds the commits, all source-file byte lengths and SHA-256 hashes, compressed and expanded hashes for gzip inputs, all 34 scanned parts, actual containing files, original packet file hashes, and issue/release pins. The verifier pins the spec's own SHA-256 in its source.
- The verifier checks the issue scope, v5 hierarchy/footprint pins, macro-certificate hash and research-only flag, frozen region envelope, all source bytes, unique ID occurrence, and consistency with the original packet **before opening an output file**. It refuses mismatched commit overrides, unsafe output paths, symlink targets, and overwriting existing evidence.
- No current-main geography refresh is included. A later current-main reproduction must be a distinct, separately identified vintage.

The inherited source citations, source reference dates, stated licenses, retention/restoration instructions, and limitations remain in the original packet's [`README.md`](../regional-review-dbe207dead8603ae/README.md), assessment, and shoreline-screen files. This correction preserves and hashes those artifacts rather than copying or relicensing their source material. It makes no new authoritative-source claim and does not change the existing uncertainty about unretained pages or the binary shoreline original. The commit-pinned repository inputs are lawful Git blobs already present in repository history; this packet stores descriptors and generated assessment output, not duplicate source datasets.

## Reproduction and controls

Run from the repository root with Python 3:

```sh
python data/regional-review/bouvet-tristan-baseline-correction/build_immutable_extract.py
python data/regional-review/bouvet-tristan-baseline-correction/build_immutable_extract.py --check
python data/regional-review/bouvet-tristan-baseline-correction/verify_controls.py
```

The first command creates `corrected-baseline-extract.json` exclusively inside this owned directory. It will not overwrite an existing file. `--check` recomputes from the pinned Git commits and compares exact output bytes. The controls exercise repeat generation, rejection of a different baseline commit before output creation, rejection of a changed candidate in check mode, and overwrite protection. Their captured results and output hash are in `control-results.json`.

## Integration boundary

This packet supersedes only the immutable extraction/containing-file evidence defect. It links the original review/parent umbrella #399/#398 and the engineering integration follow-up #400. Engineering may use the corrected file binding when integrating evidence, but still must validate the complete regional branch and all outstanding source/tier findings before publication or any location-attribute research import becomes eligible.

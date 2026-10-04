# Pinned American Samoa and Wallis–Futuna source-profile reproduction

Issue [#663](https://github.com/ChengshuLi/WorldAtlas/issues/663), follow-up to [#616](https://github.com/ChengshuLi/WorldAtlas/issues/616). This issue-owned packet repairs repeatability for the eight existing Natural Earth source profiles. It does not edit their original research packet or claim that a changed output is an administrative correction.

## Two immutable inputs

- **Project geography baseline:** `f592b3d8b72f40036218803d2c70c733112e4d37`, the exact baseline already named in the #616 evidence manifest and generator. `evidence-quality.json` pins all 36 parts enumerated by that commit's `data/world-index.json`, the actual `part-28.json` containing all eight assigned IDs, complete hierarchy, macro release 5, the geography gate, current membership inventory, and regional handoffs. The helper checks each whole file before generation, searches every indexed part for duplicate/missing subject IDs, and verifies all eight full five-level parent chains.
- **Original #616 source snapshot:** merge commit `6c6271af6b0dac49b82eaafb2db4de8b9c4611f2`. `source-snapshot-pin.json` records each ordinary file in the original packet, including retained source sidecars, Census archives, the INSEE workbook, original outputs and their compressed/uncompressed hashes. The driver checks the original source receipts against those exact Git blobs and compares the current repository copies before running.

These two commits answer different questions: the first freezes project geography inputs; the second freezes the original source and generator packet. `build_audit.py` is restored from the second commit into a private scratch tree containing the first commit's verified geography files. Its only adaptation redirects writes into a separate private output directory. Original files are never rewritten.

## Reproduction and outputs

The new vintage is `vintages/20261003-f592-source-profile-reproduction-v1/`. It contains seven regenerated JSON products, a full source-snapshot file inventory, a per-output old/new byte and semantic comparison, a run receipt, and positive, negative and two-run reproducibility controls. New result JSON is canonical compact UTF-8; original #616 files retain their old pretty-printed bytes. The comparison reports each original and new uncompressed JSON byte length and SHA-256 separately, and lists semantic JSON difference counts without treating byte changes as changed facts. All seven regenerated outputs are semantically equal to their #616 counterparts; the byte hashes differ because the new vintage uses deterministic canonical JSON serialization. No substantive conclusion changed in this reproduction.

From the repository root:

```sh
python3 research/geography/pacific-ne-source-reproduction-followup/reproduce.py --check 20261003-f592-source-profile-reproduction-v1
node scripts/evidence-quality.mjs research/geography/pacific-ne-source-reproduction-followup/evidence-quality.json .
node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs
```

`--check` is the default workflow and is read-only in the repository; it generates two runs in private temporary directories and compares every output byte with the stored vintage. Creation is explicit and exclusive:

```sh
python3 research/geography/pacific-ne-source-reproduction-followup/reproduce.py --new-vintage 20261003-f592-source-profile-reproduction-v1
```

An existing destination is rejected before project inputs are read or any output is written. The negative controls test incorrect project and Natural Earth sidecar hashes, plus an existing destination whose bytes must stay unchanged.

## Source limits and interpretation

The inherited source descriptions and licenses remain in the new evidence contract. Natural Earth is a public-domain cartographic reference, not a legal boundary authority. The U.S. Census materials describe statistical areas and do not establish jurisdiction, title or ownership. INSEE's 2018 tables have Open Licence 2.0 terms and describe statistical populations, not authoritative legal boundaries. The American Samoa code and Territorial Assembly pages remain restoration-only where reuse or exact primary-source access was not established. The GSHHG record is a physical shoreline screen, not settlement or administrative evidence. The retained GSHHG screen is carried in the source snapshot inventory; this reproduction does not expand its restricted-size upstream archive.

The output inventory keeps political, administrative, statistical and physical-source roles distinct. It makes no sovereignty, historical, settlement-completeness or legal-boundary conclusion. Any semantic or cross-region correction requires separate sourced work and coordination with affected neighbors; this reproducibility packet cannot approve a region or enable historical imports.

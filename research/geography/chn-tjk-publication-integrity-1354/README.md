# China–Tajikistan publication-custody correction

This additive packet addresses the comparison reader used by the retained PR #1354 workbook-inventory correction. The original workbook, source inventory, subject records, two original producer runs, and earlier comparison remain byte-for-byte untouched. New files and runs are confined to this packet.

The predecessor producer source and immutable helper are authenticated from their actual historical commits. The successor executes the predecessor’s pinned capture and pure output functions in memory; it never calls the predecessor’s writer. Each comparison validates both complete publications before it can emit a reproducibility result: supported version, `complete` status, exactly four unique run-relative output paths, regular nonsymlink files, and exact `file-bytes` size and SHA-256 descriptors. It then reads and compares every actual product byte. The comparison destination is exclusively reserved before product reads; publication receipts are installed last.

## Reproduce

From the repository root with CPython 3.12.14 (substitute your installed `python3.12` executable):

```sh
python3.12 -I -B research/geography/chn-tjk-publication-integrity-1354/reproduce.py --vintage run-20261008-a1
python3.12 -I -B research/geography/chn-tjk-publication-integrity-1354/reproduce.py --vintage run-20261008-a2
python3.12 -I -B research/geography/chn-tjk-publication-integrity-1354/reproduce.py --compare run-20261008-a1 run-20261008-a2 --vintage compare-20261008-a1
python3.12 -I -B research/geography/chn-tjk-publication-integrity-1354/test_publication.py
node scripts/evidence-quality.mjs research/geography/chn-tjk-publication-integrity-1354/evidence-quality.json
```

The final CPython 3.12.14 producer runs `run-20261008-b1` and `run-20261008-b2`, and their comparison, are retained in `vintages/`; all four complete payloads are byte-identical. Earlier `a1`/`a2` trials are also retained with their recorded CPython 3.7.3 runtime, but are not relied on for the final result. The tests invoke the actual CLI for failed/unsupported status and schema version, duplicate descriptors, foreign same-basename paths, missing products, and altered products; each invalid comparison exits unsuccessfully and leaves no passing completion receipt. Both actual CLI writer entrypoints reject occupied file, directory, symlink, dangling-symlink, and traversal destinations. A forced failure at the final receipt link leaves partial output without a completion receipt, exercising the shared exclusive writer.

## Scope and limits

The evidence manifest binds the three issue subjects and all twelve exact whole-file pins to their actual historical commits. The correction is a publication-custody mechanism only. It does not reacquire the official statistics page or review its license, validate administrative counts, establish territorial meaning or parent relationships, assess boundary placement or geometry completeness, establish current status or neighboring granularity, or approve geographic publication. The retained workbook is dated to counts as of 2025-01-01 and is not boundary geometry. Those questions remain explicit unresolved research and source-owner follow-ups; no core geography, live data, deployment, or publication state is changed.

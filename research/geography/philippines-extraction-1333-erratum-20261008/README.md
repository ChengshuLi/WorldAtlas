# Philippines #1333 bounded extraction erratum

This packet corrects preservation and admission handling for the accepted #1333
extraction path. It does not rerun or replace the historical extraction. The
legacy producer and acceptance harness remain pinned and unchanged because the
issue owns only this additive directory.

## Reproduction

Use the repository's Python 3.12 runtime (the standard library and committed
`scripts/evidence/immutable.py` helper only):

```sh
python3.12 methods/guarded_run.py
python3.12 methods/test_guarded_run.py
python3.12 methods/run_bounded_controls.py --prefix controls-20261008-g  # use a fresh unused lowercase prefix for each reproduction
```

The first command prints a `status: refused` result after it authenticates the exact prior receipt and its complete unique
input inventory, then refuses the original operation from size metadata before
decompression, concatenation, or product generation. No files are created by
that refusal. It must not be changed to split the same logical bodies or omit
their outputs to obtain admission.

Tests exercise the bounded `NewVintage` producer boundary with two independent
synthetic (non-geographic) runs and the separate import-safe acceptance reader
in `methods/verify_bounded_run.py`. They cover destination collisions,
sentinels, dangling and parent symlinks, complete receipts, partial inventory,
missing descriptors, body/phase/output limits, and output mutation. Synthetic
fixtures establish preservation behavior only; they make no claim about
Philippine geography or successful full extraction.

## Original operation admission

The predecessor's exact recorded closure contains 71 unique stored files and
78,605,746 raw bytes. Its declared decoded inputs sum to 459,875,028 bytes;
the issue's conservative decoded lower bound excludes the identical retained
source body and is 452,803,761 bytes. The issue's conservative complete-phase
lower bound is therefore 531,409,507 bytes before generated products, above
268,435,456 bytes. The two complete logical routing streams are 208,391,779
component bytes and 111,223,285 family bytes, each above the 33,554,432-byte
ordinary/decoded file ceiling. Descriptors, whole raw blob hashes and lengths
are checked before any gzip reader is opened. No giant extraction was run.

The source-relative comparison results, source authority, source-vintage
suitability, legal reuse, neighboring granularity and regional completeness
remain inherited or unresolved exactly as recorded in the predecessor packet.
This erratum makes no new geographic finding, source adjudication, import
approval, or publication request.

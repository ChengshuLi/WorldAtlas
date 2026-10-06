# Issue #413: Zambia and Zimbabwe evidence packet

This directory is the exact owned evidence path declared by issue #413. It reviews 102 frozen Atlas locations and their 11 in-scope province parents. It contains no shared geography edits and does not approve the Southern African region or its boundaries.

## Reproduce the roster and assessment

From the repository root, run:

```sh
python3 data/regional-review/regional-review-9203cb61c3883e07/reproduce.py
```

The script uses Python's standard library, the retained source files in `source/`, the issue's frozen scope snapshot, and the pinned `data/geography/part-28.json` and `data/administrative-sources.json`. It regenerates `subject-assessment.csv` and prints scope, source-roster, classification, and hash checks. The declared 102-member scope digest does not match the standard compact-JSON digest computed from the preserved unique ID list; the script reports both without changing the saved issue pin. The exact count and baseline membership are checked independently. It does not establish polygon correctness.

Two consecutive runs on 2026-10-05 produced byte-identical summaries, retained in `source/reproduction-run-1.json` and `source/reproduction-run-2.json`. Both report an assessment CSV SHA-256 of `b51281dece57dc59a18bd1c8b1b21bcb1cd0a9ae3529e3ddaa48a2b0380095f2`; explicit positive-roster, deliberate omitted-member negative, and byte-reproducibility receipts are retained beside them. The declared-vs-computed scope digest mismatch remains visible in both run records. `evidence-quality.json` inventories baseline/source/output bytes and reports `limited` because specified official sources are restoration-only or could not be verified; it does not imply geographic approval.

## Findings at a glance

- All 102 frozen locations resolve to the pinned `part-28.json`; assessment includes every location and all 11 scope-listed province parents (113 rows total).
- The pinned geoBoundaries files contain 116 ZMB ADM2 features and 91 ZWE ADM2 features. Atlas carries the 91 Zimbabwe source rows once: 87 standalone district locations plus four source members inside `atlas:city:ZWE-525`.
- The 14 Eastern Province locations in this issue all have direct ADM2 source identities, but current ZamStats and Eastern Province Administration list 15 Eastern districts. The fifteenth, Chama (`gb:ZMB:ADM2:96606910B17560798529879`), is assigned to Muchinga in the 2020-pinned Atlas hierarchy and is in issue #412's distinct Zambia scope. A sourced handoff is on #412.
- Natural Earth labels `ZWE-525` as `Harare`, type `City`, but its `gn_name` is `Harare Province`; ZIMSTAT's 2022 report describes Harare Province with Harare Urban, Chitungwiza Urban, and Epworth. The Atlas item aggregates four older geoBoundaries ADM2 rows. Available sources do not resolve whether that is a suitable metro-city territory or an over-broad repeated province tier. The finding remains **insufficient evidence**, with a bounded boundary/source-restoration handoff recommended.
- The bounded Harare source-restoration follow-up is [#1040](https://github.com/ChengshuLi/WorldAtlas/issues/1040). It remains blocked behind #413 and Geoportal source access.
- Source roles and name/ID crosswalks do not establish the correctness or currentness of any polygon. All 113 classifications therefore carry a separate `geometry_assessment=insufficient-evidence`.

See [ASSESSMENT.md](ASSESSMENT.md) for detailed findings and [source/PROVENANCE.md](source/PROVENANCE.md) for source versions, licenses, hashes, and restoration instructions.

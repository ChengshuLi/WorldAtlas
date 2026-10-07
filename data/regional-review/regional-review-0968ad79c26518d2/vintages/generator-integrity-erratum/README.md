# #1308 generator integrity erratum

This is a bounded evidence/generator correction for the 224 Madhya Pradesh subjects inherited from #82. It does not approve territorial assignments, current boundaries, the region, or the historical #82 packet.

## What changed

The original generator already used the retained `Agar-Malwa` roster to prepare the province summary, but omitted that alias for individual records whose parent name is `Agar`. The archived erratum generator uses the same explicit mapping for both. The corrected run adds exactly four fields to each of four original subject rows: roster URL, roster hash, roster system, and exact name match. The four affected subjects are Susner (`7132399B31080084091770`), Badod (`7132399B34961567465885`), Agar (`7132399B49556750707096`), and Nalkheda (`7132399B64060404851550`). All sixteen values were previously null and are now linked to the retained IGOD / Local Government Directory extraction.

The producer resolves its full input set against immutable commit `cbb829672d18801e4310c30896a7ddb13a79b451`, checks all expected whole-file hashes before computing, and refuses an existing output destination. The original `assessments.json` was preserved at SHA-256 `9c5a0cbc869918466c5162aead971a5ccedd72fe42cba007c2660bf120da21ad`. The original 2018 geoBoundaries inputs, exact 224 subject IDs, hierarchy, geographic decisions, Atlas files, sibling partition, and historical helper versions were retained as the evaluation vintage. Historical helper source copies are under `methods/` and hash-match the pinned commit.

Two clean outputs are in `runs/2026-10-07/run-1/assessments.json.gz` and `run-2/assessments.json.gz`. They are byte-identical. Both contain 224 subjects, 27 province groups, and the same classifications as the original assessment: 0 justified, 11 correction-needed, 213 insufficient-evidence. The source retains 6,822 features while its metadata declares 6,836; the 14-feature discrepancy remains unresolved. The original run's 224 valid geometry pairs and 212 topological matches are reproduced, not reinterpreted as geographic approval.

## Source limits and unresolved findings

The retained Agar roster capture is dated 2026-10-05 and has page SHA-256 `190564a28ca08e96785ad20d9a6d2d235c7b0972d731c102ba361c16ac01374e`. The IGOD page is restoration-only because no page-specific reuse terms were identified; the packet retains its URL, hash, retrieval date, extraction and exact names, not the raw HTML. Treat it as an administrative name/count crosswalk only. Its names do not prove jurisdiction, polygon membership, completeness, or current legal boundaries.

Sheopur remains without a retained current roster source. Its roster fields stay unknown. No new official source was retrieved for this erratum. The boundary vintage, completeness, administrative level meaning, territorial role, and current legal polygon correspondence remain unverified; #1085 and #1086 retain their separate source/boundary and engineering scopes. No core geography, hierarchy, release pin, source data, or production data was changed.

## Reproduction

Use the archived Python 3.12.14, Shapely 2.1.2, and PyProj 3.7.2 environment (or compatible pinned environment); choose fresh, nonexistent output paths ending in `.json.gz`:

```sh
python3 data/regional-review/regional-review-0968ad79c26518d2/vintages/generator-integrity-erratum/reproduce_integrity_erratum.py data/regional-review/regional-review-0968ad79c26518d2/vintages/generator-integrity-erratum/runs/DATE/run-N/assessments.json.gz
python3 data/regional-review/regional-review-0968ad79c26518d2/vintages/generator-integrity-erratum/validate_controls.py
```

The output path must not already exist. The input manifest is deliberately pinned to the original #1087 merge vintage and will fail closed if changed.

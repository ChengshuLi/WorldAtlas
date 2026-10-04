# British Columbia 2016–2021 local-unit crosswalk follow-up

Issue #607 asks for exhaustive follow-up on the flagged members of the 376-member 2016 geoBoundaries Canada ADM3 cohort in #485. This packet carries 58 unique flagged source IDs: 20 with no normalized 2021 CSD name match, five with multiple same-name candidates, and 33 whose best overlay is below the #485 95% triage screen. The screens are flags, not evidence of an incorrect legal boundary.

`crosswalk-assessment.json` accounts for every flagged ID, keeps source spelling and parent Census Division context, records the 2021 candidate retained by #485, and joins the candidate 2021 CSDUID to official 2016 predecessor CSDUIDs derived from Statistics Canada's 2021 DB correspondence file. Records distinguish unique-name candidates from spatial-only and ambiguous-name candidates. Every direct source-feature-to-StatCan-2016-CSD relationship is explicitly marked candidate/unresolved; no unsupported successor is declared.

## Source and method

The 2016 geoBoundaries source geometry, the 2021 Statistics Canada Census Subdivision layer and the original screening receipt remain intact in #485. Their truthful source commit is `39188aadf6efdae60357d9d4a1bbb62ffd981003`; the current PR base is separately pinned by the evidence manifest. The exact file paths, byte hashes or retrieval instructions, source dates, publishers, terms and limits are recorded in `sources-manifest.json`.

The new lawful retained file `sources/2021_92-156-X_DB_ID.zip` is Statistics Canada's 2021 Census DB identity correspondence file. It maps 2021 dissemination-block IDs to 2016 IDs and includes the official relation flag. The reproducible script derives each CSDUID from the first seven digits of each DBUID and aggregates unique old/new code pairs and row counts for British Columbia. These are counts of corresponding DB records, not areas or legal succession weights.

The #485 assessment remains a screening source: its geometry comparison uses projected overlap ratios and Unicode/name normalization. A candidate overlap or unique normalized name is not independent proof that a geoBoundaries feature and a Statistics Canada CSD are the same legal or political unit. Duplicate names, sub-95% overlays and no-name cases remain clearly unresolved at source-feature level unless direct administrative evidence supports more. First Nations and municipal names are preserved as records; this packet does not infer political ownership.

## Reproduction

From the repository root:

```sh
python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/build_crosswalk.py
python data/regional-review/bc-admin-vintage-crosswalk-followup-2026/verify_crosswalk.py
```

The verifier checks exact flagged-subject coverage, source-roster uniqueness, candidate targets, correspondence codes, official ZIP integrity and generated output bindings. Original #485 files are read-only and are never copied or rewritten.

## Scope and limitations

This completes an evidence accounting of the 58 flagged rows, not a fresh semantic approval of all 376 source members. It proposes no correction to source membership, shared parent lineage, published hierarchy, geometry or live data. Official DB correspondence corroborates statistical-vintage links for candidate CSD codes but does not itself establish each geoBoundaries ADM3 source identity. The specific remaining direct-feature lineage questions are preserved row by row for coordinated follow-up with #484 where a parent/source lineage correction is actually supported.

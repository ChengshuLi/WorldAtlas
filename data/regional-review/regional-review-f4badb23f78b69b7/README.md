# Southern Africa batch 2 evidence packet (#412)

This packet reviews the issue-owned subset of Mozambique and Zambia ADM2 records: 121 Mozambique records and 102 Zambia records, grouped under 16 scoped province parents. It is a review-only evidence packet. It makes no production geography edits and does not certify a whole country or region.

## Reproduce

From the repository root, run:

```sh
python3 data/regional-review/regional-review-f4badb23f78b69b7/reproduce.py
```

The script checks that all 223 frozen issue IDs are unique, each joins to exactly one retained pinned ADM2 source feature, and each normalized name agrees. It rewrites `location-assessments.csv`. That proves an identity/name crosswalk only; it does not test territorial meaning, polygon validity, boundaries, completeness, licensing, or legal parentage.

## Packet contents

- `scope.json`: frozen issue scope, exact IDs, owned path, and source IDs.
- `location-assessments.csv`: one transparent assessment row per scoped ID, including Atlas and source polygon-part/vertex/ring summaries and unresolved parent/boundary status.
- `province-review.csv`: row counts for all 16 fully scoped province parents, issue-declared parent totals, and the 2022 Zambia source's parent-field conflicts grouped by Atlas parent.
- `findings.md`: source comparison, substantive findings, uncertainty, and engineering handoffs.
- `SOURCES.md`: source versions, retrieval dates, license treatment, hashes, and restoration instructions.
- `source-inventory.json`: machine-readable exact source hashes, lengths, vintages, retrievals, licenses, and restoration pointers.
- `source/reproducibility.json`: two-run output hashes and exact evaluation base commit.
- `reproduce.py`: deterministic scoped source join and summary generator.
- `source/`: lawful pinned-source originals, source metadata, claim receipt, and issue snapshots. The exclusive-ownership INE live service geometry was not retained.

Polygon part, vertex, and ring counts are structural descriptions. They do not certify valid topology or a correct real-world boundary.

## Phase 2: province and regional-risk review

`phase-2/province-assessments.csv` individually assesses all 16 province groups in the exact issue scope. It records the scope-member names, source-vintage and role findings, source-parent roster evidence where available, classification, and explicit limitations. `phase-2/zambia-province-roster.csv` gives the full 2022 official source roster by province, including Eastern as source context outside this issue's scope. `phase-2/zambia-source-area-screen.csv` ranks the official layer's supplied `Area_km` values by province as a screening lead, not an independent area measurement. `phase-2/geographic-risk-review.csv` addresses each regional-risk category in the issue acceptance. The exact source hashes, restoration links and access limits are in `phase-2/source-inventory.json` and `phase-2/source/reference-records.json`. Unresolved full-Mozambique roster/license work is tracked in #1042, disputed Zambia parentage in #1043, and OSG/GRID3 `FEATURE_TY` / `Area_km` interpretation in #1048.

Run from the repository root:

```sh
python3 data/regional-review/regional-review-f4badb23f78b69b7/phase-2/reproduce.py
```

This reproduces the province and risk tables, confirms the full 116-name Zambia crosswalk and checks that #411's 38 Mozambique IDs and #412's 121 Mozambique IDs are disjoint and reconcile to the 159-ID frozen area scope. It does not validate geometric correctness, current Mozambique completeness, or legal parentage.

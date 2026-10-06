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

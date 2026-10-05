# USA ADM2 source-lineage packet (#981)

This packet resolves the checksum lineage for the exact 279 `gb:USA:ADM2:*` subjects from #428. It retains the immutable GeoBoundaries 2018 full and simplified source objects, their LFS pointers, metadata, API retrieval records, an input hash inventory, a reproducible audit, and one row per subject in `findings/subject-crosswalk.jsonl`.

Run the reproducible audit from the repository root:

```sh
python3 data/regional-review/usa-adm2-lineage-428/scripts/audit_lineage.py
node scripts/evidence-quality.mjs data/regional-review/usa-adm2-lineage-428/evidence-quality.json
```

The audit intentionally does not modify shared geography or the administrative-source catalog. See `findings.md` for source interpretation, uncertainty, and the engineering handoff. The evidence manifest records exact baseline pins, source/output hashes, issue scope, and limitations.

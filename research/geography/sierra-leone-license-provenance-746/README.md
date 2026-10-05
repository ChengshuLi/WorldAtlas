# Sierra Leone license provenance supersession

This additive receipt corrects one inherited metadata field in the original #479 / PR #746 assessment. Its builder assigned Togo's final metadata license to every assessed member after iterating over both countries. The original source inventory and README distinguish the country licenses; the 12 Sierra Leone assessment rows do not.

The immutable assessment scope contains 12 Sierra Leone ADM2 IDs and 37 Togo ADM2 context IDs. The receipt identifies each Sierra Leone row by its exact ID, name, direct parent, and parent chain. It records both the original assessment value and the Sierra Leone metadata-declared value. All 37 Togo context rows retain their matching Togo value. No identifiers, names, parents, geometries, counts, source archives, assessment files, or earlier evidence are edited.

## Source records and limits

The pinned geoBoundaries metadata snapshots were retrieved into the original packet on 2026-10-04. Both declare represented year 2017. Sierra Leone metadata names Government of Sierra Leone and OCHA ROWCA as source, calls ADM2 units “Districts,” and declares Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO); its detailed-license field is `nan`, and its license-source field points to the HDX Sierra Leone boundaries dataset. Togo metadata names OpenStreetMap and Wambacher, calls ADM2 units “Prefectures,” and declares Creative Commons Attribution-ShareAlike 2.0.

The source bytes are retained in the original packet, not recopied here. Compressed and restored byte counts and SHA-256 hashes are in `license-provenance.json`; acquisition receipt hashes and the exact Git restoration paths are pinned in `issue-contract.json`. Restore either snapshot with `git show f92b1774aedcaaaf72ac0fe4cc45857dd641d7d1:<recorded metadata path>` and verify its recorded digest before use. The packet reports catalog metadata declarations; it does not adjudicate legal licensing, establish completeness or statutory authority, or approve geography.

## Reproduction

From the repository root:

```sh
python research/geography/sierra-leone-license-provenance-746/reproduce.py
python research/geography/sierra-leone-license-provenance-746/verify.py
node scripts/evidence-quality.mjs research/geography/sierra-leone-license-provenance-746/evidence-quality.json
```

The verifier runs the generator from two separate temporary working directories, requires byte-identical outputs, checks all 12 SLE and 37 TGO rows, verifies identity and direct-parent agreement with the pinned canonical partition, and exercises country-metadata and injected-license negative controls.

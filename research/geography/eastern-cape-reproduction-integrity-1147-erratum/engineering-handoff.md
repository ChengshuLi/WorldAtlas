# Engineering handoff: Eastern Cape measurement producer

**Date:** 2026-10-07 America/Los_Angeles  
**Origin:** geography work item #1371; exact inputs and reproduction receipts are in this packet.  
**Authority:** evidence proposal only; this handoff is not implementation, geographic approval, or publication approval.

## Proposed correction

The retained `data/regional-review/eastern-cape-source-restoration-435/measure_boundary_vintages.py` currently reads `CAT_C` for its 2021 district field. The authenticated 2021 MDB schema supplies nonempty district code/name fields `DISTRICT` and `DISTRICT_N`. Derive `district_2021` and `district_name_2021` from those two fields and retain the full 33-feature contextual output. Two actual-entrypoint runs in this packet show that this field correction preserves all 231 numeric measures exactly.

Before adopting a producer change, preserve and validate the separately recorded output path, authenticate all four complete consumed MDB attribute/geometry responses and all imported measurement code before calculations, reject duplicate/missing/swapped/ambiguous records before joining, and reserve an exclusive fresh output vintage before writes. The complete adverse controls and immutable source bytes are under `vintages/` and in `evidence-quality.json`.

## Separate source/research work still unresolved

- Obtain and inspect the four cited 2024 Gazette/name response bodies, the IEC Section 23 materiality opinion and any corresponding MEC effective-date notice. The original response bodies were not restored here.
- Establish an authoritative bridge between post-2023 MDB decisions and a legally effective current boundary vintage. The MDB 2026 source is prospective as retrieved.
- Establish detached-territory completeness and the legal name/effective date for Dr AB Xuma/Engcobo before any name or boundary edit.

The retained comparison is a reproduction-integrity check. It neither selects a correct municipal footprint nor authorizes changing shared geography or production data.

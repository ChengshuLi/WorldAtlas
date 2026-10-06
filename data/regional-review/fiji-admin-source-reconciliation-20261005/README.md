# Fiji ADM2 source and semantic reconciliation (#910)

Research packet retrieved 2026-10-06 on GEO 0's confirmed claim. Baseline: `fc328993bb8c0690b3b4687d193c7f0887bd5b17`. Scope is exactly the 15 issue-declared Fiji ADM2 IDs; this packet makes no core geography, release, regional approval, or publication change.

## Source chain and findings

The pinned geoBoundaries release is commit `9469f09592ced973a3448cf66b6100b741b64c0d`; the GeoJSON is a real 1,357,011-byte LFS object whose content SHA-256 is `a9cd94789cb5eb66cfbcbaf32a21bcbceba16b9a76adacba9ac675b950ca1ccd`. Its Git blob is a 132-byte LFS pointer with the same OID. The full feature layer is retained under CC BY 4.0 with required attribution; metadata and citation/use instructions are retained beside it. The geoBoundaries metadata links to Pacific Data's 2007 Fiji census administrative boundary record. In contrast, the geoBoundaries current API labels represented year 2020, while source update/build timestamps are 2023. The pinned release metadata's `boundaryYearRepresented` and `sha256` are null; the current API also has null SHA. Atlas's pinned registry SHA `0339f90794264719b98c93a9a7c2d71fdb473c0a2f9c1e9b74ecd98a67ddb93f` does not equal the raw content SHA, and its digest recipe is unresolved. Neither year label nor digest is silently preferred.

Fiji Bureau of Statistics materials confirm census reporting context, including 2017 census reporting for the province-named units. That is not a legal boundary or administrative-status determination. Fiji Parliament's 2024 Hansard describes Rotuma as a dependency administratively incorporated in Fiji, with local-government autonomy under the Rotuma Act. The official UN SALB catalog identifies a validated national-authority dataset, but its page returned 403 here; underlying boundaries were unavailable and were not compared. Small-island completeness remains unverified. Source URLs, lawful retained bytes, hashes, restoration instructions, and license limits are in `source-provenance.json`. Restricted/unknown-reuse official PDFs were not retained.

## Subject-level crosswalk

All 15 IDs have a unique exact match by native `shapeID` suffix and exact name in the pinned 15-feature source; the reproduction output records each result and current Atlas parent. Exact current legal edge authority and completeness remain unestablished for each.

| Subject ID | Source name | Atlas parent | Finding |
|---|---|---|---|
| `gb:FJI:ADM2:14151628B20319301670654` | Lomaiviti | Eastern | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B28251361437248` | Namosi | Central | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B39642918357252` | Rewa | Central | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B42533076410957` | Macuata | Northern | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B48978228339800` | Tailevu | Central | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B53541640625043` | Ra | Western | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B53702400461405` | Nadroga-Navosa | Western | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B59272471160482` | Bua | Northern | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B61046117406534` | Kadavu | Eastern | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B68154180840071` | Serua | Central | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B71764118664060` | Rotuma | Rotuma | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B80423492752803` | Lau | Eastern | exact source ID/name; material source-to-Atlas discrepancy; authority and source-vintage disagreement unresolved |
| `gb:FJI:ADM2:14151628B8492423103487` | Naitasiri | Central | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B95966095088914` | Cakaudrove | Northern | exact source ID/name; exact current official boundary and small-island completeness not established |
| `gb:FJI:ADM2:14151628B98370545668292` | Ba | Western | exact source ID/name; exact current official boundary and small-island completeness not established |

## Lau comparison

Using shared `worldatlas-evidence-geometry-v1` on EPSG:4326 coordinates in longitude-latitude order, WGS84 ellipsoidal area integration gives intersection `400229314.423` m², union `520593104.441` m², Jaccard `0.768794882237416`, and symmetric difference `120.363790018752` km². Two independent runs are byte-identical. This confirms material outline divergence only; resemblance does not decide which outline is legally or geographically correct. The 2007/2020 source vintage ambiguity remains a blocker to source adjudication.

## Engineering handoff: Rotuma parent/category

For stable subject `gb:FJI:ADM2:14151628B71764118664060` (Rotuma), the baseline currently parents it to `framework:province:rotuma` / “Rotuma.” The official Hansard calls Rotuma a dependency under the Rotuma Act; census reporting groups it with province rows. Please determine the intended ontology and hierarchy representation for a dependency with local-government autonomy, assess any consumers of the current province parent, and propose a reviewed hierarchy/parent correction in a separately scoped engineering/geography change. This packet does not modify the parent or certify a replacement.

## Reproduction and limits

Run from repository root after managed workspace checks: `python3 data/regional-review/fiji-admin-source-reconciliation-20261005/reproduce.py --output data/regional-review/fiji-admin-source-reconciliation-20261005/run-one/reproduction.json`; repeat to `data/regional-review/fiji-admin-source-reconciliation-20261005/run-two/reproduction.json`. The script verifies issue scope, active claim identity, four exact issue pins plus hierarchy at immutable baseline, all 15 source/baseline mappings, controls, and Lau geometry metrics. Positive/negative control outcomes and run-byte comparison are retained. The evidence-quality manifest verifies baseline/source/output bytes and binds metrics.

Unresolved: legal edge authority and small-island completeness; source-year semantics; old registry hash recipe; SALB polygon comparison due 403; Rotuma hierarchy implementation. Research is complete for the bounded evidence handoff, but geography is unapproved and implementation is not proposed here.

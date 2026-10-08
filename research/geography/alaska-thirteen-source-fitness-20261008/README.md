# Alaska 13 component source fitness

This packet assesses the exact 13 land-plus-unique-route components in family `gap-source-batch:9a8d66e4d47f5883620328f9`, selected from the accepted #1202 funnel. The other 982 members of the 995-component family, all 17 positive-length neighbors, and all complete contacts remain read-only context in `sources/complete-native-family-record.jsonl`.

## Findings

All 13 routed geoBoundaries subjects resolve one-to-one to actual current Atlas geography features. Each target feature records `source_id=gb:USA:ADM2`, the same `original_id` as the routed source subject, `reference_year=2018`, `source_role=Counties`, `administrative_level=ADM2`, and parent `framework:province:alaska:4057e2fddbc5`. This establishes the recorded native target identity and source role: each selected subject is part of a named 2018 Alaska county/county-equivalent target. Seven target records serve the 13 components:

| Component prefix | Native Atlas target |
| --- | --- |
| `073d9a81` | Aleutians East |
| `4d36c81f` | Valdez-Cordova |
| `5874689a` | Kodiak Island |
| `66e4f6c1` | Kenai Peninsula |
| `70174bff` | Valdez-Cordova |
| `777e7bc9` | Kodiak Island |
| `8435dc6d` | Valdez-Cordova |
| `8fb2ed93` | Aleutians East |
| `9f130f02` | Aleutians East |
| `cffd5f51` | Kusilvak |
| `d688afd3` | Kodiak Island |
| `e76fd386` | Hoonah-Angoon |
| `ef7383db` | Prince of Wales-Hyder |

The source-subject identity and source role are a **fit for the recorded county target** for all 13 candidates. Exact geometry applicability is **unresolved**. The retained source product is the geoBoundaries simplified GeoJSON at release tag `9469f09`; each current Atlas target metadata URL points to the non-simplified GeoJSON at the same tag. The retained source-feature geometry hash and the Atlas target geometry hash differ for all seven subjects, and the routed source-geometry hashes differ from the retained simplified feature geometry hashes. This packet does not run GIS or infer coordinate equivalence. It therefore does not claim that one variant can replace or repair the other, or that the 13 candidate fragments are a valid boundary edit.

All 13 physical-comparison rows report `unknown-source-fitness-and-observation-date` and unapproved physical authority. The retained query relations show one level-1 GSHHG record covering each candidate, supporting only source-relative coarse land support. The 11 referenced native metadata records identify GSHHG 2.3.7 (release 2017-06-15); observation dates are heterogeneous and per-feature dates are not established. This does not negate the recorded county-target identity. It leaves the source’s use for candidate-specific boundary reconstruction unresolved where exact geometry, no-loss and shoreline-registration predicates have not been measured. No geometry measurement, historical-cause finding, repair proposal or repair authority is included.

## Candidate-level results

`sources/candidate-components.geojson` retains the exact 13 original component features from the pinned 95,173-component input; their canonical feature and geometry hashes match the funnel's current-feature and current-geometry hashes 13/13. `sources/candidate-source-screen.json` contains the exact full component IDs, current feature/geometry hashes, source route rows, original source offsets, original component records, exact target feature IDs and hashes, physical query rows and their hash bindings, all retained source relations, per-candidate decision axes, and missing facts. It preserves every query relation, including disjoint/neighbor contacts. `sources/physical-query-rows.jsonl` preserves the canonical whole physical rows; `sources/gshhg-native-query-records.json` preserves all 11 referenced native metadata rows.

The main conclusions are:

- **13/13:** source-subject identity and `Counties`/`ADM2` source role fit the corresponding recorded Atlas target.
- **13/13:** exact source-geometry variant applicability to the target geometry remains unresolved.
- **13/13:** coarse GSHHG land support is source-relative only; per-feature observation date and repair authority remain unapproved/unknown.

The source product's derivative use terms and underlying source attribution are retained in `sources/geoBoundaries-derivative-use-terms.txt` and `sources/usa-adm2-attribution.json`. The evidence preserves those as source claims, not a new legal opinion.

## Reproduction and scope

Run `run_reproducibility.py` with the repository's Python runtime from the repository root. It runs `build_evidence.py` twice against the pinned baseline in separate fresh directories, retains the first run’s independently recorded input digest, output inventory digest, and timestamp, keeps the second output under `sources/`, and verifies matching inputs and output inventories across two separately timestamped executions. The first run’s regenerated scratch files are discarded after the durable receipts are written. The second run's bounded phases and output hashes are recorded in `sources/build-receipt.json`. It performs no GIS operation, source acquisition, geometry proposal, production edit, or database/provider/publisher work. The first published exploratory draft is retained under `exploratory-v1-*` as historical context; it is superseded and not used by the final findings.

The canonical task is [#1488](https://github.com/ChengshuLi/WorldAtlas/issues/1488), claimed on branch `geography/alaska-thirteen-source-fitness-20261008-r1`. This packet does not close #486 or resolve the remaining family members.

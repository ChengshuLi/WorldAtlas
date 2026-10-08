# Alaska 13 component source fitness

This packet assesses the exact 13 land-plus-unique-route components in family `gap-source-batch:9a8d66e4d47f5883620328f9`, selected from the accepted #1202 funnel. The other 982 members of the 995-component family, all 17 positive-length neighbors, and all complete contacts remain read-only context in `sources/complete-native-family-record.jsonl`.

## Findings

All 13 routed geoBoundaries subjects resolve one-to-one to actual current Atlas geography features. Each target feature records `source_id=gb:USA:ADM2`, the same `original_id` as the routed source subject, `reference_year=2018`, and parent `framework:province:alaska:4057e2fddbc5`. This is direct evidence that the selected source subject belongs to a named 2018 Alaska county/county-equivalent target. Seven target records serve the 13 components:

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

The source-subject identity is a **fit for the recorded county target**. Exact geometry applicability is **unresolved**. The retained source product is the geoBoundaries simplified GeoJSON at release tag `9469f09`; each current Atlas target metadata URL points to the non-simplified GeoJSON at the same tag. The retained source-feature geometry hash and the Atlas target geometry hash differ for all seven subjects, and the routed source-geometry hashes differ from the retained simplified feature geometry hashes. This packet does not run GIS or infer coordinate equivalence. It therefore does not claim that one variant can replace or repair the other, or that the 13 candidate fragments are a valid boundary edit.

For a separate ecological, shoreline, or other physical-region boundary, the administrative county source is **not fit as that boundary source**. The family record only gives `inside-unassigned-native-cell:reference-shore-context`; it does not name a distinct physical-region target. The exact missing fact is a target-specific native source identity and its authoritative geometry/vintage, plus the transformation that binds the retained geometry variant to the intended target.

No applicable native physical-region target source is retained in the references examined for this batch. The retained GSHHG records provide coarse source-relative land support, not a named target boundary or repair authority. The assessment therefore records a no-fit for using the county source as physical-region authority and leaves the intended physical target unresolved.

All 13 physical-comparison rows report `unknown-source-fitness-and-observation-date` and unapproved physical authority. The retained query relations show one level-1 GSHHG record covering each candidate, supporting only source-relative coarse land support. The 11 referenced native metadata records identify GSHHG 2.3.7 (release 2017-06-15); observation dates are heterogeneous and per-feature dates are not established. No shoreline accuracy or historical cause is inferred, and no repair authority is proposed.

## Candidate-level results

`sources/candidate-components.geojson` retains the exact 13 original component features from the pinned 95,173-component input; their canonical feature and geometry hashes match the funnel's current-feature and current-geometry hashes 13/13. `sources/candidate-source-screen.json` contains the exact full component IDs, current feature/geometry hashes, source route rows, original source offsets, original component records, exact target feature IDs and hashes, physical query rows and their hash bindings, all retained source relations, per-candidate decision axes, and missing facts. It preserves every query relation, including disjoint/neighbor contacts. `sources/physical-query-rows.jsonl` preserves the canonical whole physical rows; `sources/gshhg-native-query-records.json` preserves all 11 referenced native metadata rows.

The main conclusions are:

- **13/13:** source-subject identity fits the corresponding recorded 2018 county/county-equivalent target.
- **13/13:** exact source-geometry variant applicability to the target geometry remains unresolved.
- **13/13:** coarse GSHHG land support is source-relative only; physical authority and observation date remain unapproved/unknown.
- **13/13:** an ecological or other distinct physical-region target is not established by this administrative source.

The source product's derivative use terms and underlying source attribution are retained in `sources/geoBoundaries-derivative-use-terms.txt` and `sources/usa-adm2-attribution.json`. The evidence preserves those as source claims, not a new legal opinion.

## Reproduction and scope

Run `build_evidence.py` with the repository's Python runtime from the repository root. It reads immutable Git blobs and retained payloads, then creates a fresh `sources/` output vintage and a byte-readback receipt. Its bounded phases and every output hash are recorded in `sources/build-receipt.json`. It performs no GIS operation, source acquisition, geometry proposal, production edit, or database/provider/publisher work.

The canonical task is [#1488](https://github.com/ChengshuLi/WorldAtlas/issues/1488), claimed on branch `geography/alaska-thirteen-source-fitness-20261008-r1`. This packet does not close #486 or resolve the remaining family members.

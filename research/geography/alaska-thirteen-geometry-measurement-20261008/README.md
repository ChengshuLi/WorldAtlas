# Alaska 13 component geometry measurement

This packet measures exactly the 13 physical-component IDs assigned in issue #1508. It retains the complete 995-member family as read-only context, all seven Atlas targets, 25 original physical query relations, 11 original GSHHG records, 17 positive-length Atlas neighbors, and all 13 original detector contact geometries.

## Result

No individual or tested same-county batch satisfies the full exact geometry gate. The single-case strict no-loss table and all nine deterministic two/three-component batch results are in [truth-table.json](vintages/acceptance-receipts-20261008/truth-table.json); none creates a new positive-area overlap with an actual Atlas neighbor. The candidate proposal and gain GeoJSON files are valid empty FeatureCollections because no candidate qualified. Nothing in this packet approves a repair or changes Atlas production data.

The seven selected simplified county geometries and the seven non-simplified geometries from geoBoundaries tag `9469f09` were compared directly. Candidate-specific predicates, projected/raw intersection areas, coverage, and uncovered areas agree across the two variants for all 13 candidates. The full and simplified county polygons are not themselves geometrically identical, and neither product resolves which exact boundary version is applicable to the recorded Atlas target. Real-world boundary authority and the intended vintage remain unresolved.

The 11 GSHHG level-1 records preserve their original headers, offsets, parent/container fields, flags, hashes, and complete native coordinates. They contain 895,990 points (7,167,920 coordinate bytes). These are coarse source-relative land-support observations; per-feature observation date, precision, shoreline registration, and repair authority remain unknown. Original license wording conflicts are retained without a new legal conclusion.

## Numeric ledger

The following table is rendered from `metric-values.json`; each row is also bound to the same scalar in the evidence manifest.

| Measure | Value | Unit |
|---|---:|---|
| atlas_target_count | 7 | features |
| candidate_pair_count | 78 | pairs |
| collective_union_trial_count | 9 | trials |
| component_count | 13 | components |
| family_member_count | 995 | members |
| full_source_feature_count | 3233 | features |
| native_coordinate_bytes | 7167920 | bytes |
| native_gshhg_record_count | 11 | records |
| native_linked_support_count | 13 | cases |
| native_point_count | 895990 | points |
| native_source_pair_count | 143 | pairs |
| negative_control_count | 4 | controls |
| neighbor_feature_count | 17 | features |
| new_positive_area_neighbor_overlap_count | 0 | overlaps |
| original_neighbor_contact_match_count | 13 | cases |
| original_physical_relation_match_count | 13 | cases |
| output_bytes_per_run | 735528 | bytes |
| physical_relation_count | 25 | relations |
| positive_control_count | 2 | controls |
| proposal_feature_count | 0 | features |
| qualifying_batch_count | 0 | batches |
| qualifying_single_case_count | 0 | cases |
| reproducible_run_count | 2 | runs |
| simplified_target_count | 7 | features |
| single_case_gate_count | 13 | cases |
| source_parent_support_count | 11 | cases |
| variant_candidate_agreement_count | 13 | cases |

## Method and retention

Inputs and execution code are byte-pinned in `evidence-quality.json`. The producer compares WGS84 longitude/latitude GeoJSON without pre-transforming coordinates; area is reported in raw square degrees as a coordinate-plane diagnostic and in EPSG:3338 Alaska Albers Equal Area square metres. Exact topological coverage and zero-area differences use no tolerance. Invalid source geometries are reported and never repaired, buffered, snapped, or silently discarded.

Resource admission was completed before the bounded producer runs. `phase-admission.json` records the free-space/process scan and 6,680,375-byte admission headroom under the 256 MiB phase cap. Runs 13 and 14 exited naturally within the 900-second/768 MiB ceilings; their actual times, peak sampled RSS, complete output inventories, and hashes are in `execution/` and [reproducibility.json](vintages/acceptance-receipts-20261008/reproducibility.json). All four scientific output files are byte-identical across fresh run destinations.

## Reproduction

From the repository root, use the retained Python 3.12.14 runtime and invoke `measurement_driver.py run-thirteen` or `measurement_driver.py run-fourteen` with a fresh output destination. The exact completed commands and process receipts are retained in the packet. To rebuild the truth table, controls, reproducibility receipt, and numeric ledger without rerunning geometry, run `python3.12 -B research/geography/alaska-thirteen-geometry-measurement-20261008/build_acceptance_packet.py`.

Research is complete for the bounded measurements. Implementation is not proposed and geographic approval is unapproved. This packet does not determine historical cause, political affiliation, ownership, rights, publication permission, current physical status, or real-world boundary accuracy.

# Namibia–Angola reproduction and operand identity erratum (#1437)

Recorded 2026-10-07 (America/Los_Angeles). This additive packet preserves the original #1268 source files, reports, IDs and findings. It corrects reproduction-integrity and operand-description claims only; it does not certify the geography of the region.

## Scope and findings

The pinned inputs contain 21 unique physical-component candidate IDs and 10 unique source-contact ADM2 features (the exact contact subject roster is in `source-context-review.json`). Their Cartesian comparison has 210 unique pairs. These are investigation candidates, not Atlas locations or territorial assignments.

**The original commands are historical, unsafe reproductions and are superseded by the two commands below. Do not use them for a new reproduction.** Their exact preserved source blobs are [`reproduce_source_geometry.py` at `de506f5`](https://github.com/ChengshuLi/WorldAtlas/blob/de506f51100568e150e51f2926a5259b71e55272/research/geography/gap-source-namibia-angola-20261006/reproduce_source_geometry.py) and [`reproduce_full_product_comparison.py` at `de506f5`](https://github.com/ChengshuLi/WorldAtlas/blob/de506f51100568e150e51f2926a5259b71e55272/research/geography/gap-source-namibia-angola-20261006/reproduce_full_product_comparison.py). Their original outputs remain unchanged: [source-geometry-comparison.json](https://github.com/ChengshuLi/WorldAtlas/blob/de506f51100568e150e51f2926a5259b71e55272/research/geography/gap-source-namibia-angola-20261006/source-geometry-comparison.json) and [full-product-comparison.json](https://github.com/ChengshuLi/WorldAtlas/blob/de506f51100568e150e51f2926a5259b71e55272/research/geography/gap-source-namibia-angola-20261006/full-product-comparison.json). Their original file hashes and byte counts are retained in `source-pin-inventory.json` and `legacy-reproduction-audit.json`. The old full-product entry point accepts same-length duplicate candidate or contact lists; the duplicate-candidate control produced 210 rows representing only 20 distinct candidate IDs. Its standalone inventory check is therefore incomplete. The old source-geometry entry point rejects the recorded duplicate/missing fixtures, but this does not make the old full-product command safe. No legacy file or output has been rewritten.

The historical report README describes the pair loop as using full source-contact geometries. Inspection of the pinned entry point shows the loop uses the consumed `source-contact-features.geojson` geometries. Full products are separately used for country-wide scans and same-ID comparisons. All 10 consumed contacts differ topologically from their same-release full-product feature; 35 of 210 candidate/contact intersection areas differ when substituting the full geometries. The original successor matrix keeps those operands separate. The two supported successors below now independently authenticate their committed code, complete issue pin inventory, materialized source inputs, exact candidate/contact identities and complete product rosters at their own entry points. They emit distinct products: the source-geometry successor records all 210 candidate-by-consumed-contact rows; the full-product successor records all 5,670 candidate-by-full-product feature rows, including disjoint rows. Both separately identify the consumed and same-release full contact operand. Each rejects changed source/code bytes, incomplete or duplicate inventories, invalid/empty geometries, unsafe run names, symlinked output roots, and existing destinations before output publication. These are scoped controls, not a general fuzz campaign.

Both unchanged historical entry points were executed twice from issue-pinned Git blobs. All four outputs match their preserved historical reports byte-for-byte. The earlier authenticated matrix was run twice into fresh output directories; both outputs are 101,810 bytes with SHA-256 `af573ff25ba961ea574ed08214ab9befbe95626d6b78977cc329c914222fc5de`. After binding the amended issue body, each standalone successor was run twice from code commit `016dc563e6d6e0d6eb1ac3542c6cc93cd749da49`. Both source reports are 74,159 bytes with SHA-256 `15789ad78c5d095d0a165f7756c934606e77fa94a0f998aaf8f7063f18cec3b6`; both full-product reports are 1,461,226 bytes with SHA-256 `19fa76a5c1e8de6ff74af2328f25b15bf9303afe191ece8a95ece938306b90fe`. Each pair is byte-identical.

## Provenance and reproduction

`source-pin-inventory.json` preserves all 46 issue-pinned commit/path/size/hash records (45 unique paths). `legacy-reproduction-audit.json` is the authoritative record for the unchanged scripts, their outputs, source pins, fixture controls, tool versions and preserved legacy destinations. `attempt-history.json` separates the corrected run from earlier harness attempts; the flawed artifacts remain under `failed-attempts/` and are not acceptance evidence.

Each successor verifies all 46 issue-pinned Git blobs against the retained inventory, compares the materialized candidate/contact/full-product input bytes with those pinned blobs, and checks all three executed code files against their immutable `HEAD` blobs. It requires all 21 bound candidate IDs, the exact 10 subject IDs, complete unique 109-feature NAM and 161-feature AGO products, and (depending on command) complete unique rows for each expected pair set. It does not depend on a prior optional validator. Output is admitted only as a newly created directory under `vintages/`.

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_source_geometry_successor.py successor-source-one-20261008
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_full_product_successor.py successor-full-one-20261008

For the negative-control suite and row-by-row comparison with the retained historical full-product report, run:

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/verify_successor_controls.py
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/verify_successor_results.py
```

## Acceptance reconciliation (2026-10-07, America/Los_Angeles)

| Criterion | Evidence and status |
| --- | --- |
| Preserve all original source, code, report, identities and earlier research | Preserved. The legacy code and report hashes remain fixed in the issue pin inventory; changed paths are confined to this erratum directory. |
| Two supported commands independently authenticate complete code, inputs, identities and operands | Implemented. Each checks all pinned blobs, the five materialized source operands and all three committed runtime files from `HEAD`; exact 21/10 inventories and full 109/161 source products are required at each invocation. |
| Exact complete pair rows | Source successor: 210 unique candidate/consumed-contact rows. Full-product successor: 5,670 unique candidate/full-product feature rows, including disjoint pairs. |
| Correct consumed-versus-full operand meaning | Documented. Consumed contacts are the retained NAM-2007 / AGO-2018 geometry operands. Same-release full products are separate; the 10 contacts differ topologically, and the preserved comparison found area differences for 35 of 210 pairs. |
| Two genuine fresh runs and baseline agreement | Passed. Each command was run twice into separate new directories; byte hashes match between repetitions. An independent identity join compared all 210 and 5,670 row values to the preserved historical full-product report; all matched. See `vintages/successor-baseline-final-20261008/independent-baseline-comparison.json`. |
| Duplicate/omission, geometry, source/code drift and unsafe-output controls | Passed for both actual entry points: 28/28 failures, with no valid output published and all temporarily altered files restored byte-for-byte. See `vintages/standalone-controls-rebound-20261008/control-results.json`. |
| Independent exact-head review | Pending. Do not close #1437 or treat this research packet as region-complete until a distinct reviewer tests both documented entry points and accepts the current PR head. |
| Territorial/source completeness, current authority, parent assignment, neighboring granularity, legal meaning or physical classification | Not established. These remain explicit limits and do not become positive findings from reproduction success. |
```

The recorded environment is Python 3.12.14, Shapely 2.1.2, and GEOS 3.13.x. Pair intersection areas are planar square degrees in the source coordinate space; they are reproducibility metrics, not ground areas. Historical and new report files are retained without overwriting original destinations.

## Source meaning and limits

The retained source metadata describes geoBoundaries release commit `9469f09592ced973a3448cf66b6100b741b64c0d`, ADM2. It records Namibia as represented by 2007 source data (109 ADM2 features) and Angola as represented by 2018 source data (161 ADM2 features), with metadata update/build dates 2023-01-19 / 2023-12-12. The Namibia metadata names Namibia Statistics Agency / Stanford Digital Repository and records “Public Domain”; the Angola metadata names GADM and INE / HDX and records CC BY 3.0 IGO. These are transcriptions of pinned metadata, not independent license or legal-authority determinations.

The contact features have source group, source ID and name fields but no explicit parent ADM1 identifiers. The source grouping does not establish territorial attribution. This erratum does not establish current boundaries, completeness of either national source, parent relationships, boundary authority, legal meaning, water status, or physical-component assignments. Neighboring administrative granularity was not independently assessed. These questions remain open for their existing research owners; engineering follow-up should make complete identity/source/code pins mandatory before either standalone producer publishes output.

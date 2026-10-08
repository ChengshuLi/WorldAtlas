# Namibia–Angola reproduction and operand identity erratum (#1437)

Recorded 2026-10-07 (America/Los_Angeles). This additive packet preserves the original #1268 source files, reports, IDs and findings. It corrects reproduction-integrity and operand-description claims only; it does not certify the geography of the region.

## Scope and findings

The pinned inputs contain 21 unique physical-component candidate IDs and 10 unique source-contact ADM2 features (the exact contact subject roster is in `source-context-review.json`). Their Cartesian comparison has 210 unique pairs. These are investigation candidates, not Atlas locations or territorial assignments.

The historical `reproduce_full_product_comparison.py` is count-based for its standalone input inventory. It accepts a same-length duplicate candidate or contact list. In the duplicate candidate control, it emits 210 pair rows while representing only 20 distinct candidate IDs. The separate source-geometry entry point rejects the duplicates and missing-row fixtures through exact membership checks. Therefore the full-product command cannot be treated as authenticating complete inventories on its own.

The historical report README describes the pair loop as using full source-contact geometries. Inspection of the pinned entry point shows the loop uses the consumed `source-contact-features.geojson` geometries. Full products are separately used for country-wide scans and same-ID comparisons. All 10 consumed contacts differ topologically from their same-release full-product feature; 35 of 210 candidate/contact intersection areas differ when substituting the full geometries. The two operands are reported separately by `reproduce_authenticated_geometry_matrix.py`. The successor rejects missing or duplicate IDs, a changed issue or pin inventory, incomplete full products, invalid or empty geometries, unsafe run names, symlinked output roots, and existing output directories before publishing a report. These are scoped negative controls, not a general fuzz campaign.

Both unchanged historical entry points were executed twice from issue-pinned Git blobs. All four outputs match their preserved historical reports byte-for-byte. The new authenticated successor was run twice into fresh output directories; both outputs are 101,810 bytes with SHA-256 `af573ff25ba961ea574ed08214ab9befbe95626d6b78977cc329c914222fc5de`.

## Provenance and reproduction

`source-pin-inventory.json` preserves all 46 issue-pinned commit/path/size/hash records (45 unique paths). `legacy-reproduction-audit.json` is the authoritative record for the unchanged scripts, their outputs, source pins, fixture controls, tool versions and preserved legacy destinations. `attempt-history.json` separates the corrected run from earlier harness attempts; the flawed artifacts remain under `failed-attempts/` and are not acceptance evidence.

The successor authenticates its issue snapshot and pin inventory against fixed SHA-256 values, checks each pinned blob from Git, rejects incomplete or duplicate candidate/contact/full-product identities, verifies the exact 10-contact membership, and writes only into a new directory under `vintages/`.

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_authenticated_geometry_matrix.py successor-final-one-20261007
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/gap-source-namibia-angola-reproduction-erratum/reproduce_authenticated_geometry_matrix.py successor-final-two-20261007
```

The recorded environment is Python 3.12.14, Shapely 2.1.2, and GEOS 3.13.x. Pair intersection areas are planar square degrees in the source coordinate space; they are reproducibility metrics, not ground areas. Historical and new report files are retained without overwriting original destinations.

## Source meaning and limits

The retained source metadata describes geoBoundaries release commit `9469f09592ced973a3448cf66b6100b741b64c0d`, ADM2. It records Namibia as represented by 2007 source data (109 ADM2 features) and Angola as represented by 2018 source data (161 ADM2 features), with metadata update/build dates 2023-01-19 / 2023-12-12. The Namibia metadata names Namibia Statistics Agency / Stanford Digital Repository and records “Public Domain”; the Angola metadata names GADM and INE / HDX and records CC BY 3.0 IGO. These are transcriptions of pinned metadata, not independent license or legal-authority determinations.

The contact features have source group, source ID and name fields but no explicit parent ADM1 identifiers. The source grouping does not establish territorial attribution. This erratum does not establish current boundaries, completeness of either national source, parent relationships, boundary authority, legal meaning, water status, or physical-component assignments. Neighboring administrative granularity was not independently assessed. These questions remain open for their existing research owners; engineering follow-up should make complete identity/source/code pins mandatory before either standalone producer publishes output.

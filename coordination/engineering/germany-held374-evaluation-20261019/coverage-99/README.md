# DEU ADM3 unsupported coverage keys: evidence-only packet

This packet expands the exact 99 tuples retained in `held-original.json` under `unsupported_coverage_cells`. It is pinned to accepted main `77609a1f159bfee954e52d48a883c5fe3e4b59f5` and records all four source blob OIDs in `coverage-99.json`.

## Result

- 99 unique cell tuples across nine owners, expanded from original half-open row runs with source row/run indexes retained.
- The source membership crosswalk has 100 atoms overall and 18 exact rows across these nine owners: two source atom IDs for each of nine multipart targets.
- The source evidence contains one `mapped_land_support` record per owner. All 99 held coordinates occur in those target-level mapped support rows.
- The whole-target physical file has a result for each of the 18 source atoms. Its relations and physical issue flags are target-level only.
- No evidence here establishes complete-cell coverage for any held key. All 99 remain held; accepted count is zero.

A reproducible, pinned, per-cell full-coverage result keyed by exact row, column, and owner is required for positive repair or clearing the native hold; target-level `mapped_land_support` alone does not satisfy it. For a documented-unresolved proposal, each key instead retains its original fragment, both original multipart atoms, source-evidence rows, physical context, and a concrete unresolved coverage/source-applicability question. These proposals are not accepted: native holds remain and credit is zero. The shared witness is linked at [shared/original-contact-witness.json](../shared/original-contact-witness.json); its contacts are context, not per-cell intersections.

## Scope and caution

This is an evidence reconciliation, not a repair or acceptance decision. The original package has 7,499 `interval_segments`; `held-original` contains 255 row records and 267 held runs. These are distinct counts. This packet does not change the 27,555 original-cell scope, the 35-owner held scope, or other hold categories. No 210-style recompression or omission is applied. The source atom IDs are preserved verbatim for every tuple.

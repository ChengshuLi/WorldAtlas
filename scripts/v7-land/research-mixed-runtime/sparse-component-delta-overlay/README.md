# Sparse component delta arithmetic

This research-only library calculates the changed-cell impact of a supplied set
of whole-component land targets against an already verified candidate grid and
reference grid. It reads all selected component spans in one batched pass, then
compares every affected cell, including cells which previously matched. It
reports old mismatches, resolved mismatches, newly introduced mismatches and
reference-water cells separately. It neither builds a map nor selects geography.

The caller must independently authenticate the baseline reconciliation, the
exact component generation, candidate and reference streams, target category
bindings, the complete source-resolved decision delta, and all conflict and
protected-witness checks. The projection applies only while those inputs and all
other policies, line rules and physical masks are unchanged. It must not be used
to infer an allowlist from entire mainland components or a broad bounding box.
Physical-mask differences are separate from shared-land mismatch totals.

Inputs are caller-materialized little-endian uint32 RLE streams. Selected spans
are retained in memory, so memory use grows with the number of matching intervals. The chunk size controls iteration, not a limit on which
roots or intervals are included. A trusted execution environment is required.

The included synthetic tests include random per-cell differential comparisons,
new mismatches, reference-water exclusion, malformed inputs and valid root zero.
A separate, earlier exploratory variant was compared with pinned research data;
this code freeze has not received an end-to-end live-data replay or production
integration. No map build, publication or source validation is implied.

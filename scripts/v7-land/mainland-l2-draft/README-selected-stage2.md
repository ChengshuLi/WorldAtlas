# Draft stage-2 selected-input schema and exporter

Code and schema only. Apply on an authorized Neon draft branch with the existing atlas bootstrap and mainland boundary schema, never directly on production. The schema creates the selected stage-1 source links, stage-2 closure/region/witness/rule tables and revision-bound baseline policy. It contains no geography, raw sources, data selections, or credentials.

The read-only query exports the actual selected revision and catalog-backed source links. A consumer must reject missing selections, stale revisions, unverified source/geometry hashes, unsupported provenance, conflicting claims, failed physical closure checks, or partial outputs. It does not itself regenerate stage-1 physical inputs or prove that recovered candidate boundaries and raster application are identical to historical V7. Current R2 custody includes uploader-reported full readback, not a separately pinned bucket receipt. The policy represents a research selection, not production publication.

This is an incomplete building block: it does not include the stage-1 raster producer, stage-2 seed/geodesic executors, stage-3 List 1 overrides, or the historical-comparison verification. Do not run it as a complete map builder.

The v1 policy schema restricts connectivity, aggregation and tie semantics to the currently supported literals. Changing them requires a reviewed schema migration. Its separate distance-policy foreign keys do not alone prove that the referenced version is the version selected by that revision: the importer and consumer must validate the exact revision, policy ID and version together. A composite foreign key should be considered in a separately reviewed migration.

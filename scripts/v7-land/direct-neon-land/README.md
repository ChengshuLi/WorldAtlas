# Direct source-decision land compiler (research prototype)

This stage starts with a **physical land/water mask**, components derived from that mask, and a pinned versioned geography-decision export plus pinned source geometries. It never reads V2 continent labels or another prior continent grid. Existing V2 land/water is optional validation evidence only. Output is a new candidate, not a release. It can accept the newer physical mask with 674 known land/water differences; it does not require parity with the old mask.

**Current blocker:** the Neon draft has no land affiliations and only partial mask-bound witness rules. Source-component memberships, partition/cut polygons, mainland splits, and a complete coherent set of reviewed land decisions have not been established. An unpopulated or incomplete snapshot must fail, rather than silently inherit a baseline. The local snapshot hash and an `accepted` string do not authenticate a Neon revision. The tool consequently requires `--allow-unverified-snapshot` and marks every output `unverified-research-not-published`. Do not use for deployment, source acceptance, or claims of geographic correctness.

## Input contract: `direct-neon-land-build-v1`

The JSON config has exactly these keys: `schema`, `snapshot`, `grid`, `physical_rows`, `physical_runs`, `component_rows`, `component_runs`, `source_files`, and optional `strip_rows`. A file pin is `{ "path": "...", "sha256": "<lowercase sha256>" }`. Paths are local; all pins are checked at start and end. The grid is `{ "width", "height", "step", "west", "north" }`, north to south. Strip size defaults to 128. Values use the same center-sampled lon/lat grid as the physical build.

Physical rows are little-endian uint32 offsets into a flat stream of `(exclusive_end, code)` uint32 pairs; every row covers the width and uses 1 for water and 17 for physical land. Components are generated from those exact physical streams by `../build_components.cpp`: rows are uint32 offsets into `(start, exclusive_end, component_id)` uint32 triples. This compiler **recompiles and reruns** that component builder in its fresh output directory and requires byte-identical regenerated component streams. It records the source/binary hashes, compiler version and result. IDs are reproducible only for the exact physical input and algorithm, so source-based selectors below resolve them afresh. Validation compares actual membership, not only footprint. A representative invocation to produce intermediate components is:

```
g++ -std=c++17 -O2 -Wall -Wextra -Werror ../build_components.cpp -o /new/path/component-builder
/new/path/component-builder WIDTH HEIGHT physical-rows physical-runs /new/path/component-rows /new/path/component-runs
```

Snapshot accepts the existing `worldatlas-geography-decision-export-v1` shape only with both entity and decision statuses `accepted`; the distinct `worldatlas-geography-decision-draft-evidence-v1` only with both `draft`. Both require `source: neon-export`, matching entity revision IDs, and explicit unverified mode. These are semantic checks, **not** proof of real review. Snapshot fields consumed are `decision_revision`, `entity_revision`, `sources`, `features`, `category_bindings`, `affiliations`, and optional draft-only `land_component_witness_rules`. Every source map entry is:

```
{
  "source_id": "...", "source_version": "...",
  "file": {"path": "...", "sha256": "..."},
  "id_property": "provider_id_property"
}
```

The local file must be a GeoJSON FeatureCollection, hash-identical to the source in the snapshot. `id_property` names a feature property whose string value identifies the pinned `source_feature_id` exactly once; a numeric property is stringified. The feature geometry must match `geometry_sha256`, calculated from JSON geometry with sorted keys, compact separators and UTF-8 (the same convention as the existing replay code). Only valid nonempty 2D Polygon/MultiPolygon geometries are accepted, WGS84 lon/lat degrees; antimeridian-crossing edges must first be represented as explicitly split source geometry. These limitations deliberately avoid silently picking a wrap convention or geometry repair. Each input feature's whole source file and feature digest are checked; a file path is not authority.

## Proposed executable land affiliation contract

This is a prototype semantic extension to the existing Neon records. It has not been established as the accepted production schema. Each relevant row has unique `affiliation_id`, `feature_id`, stable `entity_id`, `relationship: "affiliation"`, `scope: "land"`, nonempty `rationale`, and `evidence.selector`. The entity must have exactly one `physical_class: "land"` category binding with code 17–22. The feature identifies the selected source ID/version, source feature ID, and canonical geometry hash. Each record must use exactly one of:

- `method: "component_intersection_v1"`: every physical component with at least one center rasterized inside its polygon is assigned to that entity. Its selector is `{ "additional_feature_ids": ["..."], "include_witnesses": [ {"lon": "...", "lat": "..."}, ... ], "exclude_witnesses": [ {"lon": "...", "lat": "..."}, ... ] }`. The primary feature and each unique additional feature are separately hash-verified, rasterized, and their hit-component sets unioned before exceptions. Empty additional lists are allowed. Coordinates are finite decimal **strings**. Include witnesses explicitly add distinct components outside the source polygon, and exclude witnesses remove distinct intersecting components; the resulting selection must be nonempty. An inclusion already hit by the polygon is rejected as redundant. This supports documented source-group exceptions where a selected physical component has no center inside the source polygon. The cited Psara site polygon does not cover the main island anchor but does intersect its connected physical component elsewhere on the current grid, so an inclusion witness is not necessary for that exact grid. Use exclusions deliberately for mixed-continent mainlands or other source-specific overlaps, not as an inferred precedence rule.
- `method: "component_partition_v1"`: selector is `{ "component_witness": {"lon": "...", "lat": "..."} }`. It identifies one physical component, and the feature polygon assigns the entity at intersecting cell centers within that component. Multiple such records for that component jointly form a partition. Every physical-land center in the component must have **exactly one** part. No part may overlap a whole-component claim. At least one cell of that component must intersect each part.

Witnesses resolve to the physical component containing the specified point's grid cell. Missing, duplicate or ambiguous source records, unsupported methods/relationships, no-hit features, missing/duplicate/invalid exclusions, duplicate component claims, partition overlaps, partition gaps, and any unassigned or unused component all fail. No implicit source hierarchy, precedence, point-nearest assignment, default continent, V2 assignment, or legacy difference spans are applied. The general source-to-component rule can be unsuitable for some real geometries; changing it requires a reviewed method/schema change, not bypassing a failing check.

Rasterization uses GDAL default polygon mode (`ALL_TOUCHED` off). Polygon boundary exactly through a cell center may depend on GDAL conventions. The component builder always wraps longitude and requires a global, correctly ordered mask. Geographic source inclusion, polar/dateline geometry, raster boundary ties, source snapshot lineage, source semantics and actual decision completeness require independent review. Material output from this prototype is not scientifically verified merely because it is complete.

## Run, safety and output

Requires `/usr/bin/python3` with GDAL/OGR, GEOS and NumPy, plus `g++`. Run:

```
/usr/bin/python3 compile_land.py --allow-unverified-snapshot config.json /path/to/new-output-directory
```

All outputs are created under a new directory that neither contains any input nor is nested within any input file’s parent directory, including the config’s directory. No existing input is edited or deleted; interruption/failure may leave partial files. A successful run writes `land/rows.u32le` and `land/runs.u32le`: uint32-LE row offsets and `(exclusive_end, code)` pairs. All physical-land cells receive 17–22; water is placeholder 1, not final water affiliation. The top-level `report.json` is written only after all stages complete and recheck the input hashes. It contains snapshot/revision IDs and digest, physical/component input digests, component verification and output digests. Intermediate extracted geometries, regenerated components, the compiler config and nested compiler report are retained for audit. A complete report is still explicitly unverified.

Run `/usr/bin/python3 -m unittest -v test_compile_land.py` in this directory. Tests are synthetic and include direct assignment, partitions, hash and snapshot validation, connectivity regeneration, conflicts and fail-closed coverage. They do not establish global performance or verify real decisions. A preflight against the observed empty Neon draft and the newer candidate physical streams correctly failed with `snapshot has no land affiliations`, without creating an output directory. The actual draft may change and must be freshly exported and pinned before further attempts.


## Draft witness rules

A `component_witness_list_v1` rule selects physical components using coordinate witnesses. Each rule is valid only for its exact physical and component stream hashes, grid and component-builder source hash. Its cited source files, geometry hashes or named-source document hashes are evidence only; the compiler does not verify those bytes. Conflicting claims, mismatched pins and unresolved or duplicate witnesses fail. These rules are explicitly restricted to draft evidence snapshots; accepted exports do not yet cover them. They do not relax the requirement to assign every physical component. The selected-rule diagnostic resolved 51 components and left 457,842 unassigned, so no full land map was generated.

Each witness rule and draft land affiliation needs an explicit `execution_status`. `selected_for_research` remains an unaccepted draft. The compiler fails the entire build if any rule is unmarked, unknown, or marked `research_only_not_selected`; it never silently skips or executes such candidates.

## Component baseline

On 2026-11-04, one run of the current component builder on the actual 131,072 × 54,614 physical grid took 2.934 seconds and peaked at 628,544 KiB RSS. It produced 13,315,490 component runs (159,785,880 bytes) and its row/run hashes matched the previously saved components. The container reported nine available CPUs, Linux 6.18.57 and GCC 14.2.0. This is one local measurement with cache state uncontrolled; it covers only component construction, not source rasterization, land assignment, water assignment or the end-to-end build. The default audit path independently recomputes components; the optional same-run path below generates them once and streams ordinary assignments. Neither path is yet a fully validated global pipeline.


## Same-run streaming candidate

`run_single_generation.py REQUEST NEW_OUTPUT --allow-unverified-snapshot` generates physical components once and then streams assignment runs. The request schema `single-generation-direct-land-v1` pins the draft snapshot, grid, physical rows/runs, a physical-stage report, source files, and the component-builder source hash. The physical report may be a raw-pipeline report or a weaker compose-only report; its kind is recorded. The orchestrator writes a component manifest, a nested assignment report and a top-level completion report. Its same-run manifest binds bytes and code, but is not independent connectivity verification or source authentication. The default `compile_land.py` path retains independent component recomputation for audit.

On a 131,072 × 256 raw-physical band with synthetic labels and one partition, two baseline assignment runs took 2.189 and 1.648 seconds at about 323–325 MiB peak RSS; the corrected streaming version took 1.590 and 1.599 seconds at about 162 MiB. Row/run output hashes were identical; timing was noisy and does not establish a speedup. Full-width partition rasters preserve GDAL boundary behavior while hit/label arrays are limited to component extents. An 8,192 × 1,024 raw-mask subset also matched end-to-end. These are single-host subset tests, not full-world equivalence or a production speed guarantee. The complete decision set and independent geographic validation remain missing.

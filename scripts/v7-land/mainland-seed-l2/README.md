# Stage 2 mainland seed (research implementation)

This producer constructs a continent-labeled mainland seed from the accepted
stage-1 physical grid, current-generation mainland witness resolutions, and
selected versioned geography decisions. It does not consume V2 or V7 label
rasters and does not apply List 1 or island exceptions. The separate geodesic
driver must validate the selected Neon export, rerun witness resolution, and
independently verify full physical/component coverage before accepting output.
The generated seed report remains explicitly diagnostic until those checks pass.

`seed_producer.run(request, work, output)` consumes a pinned
`worldatlas-stage2-seed-direct-request-v2` request. Its `controls` object contains
only a positive integer `strip_rows`, which controls rasterization chunk size.
The closure contract uses `physical-water-closure-contract-v2`; its `resources`
contains only `max_cell_visits`, a geometric traversal bound. `inputs` pins the decision snapshot,
witness resolution, physical and component rows/runs, physical report, component
manifest, water-closure checker and contract, and reviewed rasterizer source.
A terminal-aware route additionally requires a pinned `terminal_checker` input;
only the independently reviewed allowlisted code is executable. Work and output
are fresh, disjoint directories. The producer and closure clients run directly. This runtime does not launch a
supervisor or impose a memory floor, process-memory cap, or timeout. It does not
assess constraints inherited from the execution environment, such as a cgroup,
external supervisor, or operating-system limits. The water placeholder is zero; seed land uses the continent
codes provided by the pinned category and rule decisions.

When the Panama–Colombia boundary is selected, `inputs.panama_osm_archive`
must pin the archived OSM way/full response bundle linked in the selected
source catalog. The producer validates the archive and every response, joins
the ways, and requires its geometry hash to match the selected Neon line
before assembling the region. It records the archive and geometry hashes in
`panama_source_trace`; all input and code hashes are rechecked at completion.
The caller must still authenticate the export and download the archive from
the cited R2 key. This verifies the current-source handoff, not historical
OSM coordinates or an entire map generation.

Every selected region is an explicitly ordered ring of stored L2 boundaries and
physical-water closure routes. Geographic connectors without a physical closure
proof are not supported by this builder. A terminal-aware closure references
selected boundary IDs plus their exact start/end vertices, is checked against the
pinned physical mask, and may touch land only under the checker's explicit
terminal policy. The separate ring builder checks exact joins, simple polygon
validity and region witnesses. Its rasterizer assigns every cell of a selected
mainland root by region membership rather than leaving flood-fill residuals;
per-rule and per-category populations are verified and reported.

The selected export interface, final endpoint-aware checker, and actual closure
routes must be validated and versioned before a real run. A sourced L2 boundary
is a geographic decision; citation and byte pins do not establish that every
historical V2/V7 rasterization detail or upstream source is recovered. No prior
candidate, checkpoint, or historical changed-cell ledger supplies seed labels.

Run focused local tests from this directory with:

    python3 -m unittest test_export_adapter test_regions test_seed_rules test_closure_client test_region_client test_seed_producer test_osm_source_handoff test_panama_seed_source test_direct_seed_kernel
    (cd closure-checkers && python3 -m unittest test_validate_water_closure_v2 test_terminal_closure)

The selected exporter records each boundary-source relationship alongside the
source ID/version. The adapter permits only reviewed relationships. Citations
marked supporting research remain supporting evidence in region traces and are
not represented as original construction inputs. A construction input must be a
pinned provider-original raw asset with documented origin; complete lineage
requires at least one such input. Incomplete lineage remains explicitly reported.
Pins and stated relationships do not verify provider bytes, prove historical
construction, or establish geographic correctness. Unknown relationships fail
closed and need review. This research classification does not alter geometry.

Closure routes retain selected stage-1 source citations and their stated
provenance. The seed worker validates the returned closure proof against the
physical report hash as well as the rows, runs and checker contract. Terminal
closures require the allowlisted terminal checker. The full geodesic
orchestrator remains gated until its seed freeze and validator receive an
independent real-GDAL review; this does not authorize changing frozen hashes
without verification. The rasterizer source freeze pins the witness guard;
its coordinate uncertainty box is not a geographic distance measure.

This is an unpromoted direct-run candidate. Its new checker and rasterizer bytes
are deliberately not added to the existing executable allowlist or source freeze
until independent verification. Historical closure proof hashes are not claims
about the new checker: the integration must rerun the closure proofs against the
v2 contract and preserve the original selected snapshot and independent replay.

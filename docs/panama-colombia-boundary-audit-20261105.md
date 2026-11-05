# Panama–Colombia boundary: source and pipeline status

Read-only inspection of the `continent-review-v1` Neon branch on 2026-11-05.
This is a draft research decision, not accepted geography.

## Selected data

Revision `v2-land-mainland-boundary-draft-1` selects
`panama_colombia_osm_admin_boundary` using `stored_linestring_v1`.
Its 5,254-vertex CRS84 LineString has canonical binary64 sorted compact GeoJSON
SHA-256 `cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.
The database provenance reports that 33 historical OSM ways joined using
current OSM node coordinates reproduced this hash. That statement is not
itself a retained coordinate input or a reproducible build.

The two linked catalog entries are provider-original OSM API responses:

- `worldatlas/sources/osm/panama-colombia/historical-ways-versions.json`,
  SHA-256 `b101f03f55339f4dfe26118f6b88f71ac5cd5acd25281eb6adb12c9db8836e0e`.
- `worldatlas/sources/osm/panama-colombia/historical-relations-versions.json`,
  SHA-256 `2f1107e182aa1c06245068754b80bd632be84c13858b940c39d10f04bc2e7a29`.

Their catalog provenance records full R2 readback verification. This audit
read the catalog, not the objects themselves. Both are classified as
supporting membership evidence; neither contains the node coordinates needed
to rebuild the line. No Panama coordinate source appeared in the source
catalog. Capture and retain the actual used provider-original coordinates,
record and verify their bytes and source/version in the catalog, and implement
and test a deterministic extraction and joining step before claiming complete
raw-source-to-line reproducibility. Do not infer historical coordinate versions
from historical way membership. Exact V7 reconstruction is not required.

## Land assignment

The selected `north_america_mainland_region_v1` consists of the entire
boundary in forward order and `americas_exterior_closure_v1` in reverse.
The latter is a selected 14,541-vertex water closure with terminal references
to the same line; its SHA-256 is
`36d72849f2677a2a31250451d81c614d5e00e6b3228635470167a30ef1dbb940`.
Its proof is bound to a specific physical mask and must be rechecked against
the actual generation. The region stores six inside/outside witnesses.

`scripts/v7-land/mainland-seed-l2/regions.py` checks line hashes, ordered
joins, closure proof, polygon validity and witnesses. `seed_producer.py` and
the rasterizer use current physical components and the assembled region to
assign mainland cell centers; see the adjacent README for the input contract.
These are research-stage code and the README states that the complete
orchestrator remains gated for independent review. The Panama direct cut-graph
experiment in `scripts/v7-recovery/land/panama-direct-split-research-20261104/direct.py`
is explicitly retired at its entry point and is not the selected workflow.

The present source-to-map chain therefore starts at a saved structured line,
not yet at a complete, pinned set of raw OSM inputs. The remaining work is to
capture the coordinate source, implement and validate its assembly, connect it
to the selected-line workflow and run the actual selected export and seed
against the current physical generation. A matching line hash alone does not
establish closure validity or end-to-end land assignment. No geography changed.

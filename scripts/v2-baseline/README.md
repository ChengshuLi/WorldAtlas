# V2-style source and comparison utilities

These research utilities build components, source-driven seed regions and explicit water routes from pinned inputs, or compare a completed candidate with a preserved reference. The prior spherical nearest-mainland land builder and its dependent spherical coastal-band wrappers have been retired; old checkpoints and old partial water bands must not be resumed as WGS84 output. Historical reports remain evidence, not inputs that authorize new geographic decisions.

- `build_components.py` derives wrapped physical-land components from pinned physical rows, runs and a matching report.
- `build_regions.py` and `build_seed.py` render explicit source-region and component rules. `build_water_route.py` builds a caller-specified physical-water connector using WGS84 ellipsoidal center-to-center edge costs and deterministic weighted Dijkstra. This is the shortest path on the selected four-neighbor water-cell graph, not a continuous unconstrained geodesic. The source, endpoints, bounds and route choices require review. The v2 route schema intentionally rejects old unweighted v1 route reports; regenerate them before reuse.
- `compare_land.py` compares a pinned candidate and reference without using reference labels to build the candidate.
- `list1_reconciliation/` retains generic tools for reviewing historical List 1 provenance. It does not make geography decisions by itself.

Use fresh output directories and validate the source, grid, component and code pins in each report. Research output is not an accepted or published map. The current WGS84 land-distance research is in `../v7-land/research-mixed-runtime/stage2-geodesic-20261104/`; proposed water-center code is in `../v7-replay/` and requires its versioned WGS84 policy.

Run retained synthetic tests with `python -m unittest -q test_build_components test_build_regions test_build_water_route test_compare_land`. These tests do not establish historical or geographic equivalence.

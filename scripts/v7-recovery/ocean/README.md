# Candidate ocean fill runner

This isolated candidate adapts the preserved interval flood-fill engine. It is not a release or a raw-source rebuild. It does not authenticate Neon snapshots and refuses the CLI unless `--allow-unverified-snapshot` is supplied. It never reads prior ocean labels and it creates a fresh output directory exclusively. No deployment is performed.

The snapshot uses `worldatlas-geography-decision-export-v1`: accepted, matching entity/decision revisions; endpoints with longitude/latitude; ordered routes; ocean seed records linked by entity IDs to water codes 7–10; and one `ocean_fill` policy with `connectivity: 4`, `wrap_longitude`, `barrier_tie_rule: "left-of-oriented-route"`, `unseeded_policy: "report-only"`, and explicit unique `route_ids` and `seed_ids`. Routes currently support `lonlat_polyline`, `meridian`, and `wgs84_geodesic`. The last needs `parameters.max_step_km` in (0,1] and exact `build.software_versions.pyproj` and `.proj` matching the installed libraries. Antimeridian-crossing routes and unsupported geometry fail closed. Distinct ocean seeds reaching the same connected component also fail. Seed names, boundary choices, and physical limits come from the export, not hard-coded geography.

The CLI also requires the prefill plan and audit, physical input RLEs, snapshot digest, and a new output directory. It verifies row/run, prefill, revision, plan, and snapshot pins. It emits binary barrier edges, the interval engine's partition and unseeded-component report, and a checksummed `worldatlas-full-water-assignment-tiles-v1` ocean layer. The layer contains only seeded residual-water assignments. Unseeded components are deliberately **not** automatically classified and require a separately verified closed-water process. Failed runs are left in place for inspection; choose a new directory for retries.

Example, with real paths supplied only after the required approvals and source preparation:

```
/usr/bin/python3 ocean_fill_runner.py --snapshot SNAPSHOT --snapshot-sha256 SHA256 \
  --physical-rows ROWS --physical-runs RUNS --prefill-dir PREFILL \
  --prefill-plan PLAN --out NEW_OUTPUT --allow-unverified-snapshot
```

`/usr/bin/python3 -m unittest -v test_ocean_fill_runner` runs synthetic checks including four separated basins, unseeded water, output exclusivity, versioned WGS84 route handling, and rejection cases. On this machine PyProj is in system Python, not the default primary runtime.

Before use beyond a test: authenticate the exported Neon revision and trusted snapshot digest; populate and review actual route, endpoint and seed decisions and policy; independently establish source/barrier geometry and physical/prefill completeness; verify exact software and environment pins; perform a fresh global run; review all unseeded components and barrier contacts; adapt the closed-water outputs; and complete global connectivity, overlap, land/physical invariance and final composition checks. The preserved flood-fill core and ties are candidates until independently validated against those requirements. The unverified flag is not production authorization.

For draft research, first run `make_candidate_build.py --snapshot SNAPSHOT --snapshot-sha256 SHA --physical-dir PHYSICAL_OUTPUT --physical-report-sha256 SHA --out NEW_MANIFEST --allow-draft-snapshot`. This binds the new physical TIFF and row/run hashes, the draft snapshot and installed geodesic software versions. Pass its path and digest with `--candidate-build` and `--candidate-build-sha256`, as well as `--allow-draft-snapshot`, to the ocean runner. The existing `--allow-unverified-snapshot` is still required. No historical physical-grid pin is used for this draft path. The candidate manifest is not an approval, and the complete coast, closed-water and decision inputs are still required for a final map.

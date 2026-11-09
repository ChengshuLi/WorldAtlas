# Candidate ocean fill runner

V8 uses the editable `v8-ocean` revision in Neon. The four seed points
are inside the selected marine features in the pinned Natural Earth
archive. The end-to-end pipeline binds the ocean export to the current
land and named-water selections before calling `ocean_fill_runner.py`.

## Southern ocean route sources

The raw source catalog records the official 1953 IHO S-23 PDF as
`iho-s23-limits-of-oceans-and-seas`, version `1953-ed3-en-ff838517a57c`.
The selected ocean revision cites it for the 20°E meridian from Cape
Agulhas and the 67°16′W meridian from Cape Horn. It also cites the
historical South East Cape meridian for comparison with the modern
meridian used by V8.

The Cape Horn endpoint uses 55°59′S and 67°16′W, consistent with the
[Australian Antarctic Data Centre gazetteer](https://data.aad.gov.au/aadc/gaz/place_names_within_map.cfm?east=-44&north=-47.1666666667&south=-56&west=-69.5).
The South East Cape endpoint uses 43°38′40″S and 146°49′30″E from
[Geoscience Australia](https://www.ga.gov.au/scientific-topics/national-location-information/geography/extreme-points).
Both endpoints store exact fractions for the degree values in Neon.

At Cape Agulhas, the [SANParks tip latitude](https://www.sanparks.org/parks/agulhas/what-to-do/activities/scenic-landmarks)
locates the search along the 20°E meridian. The selected endpoint is the
nearest south-facing edge with dry cells on both sides of the meridian in
the row above and water cells in the row below. The current physical grid
has that transition at row edge 45,450, between columns 72,817 and 72,818.
It yields latitude −34.8321533203125°.

## Iceland source extraction

Run `python extract_s130_iceland.py --archive S-130.zip --output iceland-routes.json`
with the archive registered as `iho-s130-global-sea-areas`, version
`1.0.0-44997a24a4fe`. The extractor verifies the ZIP and GML hashes and
recovers the two Iceland rhumb routes and their four endpoint coordinates.
It reads the endpoints of construction lines `M.1505` and `M.1504`, then
reverses their order to match the selected routes in Neon. For Jan Mayen
South Cape, the line endpoint is `-9.04279190236343` longitude and the
associated point is `-9.04279190236342`. The selected Neon record uses
the line endpoint. The extractor was reconstructed from the retained
source and records. It emits a new JSON document.

## Runner

This isolated candidate adapts the preserved interval flood-fill engine. It is not a release or a raw-source rebuild. It does not authenticate Neon snapshots and refuses the CLI unless `--allow-unverified-snapshot` is supplied. It never reads prior ocean labels and it creates a fresh output directory exclusively. No deployment is performed.

The snapshot uses `worldatlas-geography-decision-export-v1`: accepted, matching entity/decision revisions; endpoints with longitude/latitude; ordered routes; ocean seed records linked by entity IDs to water codes 7–10; and one `ocean_fill` policy with `connectivity: 4`, `wrap_longitude`, `barrier_tie_rule: "left-of-oriented-route"`, `unseeded_policy: "report-only"`, and explicit unique `route_ids` and `seed_ids`. Routes currently support `lonlat_polyline`, `meridian`, `wgs84_geodesic`, and `spherical_rhumb`. Both geographic interpolation types require `parameters.max_step_km` in (0,1]. Geodesics additionally require exact `build.software_versions.pyproj` and `.proj` matching the installed libraries. Rhumbs are constant-bearing curves interpolated in spherical Mercator coordinates, matching the IHO S-130 Ed.1.0.0 construction lines; pole endpoints are unsupported. Antimeridian-crossing routes and unsupported geometry fail closed. Distinct ocean seeds reaching the same connected component also fail. Seed names, boundary choices, and physical limits come from the export, not hard-coded geography.

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

Draft coast, closed-water and ocean policies require an explicit research-selection marker before execution. An unselected or unmarked policy stops the relevant builder; its presence in an export is not an approval.

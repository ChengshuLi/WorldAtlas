# Issue #608 — BC–Washington coastal edge review

## Decision

**All 18 assigned gap samples assessed; cause unresolved.** Each sampled point lies on the IBC section 25 line. The nearest edge among the 61 assigned BC locations is `atlas:district:CAN-5915:BRC` (Greater Vancouver); distances range 1,011.90–5,888.53 m. Each point is within 0.2 m of the 2024 TIGER/Line Whatcom County (`53073`) boundary, while San Juan County (`53055`) is not the nearest edge. Five points are not strictly contained by the county polygon; the distances to its edge for those points are 0.011–0.052 m. The remaining 13 fall within Whatcom.

This supports the reported cross-source discrepancy but does not determine whether it arises from water representation, source vintage, mapping scale, or another geometry convention. TIGER records substantial county `AWATER` for both counties, but that attribute does not identify the surfaces responsible for these sample distances. The 2021 Statistics Canada Census Division response used here has `LANDAREA` but no `WATERAREA` property. IBC explicitly restricts this line to mapping use at its stated scale and says it must not define the boundary. Therefore the assessment makes no political ownership/legal boundary finding and proposes no correction to shared boundaries. A future certified hydrographic/admin comparison would need coordinated source owners on both sides and a source that licenses that use.

`sample-assessment.json` gives a row for each of the 18 samples, coordinates, nearest BC/CD/WA edges, distances to Abbotsford’s boundary, and county containment. Abbotsford (`gb:CAN:ADM3:43193130B1191968375732`) is 23.3–40.2 km from these points, so it is not the nearby candidate for this particular run. The reproduction script recomputes it from the authorized temporary IBC download plus immutable #485 source inputs.

## Baseline identity and current memberships

Reviewed against geographic release 5 / Site 21, Western North America region `framework:region:western-north-america:d2a1c2775a57`; region geometry SHA-256 `7697f7a1a388f6b3e289ef00795cdb5e86bf9138f89eb97ec8d19bcfa1c131a9`, member-ID SHA-256 `3e060c8e712c4955bdb2996d4edf3b9271aaa8d0120501171cc7327e10797aaf`, and macro certificate SHA-256 `979afaf22e10dc936ecfe80a8cd288b2ef33d8c7bf509aba9fae4255e3d94d6e`.

- BC assigned candidate: `atlas:district:CAN-5915:BRC`, Greater Vancouver → province `framework:province:british-columbia:83abeaaac0ca` → area British Columbia `framework:area:british-columbia:4ac4bdf4a9b8` → Western North America → Northern America → North America.
- Current Washington `Whatcom` and `San Juan` members are `gb:USA:ADM2:52423323B9068998137459` and `gb:USA:ADM2:52423323B32782252789959`, respectively, in `data/geography/part-27.json`. Their parent chain is Washington province → Pacific area → Western North America → Northern America → North America. They use geoBoundaries USA ADM2, 2018 vintage, Public Domain, source role County. Current BC members and complete parent chains come from the pinned #485 packet.
- The BC candidate’s lineage is a 2021 Statistics Canada Census Division-derived group. The official 2021 CD 5915 shape and current WorldAtlas group share the reported gap. This is not an independent legal provincial boundary. The separately mapped Abbotsford feature is geoBoundaries Canada ADM3, 2016 vintage; geoBoundaries metadata lists ODbL 1.0 while also citing a Statistics Canada license detail, a source-level discrepancy preserved in #485. The complete BC assignment cohort contains 61 locations. One physical feature, `atlas:physical:CAN-185:BRC` (Northern Coastal Mountains), has no usable area boundary after the temporary validity repair used for this screen; it is recorded in `sample-assessment.json`, contributes no edge candidate, and is not treated as a hit or omitted land.

## Sources and lawful retention

| Source | Canonical reference / date | License and retained material |
|---|---|---|
| International Boundary Commission US–Canada boundary v1.3, section 25 | [IBC download page](https://www.internationalboundarycommission.org/en/data-downloads/); [direct archive](https://www.internationalboundarycommission.org/uploads/shapefile/us-canada-boundary-v1-3.zip); source metadata 2018-04-20; server Last-Modified 2022-10-21. Downloaded 2026-10-03 for this review. | Page states ©2015 IBC, All Rights Reserved and mapping use only; no open redistribution license identified. Archive (258,764 bytes, SHA-256 `eb327459528b87cbc27e55ccc6bfd6982562c75559823a00b6dc50c04abcaab1`) was used temporarily and is not included. Restore only from the direct official URL after rechecking current terms, verify size/hash, do not republish bytes, and use for mapping only. The existing derived sample evidence and source receipt remain the retained research record. |
| Statistics Canada 2021 Census Divisions, BC extract | [ArcGIS item 24f45c7b49d84aaf8e55e566a7fd670b](https://www.arcgis.com/home/item.html?id=24f45c7b49d84aaf8e55e566a7fd670b); 2021 Census; exact retained response at #485 packet | Statistics Canada Open Licence. Retained source `statistics-canada-bc-census-divisions-2021.geojson.gz`, 38,880,150 bytes, SHA-256 `8a31cf19ad0694638c88275fec9ff1005970cd8600ca6baed245b8826756e9bf`. |
| U.S. Census Bureau TIGER/Line Washington counties | [2024 TIGER directory](https://www2.census.gov/geo/tiger/TIGER2024/); county vintage 2024, database update 2024-09-16. | U.S. federal public-domain work product. Retained #485 extract `tigerline-2024-washington-counties.geojson.gz`, 859,249 bytes, SHA-256 `74c2822d327082e2738a8d93d59bc5eadf42590f7fef0941221e61deb36a4034`. County records include `ALAND`/`AWATER`; these summary fields do not establish where water is represented in the geometry. |
| Current shared WorldAtlas features and parent chains | Release 5 / Site 21 pins above. | Audited in place, not copied/edited. #485 source snapshot SHA-256s: `current-scope-and-parents.geojson.gz` `7ac3154985ef3bf5aae5b978481233e3a73c0ef6b2a753e1c7a15cef4c9302bb`; `current-parent-chains.json.gz` `aa0c1643d376baa9b7478d26886510718d3c0e242782df004e2defd028938290`. Live part hashes at review: `part-27.json` `e8df7555853e9262162c5e5d5c85e5c30be3fa8f0e6339bafec0e08323054758`; `part-29.json` `077e3bdfb18a42318e27bad840bba823a5049ced449407584fb4b9be2ef67c7a`. |

All retained external source bytes above were already lawfully retained in #485; this packet references their exact paths and hashes without altering the baseline. IBC’s restricted archive is not retained. The report is derived map evidence only.

## Method and reproduction

The IBC line is transformed from NAD83 geographic coordinates (EPSG:4269) to Statistics Canada Lambert (EPSG:3347). The exact #485 method samples section 25 at 1 km intervals (74 points in total); the scoped set is samples 50–67 inclusive, the 18 consecutive samples with nearest assigned BC location boundary over 1 km. For each, the script calculates nearest boundary distance to all 61 BC-assigned location geometries, the specific Abbotsford geometry, all 29 retained 2021 Census Division shapes, and 2024 Washington county polygons; it also reports strict county polygon containment. Temporary reprojection/validity repair does not edit any source geometry. Distances are screening measurements; precision is bounded by input scale, line/source vintage, projection and sampling. Boundary points may not be strictly contained by either side.

From the repository root, after restoring the IBC archive to a temporary path outside the repository and verifying the receipt above, run:

```sh
/usr/bin/python3 data/regional-review/bc-washington-coastal-edge-followup-2026/analyze_section25.py /tmp/ibc-boundary-v1-3.zip
```

The script requires GDAL/OGR Python bindings. It fails closed on a hash/size mismatch, writes only `sample-assessment.json` within this issue’s owned path, and expects the immutable #485 source files at their original paths. The full five-section #485 screen can be reproduced with its archived `audit_ibc_bc_neighbors.py` using the same temporary authorized archive; it writes to #485's path, so do not run it from this issue checkout. The previously retained #485 summary was verified against the exact archive bytes used here (size and SHA-256 match).

## Scope accounting and handoff

- Assigned: 18 consecutive sample subjects from section 25; assessed: 18/18 with per-sample coordinates and three-side boundary distances in `sample-assessment.json`.
- Source conclusion: confirmed map-line/feature-edge discrepancy; water-treatment explanation plausible but unproven; exact cause and any correction remain unresolved.
- Geographic correction: none proposed. No hierarchy, geometry, canonical grid, schema, certificates, live data, or other worker evidence changed.
- Cross-region follow-up: coordinate any future precise land/water reconciliation with both BC and Washington source owners, preserve release-5 baseline pins, and seek sources licensed and fit for determining the intended common footprint. Do not infer political ownership from TIGER/StatsCan shapes or IBC's map line.

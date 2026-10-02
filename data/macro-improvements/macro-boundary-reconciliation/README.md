# Macro boundary reconciliation — issue #44

This follow-up independently checks all **570** previously measured Europe–Asia / Africa–Asia crossing candidate against detailed OpenStreetMap river geometry and the published geographic release 3. It does not change geography, historical claims, the grid, or immutable approval certificates.

## Result

- All 570 original candidate IDs and footprint hashes match the current release.
- 521 candidates have a strict majority on their **existing** continent after the stated 175 m sensitivity corridor deduction. None has an opposite majority.
- Of the previously unresolved 78 candidates, 29 now have this independent conditional confirmation; 49 still lack enough actual river-reach coverage to establish a strict majority.
- All four archived physical-segment uncertainties are reconciled with the actual current reporting convention. The Ural administrative seam is explicit; the older Greater Caucasus crest and Darien watershed alternatives were superseded by the approved Kuma–Manych-associated administrative seam and shared Panama–Colombia frontier. No exact physical crest or watershed certification is invented.
- All 19 named eastern-Aegean island routes are accounted for. Full shoreline and offshore-islet coverage is a separate global coverage audit.

The 49 remaining measurements are recorded individually. Administrative geographic conventions are permitted under the user's requirements and remain authoritative where a surveyed physical boundary is not supported. These cases do not become blank memberships or disappear from the ledger. They also must not be described as verified physical precision.

## Reproducibility and rights

`reconciliation.json` pins the exact published release, source archives, footprint snapshot, measurements and original approval inputs. `current-candidates.json.gz` retains the exact 570 current source geometries and chains. `measurements.json.gz` retains every measured share, full source lines, way IDs/versions/timestamps, corridor method and area denominator.

Three unchanged OpenStreetMap XML extracts are retained under `sources/`, with raw and compressed SHA-256 hashes, retrieval date and exact API URL. Attribution: **© OpenStreetMap contributors**. The extracts and their derived river geometry use the **Open Database License 1.0**: https://www.openstreetmap.org/copyright . The original atlas footprint licenses and provenance remain unchanged.

The Ural relation's 142 `main_stream` ways join exactly into one simple contiguous line. Side streams and tributaries do not become arbitrary continental borders. The Suez canal's two inspected main-channel ways join at an identical source coordinate. No line is extended north/south into an unsurveyed crest, coast or sea. Artificial polygon-closing edges are only exterior computation limits, outside the candidate longitude bounds.

Shares use the WGS84 ellipsoid area integral for source longitude/latitude edges, including holes and the **entire** location footprint denominator. All candidates are away from the antimeridian; each checked longitude span is less than 180°. A 175 m buffer is calculated in a local WGS84 azimuthal-equidistant projection and inverted before area measurement. That corridor is a declared robustness assumption, **not a guarantee of surveyed OpenStreetMap positional accuracy**. Larger 500 m and 1 km corridor checks are retained in `sensitivity.json.gz`. They produce zero opposite majorities; some narrow or near-balanced locations become unresolved as expected (519 and 517 conditional confirmations respectively). They do not certify survey accuracy. The source footprint itself is the applicable atlas footprint; this audit does not certify its coastal/water-mask correctness.

Run `python data/macro-improvements/macro-boundary-reconciliation/verify.py` from the repository to verify hashes, exact source joins, every retained candidate and all 570 measured shares. Geographic changes require a new coordinated release; this report proposes no such changes.

The Port Said port example shows why independent detail matters: generalized Natural Earth geometry nominally placed 62% east of its centerline, but that evidence was correctly unresolved after uncertainty deduction. The detailed OSM line places 81.12% west of the canal; 67.91% remains after the stated corridor deduction. The existing Africa assignment is supported without changing its footprint.

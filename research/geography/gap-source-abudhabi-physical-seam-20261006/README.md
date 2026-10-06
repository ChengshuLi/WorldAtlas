# Abu Dhabi physical seam source assessment (#1206)

Scope: the 134 archived physical-gap components selected by the exact pinned predicate in `reproduce-overlay.py`. This is a bounded source investigation, not a topology repair or authority assignment.

## Findings

The archived component geometries were compared, without snapping or buffering, to the complete source polygons returned by the current RESOLVE “Biomes and Ecoregions 2017” service for a bounding envelope containing the selected component extents. All 134 selected components intersect a feature named Arabian sand desert (`ECO_ID=810`) or Arabian-Persian Gulf coastal plain desert (`ECO_ID=811`). 132 have positive-area intersection with the latter. Two have zero intersection area against the sand-desert polygon at the coordinates/precision returned by the service. Those two are boundary-only results and need not be interpreted as area coverage.

This is evidence that the present hosted ecological polygons corroborate the named physical-region footprint for 132 components and delimit the other two at a boundary. Atlas stable IDs are derived from the source `ECO_ID`; the service ObjectIDs 38 and 825 are separate service row identifiers and do not contradict the Atlas IDs. The deliberately retained ObjectID 810/811 response resolves to unrelated Yucatán and Yunnan features and is only a negative control against confusing those identifier fields. The current service response is not a frozen historical snapshot, so historical source-byte and processing-vintage equivalence remain unresolved. Atlas records the original member as Abu Dhabi ADM1 (`86790563B99975224300185`) for both physical regions and records 14 adjustments in bands 0.001, 0.005, 0.01, 0.025 and 0.05 degrees. Those shared per-district adjustments are candidate processing context, not proof that a particular adjustment caused an individual residual.

No independently sourced water evidence was established for any component. The component corpus marks surface status unverified; this assessment does not infer water from ecological or administrative geometry. Per-component exact extents, source intersections, types, and areas are in `overlay-v1.json`. The output also carries each exact v2 investigation record, the complete component fragment bindings and their original feature hashes, source-contact references for all three subjects, and the full archived contact geometries involving any selected component. There are 51 retained component-to-component contact rows involving the selected roster (45 point-only ambiguous and 6 shared-edge); this count is scoped to those archived contact records and does not convert point contact into area coverage.

## Reproduction

Run `python3 reproduce-overlay.py` from the repository root with Shapely 2 installed. It reads the issue-pinned complete v2 priority investigations and component custody payloads, plus the retained source response at `sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson`. It writes `overlay-v1.json`. Geometry is interpreted as EPSG:4326 longitude/latitude; predicates are exact in the stored coordinate space and no buffer, snapping, or coordinate transform is applied. GeoJSON whole source features are retained, not clipped to the query envelope.

## Source terms and attribution

The RESOLVE response feature records identify CC-BY 4.0; attribute RESOLVE and Esri. The administrative comparison source is geoBoundaries gbOpen ARE ADM1 at the pinned release, with its original ODbL license and underlying OpenStreetMap/Wambacher attribution preserved. The source records and full original geometries are retained under `sources/v1/`.

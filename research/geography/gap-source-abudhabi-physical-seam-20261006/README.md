# Abu Dhabi physical seam source assessment (#1206)

Scope: the 134 archived physical-gap components selected by the exact pinned predicate in `reproduce-overlay.py`. This is a bounded source investigation, not a topology repair or authority assignment.

## Findings

The archived component geometries were compared, without snapping or buffering, to the complete source polygons returned by the current RESOLVE “Biomes and Ecoregions 2017” service for a bounding envelope containing the selected component extents. All 134 selected components intersect a feature named Arabian sand desert (`ECO_ID=810`) or Arabian-Persian Gulf coastal plain desert (`ECO_ID=811`). 132 have positive-area intersection with the latter. Two have zero intersection area against the sand-desert polygon at the coordinates/precision returned by the service. Those two are boundary-only results and need not be interpreted as area coverage.

This is evidence that the present hosted ecological polygons corroborate the named physical-region footprint for 132 components and delimit the other two at a boundary. It does not establish that those current bytes are the historical geometry used by Atlas. In particular, Atlas stores `resolve:810` and `resolve:811` as source IDs, while the service's current ObjectID values for those ECO_IDs are 38 and 825. The deliberately retained ObjectID 810/811 response resolves to unrelated Yucatán and Yunnan features and is only a negative identity control. The identity/vintage binding therefore remains unresolved.

No independently sourced water evidence was established for any component. The component corpus marks surface status unverified; this assessment does not infer water from ecological or administrative geometry. Per-component exact extents, source intersections, types, and areas are in `overlay-v1.json`. Exact point/edge contact records and original fragment bindings remain available in the pinned component custody aliases described in `evidence-quality.json`.

## Reproduction

Run `python3 reproduce-overlay.py` from the repository root with Shapely 2 installed. It reads the immutable complete priority investigations and whole-file component custody payloads pinned by `evidence-quality.json`, plus the retained source response at `sources/v1/resolve-ecoregions-abu-dhabi-envelope.geojson`. It writes `overlay-v1.json`. Geometry is interpreted as EPSG:4326 longitude/latitude; predicates are exact in the stored coordinate space and no buffer, snapping, or coordinate transform is applied. GeoJSON whole source features are retained, not clipped to the query envelope.

## Source terms and attribution

The RESOLVE response feature records identify CC-BY 4.0; attribute RESOLVE and Esri. The administrative comparison source is geoBoundaries gbOpen ARE ADM1 at the pinned release, with its original ODbL license and underlying OpenStreetMap/Wambacher attribution preserved. The source records and full original geometries are retained under `sources/v1/`.

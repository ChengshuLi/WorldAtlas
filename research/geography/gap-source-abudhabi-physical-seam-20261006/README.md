# Abu Dhabi physical seam source assessment (#1206)

Scope: the 134 archived physical-gap components selected by the exact pinned predicate in reproduce-overlay.py. This is a bounded source investigation, not a topology repair or authority assignment.

## Findings

The archived component geometries were compared without snapping or buffering to all five complete RESOLVE polygons returned for the component extent. Every selected component intersects Arabian sand desert (ECO_ID 810) or Arabian-Persian Gulf coastal plain desert (ECO_ID 811). 132 components have positive-area intersection with ECO_ID 811. Two have zero-area boundary contact with ECO_ID 810 at the captured source precision.

The Atlas stable IDs are derived from ECO_ID. Service ObjectIDs 38 and 825 are separate row identifiers. The deliberately incorrect ObjectID 810/811 query returns unrelated Yucatán and Yunnan features and is retained as a negative identifier control. The present service response is not a frozen historical snapshot. Both physical Atlas subjects refer to Abu Dhabi ADM1 source member 86790563B99975224300185 and record 14 shared adjustment operations in bands 0.001, 0.005, 0.01, 0.025 and 0.05 degrees. Those operations are candidate processing context, not proof of per-component causality.

The original source selector is pinned `data/location-policy.json` at baseline `cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1` (69,433 bytes; SHA-256 `efab4528fd4b7b180815ef82de93480f490ef8fa48ad9ef32d1f9d76a64b7fb9`). Its ARE rule selects ADM1 from the immutable full geoBoundaries URL; `scripts/administrative.py` transforms the `.geojson` suffix to `_simplified.geojson` before retrieval. The exact transformed URL and bytes are retained in the receipt. A repository-wide check found zero disagreements between all 200 policy country/level selections and registry entries. The pinned Atlas registry selects geoBoundaries' simplifiedGeometryGeoJSON. The captured simplified source file SHA-256 3d5094daf190b9df5a4888694517692e9271b98cb161450b8f3c103602e18c6c matches that registry field and the pinned 9469f09 release. The separately captured full seven-feature geoJSON has SHA-256 f6f0097b183518b7ddedd48c60b7e864e222156d2f0227bd345f271c2dd3d873. These are distinct source products; the full geometry is a comparison reference, not the Atlas-selected simplified input. Both preserve geoBoundaries gbOpen ODbL and OpenStreetMap/Wambacher attribution/share-alike obligations.

Every archived component intersects each of the two current Atlas physical subject features and the simplified Abu Dhabi source feature. One also intersects the simplified Dubai source feature and the current Dubai Atlas contact subject. Exact intersection geometries for the RESOLVE, simplified administrative, full administrative reference, and Atlas subject features are retained in overlay-v1.json. The output contains every exact v2 investigation row, all 140 original detector-fragment geometries with source hashes and component memberships, source-contact references for all three subjects, and all archived component-contact geometries involving the selected roster.

The archived component-contact product contains 51 geometry rows involving the selected roster (45 point-only ambiguous and 6 shared-edge). A separate custody-indexed component-links product contains 202 old-gap/new-component link rows involving these components: 128 identical-coordinate-only, 68 point-only-contact, and 6 carrying both identical-coordinate and positive-length-contact kinds. These are distinct namespaces/products; the link rows do not replace or add to the 51 component-contact geometries. Both inventories and their source relationships are retained separately in overlay-v1.json. Neither point contact nor identical coordinates are treated as area coverage.

No independent water or ice evidence was established for any component. All 134 component causal assessments are explicitly unknown. Ecological/admin geometry does not establish water.

## Processing lineage and limitations

The archived refinement code records make_valid, 0.001-degree topology-preserving simplification, intersection/difference grid size 1e-8, source-piece thresholds, and residual buffer bands from 0.001 to 0.1 degrees. The exact historical .cache/semantic/resolve-ecoregions.geojson input bytes and whole-file hash are unavailable from the pinned baseline. The current 2026 service response cannot substitute for those historic bytes. See source-processing-lineage-v1.json and handoff-v1.json. The historic operations and shared adjustment records are hypotheses about possible causes, not component-level causal proof.

## Reproduction

Run python3 research/geography/gap-source-abudhabi-physical-seam-20261006/reproduce-overlay.py from the repository root with Shapely 2 installed. It uses scripts/evidence/immutable.py to verify the issue-pinned baseline and reads all original source inputs from immutable Git blobs. It writes overlay-v1.json. Geometry is EPSG:4326 longitude/latitude and predicates are exact in the stored coordinate space; no buffer, snapping, or coordinate transform is applied.

## Source terms

The RESOLVE feature records state CC-BY 4.0; attribute RESOLVE and Esri. The exact simplified and full geoBoundaries source products retain their ODbL and OpenStreetMap/Wambacher attribution and share-alike obligations. Full source files, retrieval receipts, metadata, and hashes are retained under sources/v1/.

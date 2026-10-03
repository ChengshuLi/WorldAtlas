# Area-preserving candidate refinement

Issue #540, supplemental evidence. Earlier stage files remain unchanged.

The first full 266,240-width check proved representation, not acceptable area distortion. Six/four finer-grid hits are likewise not automatically better than one source-contained cell: dry-land area must still satisfy the existing 25% projected and WGS84 error limits. No exception to those limits is proposed here.

The held source dry-land areas are 18,616.94 m² for Kingman and 22,188.63 m² for Gardner. Exact integer-width search found both fit one genuine source-contained cell at width 262,152. Full collision-resolved preparation represented every one of 49,625 territories, but Howland Island then exceeded the area limit by 30.178%. That candidate is rejected; see `width-262152-full-check.json`.

Including Howland in the light source test gives candidates 262,162; 262,166; 262,180; 262,196; and 262,204. At 262,162, Kingman error is +23.156%, Gardner -13.869%, and Howland +17.151% in WGS84 area. These widths barely increase the existing resolution and do not require doubling GPU memory or a mobile-device compatibility change. The first passing width for the two islands alone is not necessarily the first passing width for the whole atlas.

`resolution-refinement.json` records source hashes, exact cell indices, projected and ellipsoidal errors, search limits and the first five passing candidates. Search used strict Shapely containment after the standard Web Mercator transform; cell areas use the same WGS84 ellipsoid latitude-strip integral as the full grid auditor. Polygon footprints and grid origin were never altered. A grid-width change shifts its regular centres globally, so every territory must be retested.

Root must serialize final combined-v5 compilation and begin with 262,162. Test complete representation, collision resolution, projected/WGS84 area, package size, fixed projection, fallback picking and device navigation before choosing or activating it. These candidate observations are not approval of the entire final-v5 dataset or a claim to have found the globally coarsest possible grid.

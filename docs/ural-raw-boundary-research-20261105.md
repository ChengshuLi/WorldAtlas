# Ural raw-source boundary research

This is a working construction, not a selected boundary or map release. It
uses the existing structured northern line as a route selector, not as a
requirement to reproduce a historical map. The selector still needs independent
geographic review and the complete source-to-output process needs to be packaged
and tested before selection.

The European HydroBASINS level-12 archive has SHA-256
`21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03`.
After replacing two interpolation spans with their source chords, a numerical
edge-coverage screen matched 3,437 of 3,437 non-gap segments to basin edges
within its one-millimetre residual test, using 1e-12 degree topological
normalization. This checks source fidelity, not basin convention or survey
accuracy. Two terrain-derived northern gaps use ArcticDEM; their four joins
were checked against actual raw polygon edges. The source-edge intersections
are at most 0.028 m from the earlier candidate cuts. Alternate terrain products
give different routes, so the terrain portions remain model-dependent.

The modeled southern connection uses a Copernicus GLO-30 three-basin interface
and a roughly 699 m D8 flow path to the mapped Ural spring pixel. The final
pixel-center-to-mapped-node snap is about 15.4 m. The mapped spring's identity
as the principal headwater has not been independently established, and modeled
flow is not a surveyed watercourse.

The archived OSM Ural relation v122 reconstructs 41,669 river edges and ends
at the canal/coastal node (51.5316205, 46.8307054). Mapped topology and the
available hydrological literature support following the Zolotoy channel and
Ural–Caspian canal, though this remains a cartographic convention. The relation's
`mouth` role is at the upstream Shagan confluence and is not used as the coastal
endpoint. The existing Caspian water closure starts at the canal endpoint; a
previous native-grid check found 2,956 water cells and one allowed terminal
land cell. This check does not establish the geographical correctness of the
water closure.

The complete working geometry has 46,416 vertices and canonical compact
GeoJSON SHA-256
`68390aa6ce5352226777adde3979315e1de85ca26d662c4b1c32610d1d73da66`.
The northern construction was rerun with all four cut edges checked against the
raw source and the complete geometry was reproduced byte-for-byte. The line is
simple and joins the existing water-closure endpoints. These checks do not make
it an approved or pipeline-ready boundary. The Kara endpoint's direct 22.13 m
connector is a documented construction rather than a surveyed shoreline. An
exact rational grid-contact check of its decimal coordinates touches one land
cell (89987, 7743), while the adjoining first exterior-closure segment touches
that land cell and the neighboring water cell (89987, 7742). This is a local
physical-mask check, not a surveyed shoreline. A separate rational all-touched
research check scanned both complete European water closures against the new
line and the pinned stage-1 physical mask. Both passed the terminal-cell
policy: the exterior closure visited 78,908 cells with only its Kara terminal
land cell touched, and the Caspian closure visited 3,161 cells with only its
Caucasus terminal land cell touched. This does not replace the pipeline's
formal proof or establish geographic authority.

Remaining work: package and test the entire deterministic construction,
including source and intermediate checks; substantiate the principal-headwater
and terrain choices to the required standard; generate the pipeline's bound
closure proofs; and persist the supported structured result and accurate
source relationships in Neon. Raw assets belong in R2. No map rebuild or
active-boundary change was performed for this experiment.

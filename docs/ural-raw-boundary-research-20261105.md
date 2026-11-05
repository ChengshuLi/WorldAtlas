# Ural raw-source boundary research

This is an isolated research selection, not a map release. It
uses the existing structured northern line as a route selector, not as a
requirement to reproduce a historical map. The selector still needs independent
geographic review. A fresh staging run has reproduced the complete construction
from the pinned sources and selector, including its derived intermediate hashes.

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
raw source and the complete geometry was reproduced byte-for-byte from a clean
staging directory. The 2 m ArcticDEM source tiles were reassembled and both
10 m nearest-neighbor gap rasters reproduced byte-for-byte; the actual D8
interface analysis uses a 15 m model grid. The Copernicus spring-flow result
also reproduced without requiring the independent ALOS comparison as an input.
The line is
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

The structured geometry and seven source relationships are stored in Neon
project `wild-cherry-46472487`, branch `br-shy-mountain-arsff6zb`, database
`worldatlas`, draft revision `ural-raw-source-workflow-20261105`. Readback
confirmed all 46,416 coordinates, the geometry digest, and seven source links.
The ArcticDEM links identify R2 manifests whose listed parts reassemble the raw
provider tiles; the manifest hash is not the raw tile hash. The new revision
is isolated and does not contain the complete global region decisions needed
to run the mainland seed. The prior structured selector's historical lineage
remains incomplete, even though the current construction was reproduced.

To reproduce locally, gather the seven cataloged inputs and the pinned Neon
export into one input directory. Name the reassembled ArcticDEM tiles
`ural-arctic-gap00.tif`, `ural-arctic-gap02a.tif`, and `ural-arctic-gap02b.tif`;
use `ural-hydro-eu.zip`, `ural-hydro-si.zip` and the matching extracted
`ural-hydro-eu` and `ural-hydro-si` shapefile directories; name the remaining
files `ural-copernicus-dem.tif`, `ural-river-r2.osm`, and
`review_snapshot.json`. Run:

```sh
python scripts/ural-audit/reproduce_raw_boundary.py \
  --inputs /path/to/inputs --helpers /path/to/pinned-helpers \
  --workdir /path/to/new-empty-workdir
```

The work directory must not already exist. The runner checks helper and source
hashes, writes only local intermediates and logs, and checks the final geometry
file hash. Its five helper hashes are pinned in the runner; use the audited
Ural helper versions at PR4 commit `1b494125152ae343ee48efc84b3696140c4ae82c`.
The clean run used Python 3.9.6, NumPy 2.0.2, rasterio 1.4.3 / GDAL 3.9.3,
pyproj 3.6.1, Shapely 2.0.7 and Numba 0.60.0. Byte hashes may depend on the
toolchain; a different toolchain must be validated rather than silently accepted.

Remaining integration: represent the actual construction-source relationships
in the seed adapter's current source-role contract, generate candidate-bound
formal closure proofs, and combine this research boundary with the other
required region decisions. The modeled spring and terrain choices remain
qualified geographic decisions, not survey claims. No map rebuild or existing
active-boundary change was performed for this work.

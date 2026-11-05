# Bounded priority-flood research primitive

`priority_flood.py` contains array-level primitives for exploratory local
terrain analysis. `priority_flood(elevation, valid)` fills closed depressions
from the edge of a supplied raster window and returns a filled surface and
parent indices. The eight-neighbor `trace(...)` follows the steepest descent
using WGS84 geodesic distances between raster-cell centers and uses flood parents to route equal-height
flats. Arrays outside the mask must never be treated as terrain.

Every valid window-edge pixel and every valid pixel neighboring invalid data is
an **artificial outlet**. The method does not independently resolve masked
terrain, establish an actual stream, distinguish surface artifacts, validate a
named outlet, select a divide, or define a production boundary. A parent chosen
on a flat is a deterministic modeling convention, not a measured channel.
Results must be checked for sensitivity to crop size, source quality, masking,
grid spacing, conditioning and flat routing, and compared with independent
drainage evidence. Source inputs, coordinates and results belong in the
project's data stores, not this source directory.

Pass the WGS84 unrotated raster affine transform as the final trace argument; the former fixed-distance interface is no longer supported. Ties follow iteration order.

Requires NumPy, SciPy and pyproj. Run the synthetic pit, invalid-neighbor and validation
tests with `python -m unittest discover -s scripts/caucasus-audit -p 'test_priority_flood.py'`.

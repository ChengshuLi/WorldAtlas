# V8 Panama–Colombia boundary

The editable `v8-mainland` revision in Neon selects
`panama_colombia_osm_admin_boundary`. The 5,254-point LineString has canonical
GeoJSON SHA-256
`cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17`.

The raw archive `osm-panama-current-way-full-bundle`, version
`capture-20261105-04fe1adb295e`, contains 33 OSM way/full responses and their
manifest. The [archive verifier](../scripts/v7-land/mainland-seed-l2/osm_source_handoff.py)
checks the archive and response pins, joins the ways in order, and verifies the
geometry digest. The OSM way and relation history responses linked in Neon
supply membership evidence. The way/full archive supplies the coordinates.

The [mainland export](../scripts/v7-land/mainland-l2-draft/query-stage2-selected.sql)
supplies the editable line and its source pins to the V8 build.
`north_america_mainland_region_v1` uses the boundary in forward order and
`americas_exterior_closure_v1` in reverse. The closure has 14,541 vertices and
its canonical SHA-256 is
`36d72849f2677a2a31250451d81c614d5e00e6b3228635470167a30ef1dbb940`.
The [pipeline](../scripts/v7-pipeline/README.md) checks the closure against
the physical grid generated for that run. The region builder checks ordered
joins, polygon validity and the six selected inside and outside witnesses.

To verify the line after downloading the cataloged archive, set
`PANAMA_OSM_ARCHIVE` to its local path and run from the repository root.

```bash
PYTHONPATH=scripts/v7-land/mainland-seed-l2 python3 - "$PANAMA_OSM_ARCHIVE" <<'PY'
import sys
from osm_source_handoff import verified_geometry

line = verified_geometry(
    sys.argv[1],
    "04fe1adb295e93d78ee029b48351d2b0380d69ac631b47c909dffd538bbaf6c1",
    "cfbfbb514d0f6efff1c0c803ae5f0f0835225015568747bb8b1164f3bb6d0e17",
)
print(len(line["coordinates"]))
PY
```

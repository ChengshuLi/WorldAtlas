"""Identify island units whose source land disappears under majority-cell rules."""

import gzip
import json
import sys
from pathlib import Path
import numpy as np
import shapefile
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import shape

W, H, STEP = 16384, 6827, 360 / 16384
source, proposal = map(Path, sys.argv[1:])
land = np.frombuffer(
    gzip.open(proposal / "source-land-groups.u8.gz", "rb").read(), dtype="uint8"
).reshape(H, W)
priority = {
    "Tuvalu",
    "Tokelau",
    "Kiribati",
    "Marshall Islands",
    "Maldives",
    "Nauru",
    "Palau",
    "Micronesia",
    "Pitcairn Islands",
    "Cook Islands",
    "Niue",
    "Wallis and Futuna",
    "Samoa",
    "American Samoa",
    "Tonga",
    "French Polynesia",
    "Guam",
    "Northern Mariana Islands",
}
result = []
reader = shapefile.Reader(
    str(source / "ne_10m_admin_0_map_units/ne_10m_admin_0_map_units.shp")
)
for item in reader.iterShapeRecords():
    attrs = item.record.as_dict()
    if attrs["ADMIN"] not in priority and attrs["GEOUNIT"] not in priority:
        continue
    geom = shape(item.shape.__geo_interface__)
    minx, miny, maxx, maxy = geom.bounds
    x0 = max(0, int((minx + 180) // STEP))
    x1 = min(W, int((maxx + 180) // STEP) + 1)
    y0 = max(0, int((90 - maxy) // STEP))
    y1 = min(H, int((90 - miny) // STEP) + 1)
    mask = rasterize(
        [(geom, 1)],
        out_shape=(y1 - y0, x1 - x0),
        transform=from_origin(-180 + x0 * STEP, 90 - y0 * STEP, STEP, STEP),
        all_touched=True,
        dtype="uint8",
    )
    represented = int(((mask > 0) & (land[y0:y1, x0:x1] > 0)).sum())
    result.append(
        {
            "name": attrs["GEOUNIT"],
            "represented_source_land_cells": represented,
            "source_touched_cells": int(mask.sum()),
            "needs_resolution_review": represented == 0,
        }
    )
(proposal / "island-audit.json").write_text(
    json.dumps(
        {
            "scope": "Priority island-unit screen, not an exhaustive inhabited-island survey",
            "units": result,
        },
        indent=2,
    )
    + "\n"
)
print(json.dumps(result, indent=2))

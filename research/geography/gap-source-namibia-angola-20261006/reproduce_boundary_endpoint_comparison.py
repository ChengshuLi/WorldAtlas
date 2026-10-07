#!/usr/bin/env python3
"""Compare unchanged Namibia–Angola candidates with the 1928 Beacon 47 record."""

import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, shape


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "inputs" / "original-components.geojson"
TREATY = ROOT / "sources" / "uk-treaty-series-1931-ts-28-cmd-3896.pdf"

# Read from the English/Portuguese schedule to the Final Act: PDF page 13
# (printed page 14), Beacon No. 47. Units below are decimal degrees.
B47 = Point(18 + 25 / 60 + 6.2 / 3600, -(17 + 23 / 60 + 23.7 / 3600))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


raw = INPUT.read_bytes()
features = json.loads(raw)["features"]
rows = []
for feature in features:
    geometry = shape(feature["geometry"])
    min_lon, min_lat, max_lon, max_lat = geometry.bounds
    rows.append(
        {
            "component_id": feature["id"],
            "fragment_feature_sha256": feature["properties"]["fragment_bindings"][0]["feature_sha256"],
            "bounds_lon_lat": [min_lon, min_lat, max_lon, max_lat],
            "west_of_b47": max_lon < B47.x,
            "east_of_b47": min_lon > B47.x,
            "north_of_b47_latitude": min_lat > B47.y,
            "south_of_b47_latitude": max_lat < B47.y,
            "overlaps_b47_coordinate": geometry.covers(B47),
        }
    )

out = {
    "source": {
        "title": "UK Treaty Series No. 28 (1931), Cmd. 3896",
        "url": "https://treaties.fcdo.gov.uk/data/Library2/pdf/1931-TS0028.pdf",
        "sha256": sha256(TREATY.read_bytes()),
        "schedule_page": "PDF page 13 / printed page 14; Beacon 47 row",
        "beacon_47_coordinate": {"longitude": B47.x, "latitude": B47.y},
        "document_date": "Exchange of Notes: 1931-04-29; enclosed Final Act: 1928-09-23",
    },
    "input": {
        "path": "inputs/original-components.geojson",
        "bytes": len(raw),
        "sha256": sha256(raw),
        "component_count": len(features),
    },
    "method": "Read-only bounding-coordinate comparison against the scheduled Beacon 47 coordinate. Candidate geometries were not modified. Coordinate bounds establish whether each geometry lies east/west and north/south of the recorded endpoint only; they do not estimate the river centerline or a legal boundary location.",
    "limits": [
        "The 1928 Final Act describes the first-to-last beacon chain and places Beacon 47 at the Okavango/Cubango River, but this endpoint comparison does not reconstruct that full chain or the river boundary east of the beacon.",
        "The 1926 treaty’s river-midstream rule requires dated channel geometry to map a specific historical line. Current or Landsat-derived water classifications do not supply that historical bank or midstream line.",
        "This comparison describes relation to a historical record. It does not resolve present legal effect, territorial attribution, source authority, or processing cause.",
    ],
    "summary": {
        "components": len(rows),
        "east_of_b47_longitude": sum(row["east_of_b47"] for row in rows),
        "south_of_b47_latitude": sum(row["south_of_b47_latitude"] for row in rows),
        "covering_b47_coordinate": sum(row["overlaps_b47_coordinate"] for row in rows),
        "unresolved_relation_to_river_midstream": len(rows),
    },
    "components": rows,
}

output = ROOT / "1928-demarcation-endpoint-comparison.json"
output.write_text(json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n")
print(json.dumps(out["summary"], sort_keys=True))
print(f"bytes={output.stat().st_size} sha256={sha256(output.read_bytes())}")

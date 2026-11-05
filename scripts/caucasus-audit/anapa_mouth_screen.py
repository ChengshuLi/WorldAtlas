"""Screen selected and author lines against two public OSM map extracts.

Requires shapely and pyproj. Input geometries are coordinate-linear in WGS84;
reported intersection length is a WGS84 inverse-geodesic chord, not a proof
of drainage or a matched historical shoreline.
"""
import argparse
import json
import xml.etree.ElementTree as ET

from pyproj import Geod
from shapely.geometry import LineString, Polygon


def osm_way(path, way_id):
    root = ET.parse(path).getroot()
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat")))
             for n in root.findall("node")}
    matches = [w for w in root.findall("way") if w.get("id") == way_id]
    if len(matches) != 1:
        raise ValueError("missing or duplicate OSM way " + way_id)
    way = matches[0]
    points = [nodes[nd.get("ref")] for nd in way.findall("nd")]
    return way, points


def main():
    p = argparse.ArgumentParser()
    p.add_argument("selected")
    p.add_argument("author")
    p.add_argument("anapa_osm")
    p.add_argument("shingari_osm")
    a = p.parse_args()
    with open(a.selected, encoding="utf-8") as f:
        selected = LineString(json.load(f)["coordinates"][:11])
    with open(a.author, encoding="utf-8") as f:
        author = LineString(json.load(f)["features"][462]["geometry"]["coordinates"][-20:])
    checks = (
        ("selected_anapka_polygon", a.anapa_osm, "38631288", selected, Polygon),
        ("selected_anapa_coast", a.anapa_osm, "1067095312", selected, LineString),
        ("author_shingari_coast", a.shingari_osm, "396539058", author, LineString),
    )
    geod = Geod(ellps="WGS84")
    result = {}
    for label, filename, way_id, line, constructor in checks:
        way, coords = osm_way(filename, way_id)
        geom = constructor(coords)
        if not geom.is_valid:
            raise ValueError("invalid geometry: " + way_id)
        hit = line.intersection(geom)
        result[label] = {"way_id": way_id, "version": way.get("version"),
                         "timestamp": way.get("timestamp"), "intersection_wkt": hit.wkt,
                         "length_m": geod.geometry_length(hit)}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

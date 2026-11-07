"""Check source-line intersections with complete waterway ways in OSM extracts."""
import argparse
import json
import xml.etree.ElementTree as ET

from shapely.geometry import LineString


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("selected")
    parser.add_argument("author")
    parser.add_argument("extracts", nargs="+")
    args = parser.parse_args()
    with open(args.selected) as f:
        selected = LineString(json.load(f)["coordinates"][:21])
    with open(args.author) as f:
        author = LineString(json.load(f)["features"][462]["geometry"]["coordinates"][-65:])
    found = {}
    counted = set()
    for path in args.extracts:
        root = ET.parse(path).getroot()
        nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat")))
                 for n in root.findall("node")}
        for way in root.findall("way"):
            tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
            if tags.get("waterway") not in {"river", "stream", "canal", "ditch", "drain"}:
                continue
            refs = [n.get("ref") for n in way.findall("nd")]
            if len(refs) < 2 or any(ref not in nodes for ref in refs):
                continue
            identity = (way.get("id"), way.get("version"))
            counted.add(identity)
            line = LineString([nodes[ref] for ref in refs])
            hit_selected = line.intersection(selected)
            hit_author = line.intersection(author)
            if not hit_selected.is_empty or not hit_author.is_empty:
                found["/".join(identity)] = {"tags": tags,
                    "selected": hit_selected.wkt, "author": hit_author.wkt}
    print(json.dumps({"complete_way_versions": len(counted), "intersections": found},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

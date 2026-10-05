#!/usr/bin/env python3
"""Reproduce scoped identity/source assertions; does not assess legal boundaries."""
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
PKG = Path(__file__).resolve().parents[1]
IDS = [
    "gb:AGO:ADM2:16411231B22766430211667",
    "gb:AGO:ADM2:16411231B42954517222252",
    "gb:AGO:ADM2:16411231B63355352791940",
    "gb:AGO:ADM2:16411231B679187258105",
]
ROSTER = ["Cabinda", "Cacongo", "Buco Zau", "Belize", "Miconje", "Massabi", "Necuto", "Tando Zinze", "Liambo", "Ngoio"]

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    index = json.loads((ROOT / "data/world-index.json").read_text())
    hierarchy = json.loads((ROOT / "data/hierarchy.json").read_text())
    part = ROOT / "data/geography/part-29.json"
    collection = json.loads(part.read_text())
    actual = {f["id"]: f for f in collection["features"] if f.get("id") in IDS}
    assert set(actual) == set(IDS), "baseline does not contain exact four subjects"
    expected_names = dict(zip(IDS, ["Belize", "Cabinda", "Cacongo (Landana)", "Buco Zau"]))
    for id_, feature in actual.items():
        props = feature["properties"]
        assert props["name"] == expected_names[id_]
        assert props["parent_id"] == "framework:province:cabinda:fb67d098df5d"
        md = props["metadata"]
        assert md["source_id"] == "gb:AGO:ADM2" and md["reference_year"] == "2018"
        assert md["administrative_level"] == "ADM2" and md["source_role"] == "Municipality"
        assert md["license"] == "Creative Commons Attribution 3.0 Intergovernmental Organisations (CC BY 3.0 IGO)"
        assert feature["geometry"]["type"] == "Polygon"
    raw = PKG / "source/geoBoundaries-AGO-ADM2.geojson"
    original = json.loads(raw.read_text())
    source = {f["properties"]["shapeID"]: f for f in original["features"] if f.get("properties", {}).get("shapeID") in {x.rsplit(":",1)[1] for x in IDS}}
    assert len(original["features"]) == 161
    assert len(source) == 4 and set(source) == {x.rsplit(":",1)[1] for x in IDS}
    names = {"16411231B22766430211667":"Belize", "16411231B42954517222252":"Cabinda", "16411231B63355352791940":"Cacongo (Landana)", "16411231B679187258105":"Buco Zau"}
    assert {k:v["properties"]["shapeName"] for k,v in source.items()} == names
    crosswalk = json.loads((PKG / "findings/cabinda-municipality-crosswalk.json").read_text())
    assert crosswalk["current_statutory_roster"] == ROSTER
    assert len(crosswalk["legacy_crosswalk"]) == 4
    assert crosswalk["current_names_not_represented_as_separate_members_by_these_four_ids"] == ["Miconje", "Massabi", "Necuto", "Tando Zinze", "Liambo", "Ngoio"]
    assert all(x["footprint_persistence"] == "unresolved" for x in crosswalk["legacy_crosswalk"])
    assert index and hierarchy  # Read as pinned context; no geometry validation is inferred.
    print(json.dumps({"subjects":len(actual),"source_collection_features":len(original["features"]),"matched_legacy_source_ids":len(source),"statutory_municipality_names":len(ROSTER),"separate_names_absent_from_scoped_four":6,"source_geojson_sha256":sha(raw),"result":"identity and source-vintage checks passed; legal boundary correctness not tested"}, indent=2))

if __name__ == "__main__": main()

"""Run a byte-authenticated successor comparison for the two scoped subjects."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform

from authenticated import (EXPECTED_HELPER, HELPER_COMMIT, LEGACY_MODULES, ROOT,
    SUBJECTS, code_receipt, load_run, runtime_receipt)

IRN = "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/"
PAK = "coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/"
NATIVE = "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/originals/"
PROPOSAL = "coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/originals/"
RESEARCH = "research/geography/shared-seam-irn-pak-source-assessment-20261006/"
COMMIT = "39eff6e40063a4a22bfc4e6655487404c35c54c4"
RESULT_COMMIT = "39eff6e40063a4a22bfc4e6655487404c35c54c4"
SPECS = {
    "IRN": {"id": "26516999B17111396986996", "atlas": SUBJECTS[0],
        "native": NATIVE + "IRN-ADM2-native.geojson", "osm": PROPOSAL + "osm-saravan-relation-6555069-full.json",
        "relation": 6555069, "atlas_parent": "framework:province:sistan-and-baluchestan:ed7f0643a0ed",
        "parents": [(537693, "Sistan and Baluchestan Province", "Q939575", 6555069)]},
    "PAK": {"id": "60131773B78019453337506", "atlas": SUBJECTS[1],
        "native": NATIVE + "PAK-ADM2-native.geojson", "osm": NATIVE + "osm-panjgur-relation-3229274-full.json",
        "relation": 3229274, "atlas_parent": "framework:province:balochistan:c6b6e17e4739",
        "parents": [(16347101, "Makran Division", "Q3308229", 3229274), (357968, "Balochistan", "Q163239", 16347101)]},
}
HIERARCHY = "data/hierarchy.json"
PARTS = {"IRN": "data/geography/part-11.json", "PAK": "data/geography/part-17.json"}
PARENT_WAYS = PROPOSAL


def one(values, predicate, label):
    matches = [value for value in values if predicate(value)]
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one exact match, found {len(matches)}")
    return matches[0]


def parent_chain_matches(chain, spec):
    expected = [row[0] for row in spec["parents"]]
    actual = [row.get("relation_id") for row in chain]
    return actual == expected


def area_report(gb, osm):
    project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    a, b = transform(project, gb), transform(project, osm)
    if not a.is_valid or not b.is_valid or a.area <= 0 or b.area <= 0:
        raise ValueError("Invalid or zero-area projected source polygon")
    intersection, union = a.intersection(b).area, a.union(b).area
    return {
        "measurement_crs": "EPSG:6933", "unit": "m2", "geoboundaries_area": a.area,
        "osm_area": b.area, "intersection": intersection, "union": union,
        "gb_covered_by_osm": intersection / a.area, "osm_covered_by_gb": intersection / b.area,
        "iou": intersection / union, "symmetric_difference_fraction": (union-intersection)/union,
        "limit": "Vertex-projected equal-area overlay without densification or positional-accuracy model; discrepancy diagnostic only.",
    }


def run(vintage):
    manifest, base, modules, writer = load_run(vintage, ["result.json", "positive-control.json", "negative-control.json"])
    native = modules["native"]
    out = {"version": 1, "issue": 1341, "subjects": {},
           "producer_git_head": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
           "execution": {"baseline_format": 2, "captured_code_commit": COMMIT,
               "trusted_reader_helper": {"path": "scripts/evidence/immutable.py", "commit": HELPER_COMMIT, "sha256": EXPECTED_HELPER},
               "executed_modules": [{"module":name,"path":path,"commit":COMMIT,
                    "bytes":next(f["bytes"] for f in manifest["baseline"]["files"] if f["path"]==path and f["commit"]==COMMIT),
                    "sha256":next(f["sha256"] for f in manifest["baseline"]["files"] if f["path"]==path and f["commit"]==COMMIT)}
                    for name,path in LEGACY_MODULES.items()],
               "runtime": runtime_receipt(),
               "module_paths": [
                   "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py",
                   "scripts/evidence/immutable.py", "scripts/evidence/geometry.py"],
               "code": code_receipt([Path(__file__), Path(__file__).with_name("authenticated.py")]),
               "consumed_inputs": []}}
    hierarchy = base.json_for(HIERARCHY, COMMIT)
    parents = {item.get("id"): item for item in hierarchy}
    input_geojson = {}
    atlas = {}
    for country, part in PARTS.items():
        features = base.json_for(part, COMMIT)["features"]
        for feature in features:
            identity = feature.get("id", feature.get("properties", {}).get("id"))
            atlas[identity] = feature
        input_geojson[country] = base.json_for(SPECS[country]["native"], COMMIT)
    osm_data = {country: base.json_for(spec["osm"], COMMIT) for country, spec in SPECS.items()}
    way_docs = {}
    for way_id in (239441239, 239453665):
        path = PARENT_WAYS + f"osm-way-{way_id}-relations.json"
        way_docs[way_id] = base.json_for(path, COMMIT)
    claim_path = "research/geography/shared-seam-irn-pak-source-assessment-20261006/source-claims.json"
    claims = base.json_for(claim_path, RESULT_COMMIT)
    archived = base.json_for(RESEARCH + "results-2ed630f9/whole-geometry.json", RESULT_COMMIT)
    archived_by_country = archived["subjects"]
    out["archived_measurement_producer_commit"] = archived.get("producer_commit")
    receipts = [base.json_for(path, HELPER_COMMIT) for path in [
        PROPOSAL + "osm-saravan-relation-6555069-full-receipt.json",
        NATIVE + "osm-panjgur-relation-3229274-full-receipt.json"]]
    claim_by_country = {"IRN": claims["subjects"][0], "PAK": claims["subjects"][1]}
    for country, spec in SPECS.items():
        native_doc = input_geojson[country]
        feature = one(native_doc["features"], lambda f: f.get("properties", {}).get("shapeID") == spec["id"], spec["id"])
        if feature.get("geometry") is None:
            raise ValueError("Scoped native source feature has null geometry")
        exact_namesakes = [f for f in native_doc["features"]
            if str(f.get("properties", {}).get("shapeName", "")).casefold() == str(feature["properties"].get("shapeName", "")).casefold()]
        if len(exact_namesakes) != 1:
            raise ValueError("Exact name is not unique in the complete country source roster")
        atlas_feature = atlas.get(spec["atlas"])
        if not atlas_feature or atlas_feature.get("properties", {}).get("parent_id") != spec["atlas_parent"]:
            raise ValueError("Atlas identity or parent differs from the pinned historical record")
        relation_id = spec["relation"]
        osm_doc = osm_data[country]
        relation = one(osm_doc["elements"], lambda e: e.get("type") == "relation" and e.get("id") == relation_id, str(relation_id))
        osm_geometry, assembly = native.assemble_osm_boundary(osm_doc, relation_id)
        chain = []
        claim = claim_by_country[country]["crosswalk"]
        retained_chain = ([claim["osm_native_parent"]] if country == "IRN" else claim["osm_native_parent_chain"])
        expected_parent = None
        for parent_claim in retained_chain:
            chain.append({"relation_id": parent_claim["relation_id"], "name": parent_claim["name"],
                "wikidata": parent_claim["wikidata"], "evidence_basis": "pinned prior source-claims record",
                "contains_relation": spec["relation"] if expected_parent is None else expected_parent})
            expected_parent = parent_claim["relation_id"]
        if claim.get("osm_relation_id") != relation_id or claim.get("osm_wikidata") != relation.get("tags", {}).get("wikidata"):
            raise ValueError("Pinned prior crosswalk and captured OSM relation identity disagree")
        if not parent_chain_matches(retained_chain, spec):
            raise ValueError("Pinned prior native parent chain differs from declared relationship")
        dated = [e["timestamp"] for e in osm_doc["elements"] if e.get("type") in ("node", "way") and e.get("timestamp")]
        source_ids = {"IRN": "IRN-ADM2-26516999", "PAK": "PAK-ADM2-60131773"}
        metadata_path = NATIVE + ("IRN-geoBoundaries-IRN-ADM2-metaData.json" if country == "IRN" else "PAK-geoBoundaries-PAK-ADM2-metaData.json")
        metadata = base.json_for(metadata_path, COMMIT)
        osm_receipt_path = (PROPOSAL + "osm-saravan-relation-6555069-full-receipt.json" if country == "IRN" else NATIVE + "osm-panjgur-relation-3229274-full-receipt.json")
        osm_receipt = receipts[0 if country == "IRN" else 1]
        metric = area_report(shape(feature["geometry"]), osm_geometry)
        old_metric = archived_by_country[country]["whole_geometry"]
        reconciliation = {key: {"successor": metric[key], "archived": old_metric[key], "absolute_delta": abs(metric[key] - old_metric[key])}
            for key in ("iou", "gb_covered_by_osm", "osm_covered_by_gb")}
        if any(row["absolute_delta"] > 2e-12 for row in reconciliation.values()):
            raise ValueError("Successor measurement differs from the retained original ratio")
        out["subjects"][country] = {
            "subject_id": spec["atlas"],
            "geoBoundaries": {"shapeID": spec["id"], "shapeName": feature["properties"].get("shapeName"),
                "shapeGroup": feature["properties"].get("shapeGroup"), "shapeType": feature["properties"].get("shapeType"),
                "shapeISO": feature["properties"].get("shapeISO"), "other_properties": sorted(k for k in feature["properties"] if k not in {"shapeID", "shapeName", "shapeGroup", "shapeType", "shapeISO"}),
                "complete_country_features": len(native_doc["features"]), "unique_exact_namesakes": len(exact_namesakes),
                "boundary_year": metadata.get("boundaryYear"), "boundary_type": metadata.get("boundaryType"),
                "boundary_source": metadata.get("boundarySource"), "boundary_canonical": metadata.get("boundaryCanonical"),
                "boundary_license": metadata.get("boundaryLicense"), "license_detail": metadata.get("licenseDetail"),
                "license_source": metadata.get("licenseSource"), "boundary_source_url": metadata.get("boundarySourceURL"),
                "source_data_update_date": metadata.get("sourceDataUpdateDate"), "build_date": metadata.get("buildDate"),
                "boundary_observation_or_effective_date": "not established by retained metadata"},
            "osm": {"relation_id": relation_id, "name": relation.get("tags", {}).get("name"),
                "name_en": relation.get("tags", {}).get("name:en"), "aliases": {k:v for k,v in relation.get("tags", {}).items() if k.startswith("name:") or k in {"name", "alt_name", "official_name", "short_name"}},
                "admin_level": relation.get("tags", {}).get("admin_level"), "place": relation.get("tags", {}).get("place"),
                "wikidata": relation.get("tags", {}).get("wikidata"), "wikipedia": relation.get("tags", {}).get("wikipedia"),
                "relation_edit": relation.get("timestamp"), "member_edit_min": min(dated), "member_edit_max": max(dated),
                "retrieved_utc": osm_receipt.get("retrieved_utc"), "response_sha256": osm_receipt.get("sha256"),
                "dated_member_count": len(dated), "assembled_boundary_way_count": assembly["boundary_way_count"]},
            "atlas": {"id": spec["atlas"], "parent_id": spec["atlas_parent"], "parent_name": parents.get(spec["atlas_parent"], {}).get("name")},
            "osm_parent_chain": chain,
            "whole_geometry": metric, "archived_ratio_reconciliation": reconciliation,
            "neighboring_granularity": {"geoBoundaries": metadata.get("boundaryCanonical"), "osm_admin_level": relation.get("tags", {}).get("admin_level"),
                "limit": "Provider administrative labels/levels differ; no equivalence is inferred from counts or level numbers."},
            "crosswalk": "Authored research mapping candidate based on native IDs, names, country source, OSM tags/parent membership and complete-source uniqueness. Neither provider publishes a shared geoBoundaries-to-OSM key; this is not an official adjudication.",
            "source_identity": source_ids[country],
        }
    relevant_paths = [HIERARCHY, *PARTS.values(), *(x["native"] for x in SPECS.values()), *(x["osm"] for x in SPECS.values()),
        *(PARENT_WAYS + f"osm-way-{way_id}-relations.json" for way_id in way_docs), claim_path,
        RESEARCH + "results-2ed630f9/whole-geometry.json",
        NATIVE + "IRN-geoBoundaries-IRN-ADM2-metaData.json", NATIVE + "PAK-geoBoundaries-PAK-ADM2-metaData.json",
        NATIVE + "IRN-CITATION-AND-USE-geoBoundaries.txt", NATIVE + "PAK-CITATION-AND-USE-geoBoundaries.txt",
        NATIVE + "IRN-original-lfs-pointer.txt", NATIVE + "PAK-original-lfs-pointer.txt",
        NATIVE + "osm-panjgur-relation-3229274-full-receipt.json",
        PROPOSAL + "osm-saravan-relation-6555069-full-receipt.json",
        "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py",
        "scripts/evidence/immutable.py", "scripts/evidence/geometry.py", "scripts/ellipsoidal_area.py"]
    out["execution"]["consumed_inputs"] = [
        {"path": f["path"], "commit": f["commit"], "bytes": f["bytes"], "sha256": f["sha256"]}
        for f in manifest["baseline"]["files"] if f["path"] in relevant_paths
    ]
    out["source_provenance"] = {"geoBoundaries_release_commit": claims["source_facts"]["geoBoundaries_release_commit"],
        "geoBoundaries_source_vintages": {country:out["subjects"][country]["geoBoundaries"]["boundary_year"] for country in SPECS},
        "osm_relation_retrieval_utc": {"IRN": receipts[0].get("retrieved_utc"), "PAK": receipts[1].get("retrieved_utc")},
        "osm_relation_retrieval_hashes": {"IRN": receipts[0].get("sha256"), "PAK": receipts[1].get("sha256")},
        "attribution_and_license_notice_paths": [NATIVE + "IRN-CITATION-AND-USE-geoBoundaries.txt", NATIVE + "PAK-CITATION-AND-USE-geoBoundaries.txt"],
        "original_lfs_pointer_paths": [NATIVE + "IRN-original-lfs-pointer.txt", NATIVE + "PAK-original-lfs-pointer.txt"]}
    # Real-format positives and adversarial source/measurement negatives.
    positive = {"method_id": "authenticated-source-comparison", "kind": "positive-control", "outcome": "passed",
        "subjects": sorted(out["subjects"]), "both_positive_intersections": all(x["whole_geometry"]["intersection"] > 0 for x in out["subjects"].values()),
        "both_iou_in_unit_interval": all(0 < x["whole_geometry"]["iou"] <= 1 for x in out["subjects"].values()),
        "source_rows": {k: {"feature_count":v["geoBoundaries"]["complete_country_features"], "namesakes":v["geoBoundaries"]["unique_exact_namesakes"]} for k,v in out["subjects"].items()}}
    wrong_id_rejected = len([f for f in input_geojson["IRN"]["features"] if f.get("properties", {}).get("shapeID") == "26516999B00000000000000"]) == 0
    mutated_parent = {**claim_by_country["IRN"]["crosswalk"]["osm_native_parent"],
        "relation_id": claim_by_country["IRN"]["crosswalk"]["osm_native_parent"]["relation_id"] + 1}
    wrong_parent_rejected = not parent_chain_matches([mutated_parent], SPECS["IRN"])
    bad_measurement_rejected = False
    try:
        area_report(Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]), shape(input_geojson["IRN"]["features"][0]["geometry"]))
    except ValueError:
        bad_measurement_rejected = True
    negative = {"method_id": "authenticated-source-comparison", "kind": "negative-control", "outcome": "passed",
        "unknown_native_id_absent": wrong_id_rejected, "parent_chain_mismatch_rejected": wrong_parent_rejected,
        "self_intersecting_measurement_rejected": bad_measurement_rejected,
        "controls": ["Unknown native source ID cannot resolve", "Changed exact OSM parent relation ID is rejected", "Invalid self-intersecting polygon is rejected before overlay"]}
    if not all((positive["both_positive_intersections"], positive["both_iou_in_unit_interval"], wrong_id_rejected, wrong_parent_rejected, bad_measurement_rejected)):
        raise ValueError("Source or measurement controls failed")
    out["method"] = {"id": "projected-whole-feature-overlap", "kind": "measurement",
        "description": "Complete geoBoundaries feature and OSM relation boundary; original OSM node identity, projected from EPSG:4326 lon/lat to EPSG:6933 with pyproj always_xy, planar overlay, no densification.",
        "software": runtime_receipt(),
        "units": "square metres and area fractions", "limit": "Diagnostic disagreement only; no positional-accuracy model, legal authority or water classification."}
    records = writer.publish({"result.json": out, "positive-control.json": positive, "negative-control.json": negative})
    print(json.dumps({"vintage": vintage, "records": records, "metrics": {k:v["whole_geometry"] for k,v in out["subjects"].items()}, "controls": {"positive":positive,"negative":negative}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    run(parser.parse_args().vintage)

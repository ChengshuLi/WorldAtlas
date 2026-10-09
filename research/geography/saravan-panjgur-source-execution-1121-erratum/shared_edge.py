"""Authenticate exact retained OSM component ways through captured input bytes."""
import argparse
import copy
import json

from authenticated import EXPECTED_HELPER, HELPER_COMMIT, LEGACY_COMMIT, LEGACY_MODULES, ROOT, code_receipt, load_run, runtime_receipt

COMMIT = "39eff6e40063a4a22bfc4e6655487404c35c54c4"
IRN = "coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/originals/osm-saravan-relation-6555069-full.json"
PAK = "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/originals/osm-panjgur-relation-3229274-full.json"
WAYS_DIR = "coordination/engineering/iran-pakistan-joint-proposal-971-20261005-local10/originals/"
WAYS = (239441239, 239453665)
COUNTIES = (6555069, 3229274)
NATIONAL_PARENTS = (304938, 307573)


def element_map(document):
    values = {}
    for element in document["elements"]:
        key = (element.get("type"), element.get("id"))
        if key in values:
            raise ValueError("Duplicate OSM element identity in complete response")
        values[key] = element
    return values


def has_outer(relation, way_id):
    return any(member.get("type") == "way" and member.get("ref") == way_id and member.get("role") == "outer"
        for member in relation.get("members", []))


def reconcile(documents, way_docs, ways=WAYS, omit_parent=None):
    left, right = (element_map(documents[0]), element_map(documents[1]))
    rows = []
    for relation_id, data in zip(COUNTIES, (left, right)):
        relation = data.get(("relation", relation_id))
        if relation is None:
            raise ValueError("Exact county relation missing from captured complete response")
        for way_id in ways:
            if not has_outer(relation, way_id):
                raise ValueError(f"County relation {relation_id} does not contain shared outer way {way_id}")
    for way_id in ways:
        a, b = left.get(("way", way_id)), right.get(("way", way_id))
        if not a or not b or a != b or a.get("nodes") != b.get("nodes"):
            raise ValueError(f"Complete county responses disagree about shared way {way_id}")
        if a.get("tags", {}).get("boundary") == "administrative" and len(a.get("nodes", [])) < 2:
            raise ValueError("Administrative component way has an incomplete node sequence")
        for node_id in a["nodes"]:
            x, y = left.get(("node", node_id)), right.get(("node", node_id))
            if not x or not y or (x.get("lon"), x.get("lat")) != (y.get("lon"), y.get("lat")):
                raise ValueError(f"Shared node coordinates differ or are absent: {node_id}")
        member_pairs = []
        way_response = way_docs[WAYS.index(way_id)]
        source = element_map(way_response)
        for parent_id in NATIONAL_PARENTS:
            parent = source.get(("relation", parent_id))
            members = parent.get("members", []) if parent else []
            if omit_parent == (way_id, parent_id):
                members = [m for m in members if not (m.get("type") == "way" and m.get("ref") == way_id)]
            if not any(m.get("type") == "way" and m.get("ref") == way_id and m.get("role") == "outer" for m in members):
                raise ValueError(f"National parent relation {parent_id} lacks exact outer way {way_id}")
            member_pairs.append(parent_id)
        rows.append({"way_id": way_id, "node_count": len(a["nodes"]), "same_complete_way_object": True,
            "same_ordered_node_sequence": True, "same_node_coordinates": True,
            "outer_in_counties": list(COUNTIES), "outer_in_national_relations": member_pairs})
    return rows


def run(vintage):
    manifest, base, modules, writer = load_run(vintage, ["result.json", "positive-control.json", "negative-control.json"])
    native = modules["native"]
    documents = [base.json_for(IRN, COMMIT), base.json_for(PAK, COMMIT)]
    # Assembly exercises the actual historical node-identity ring constructor
    # from captured source bytes for each true scoped relation.
    assemblies = [native.assemble_osm_boundary(documents[0], COUNTIES[0]),
        native.assemble_osm_boundary(documents[1], COUNTIES[1])]
    way_docs = [base.json_for(WAYS_DIR + f"osm-way-{w}-relations.json", COMMIT) for w in WAYS]
    rows = reconcile(documents, way_docs)
    correct_way_rejected = False
    try:
        reconcile(documents, way_docs, ways=(WAYS[0], 999999999))
    except ValueError:
        correct_way_rejected = True
    parent_omission_rejected = False
    try:
        reconcile(documents, way_docs, omit_parent=(WAYS[0], NATIONAL_PARENTS[0]))
    except ValueError:
        parent_omission_rejected = True
    shifted = copy.deepcopy(documents)
    index = element_map(shifted[1])
    node_id = index[("way", WAYS[0])]["nodes"][0]
    index[("node", node_id)]["lon"] += 0.001
    changed_node_rejected = False
    try:
        reconcile(shifted, way_docs)
    except ValueError:
        changed_node_rejected = True
    positive = {"method_id": "osm-shared-edge-source-membership", "kind": "positive-control", "outcome": "passed",
        "ways": rows, "both_actual_relations_assembled": len(assemblies) == 2,
        "assembly_way_counts": [x[1]["boundary_way_count"] for x in assemblies]}
    negative = {"method_id": "osm-shared-edge-source-membership", "kind": "negative-control", "outcome": "passed",
        "unknown_way_rejected": correct_way_rejected, "missing_national_parent_member_rejected": parent_omission_rejected,
        "changed_shared_node_coordinate_rejected": changed_node_rejected,
        "case": "A required way identity, node coordinate or national outer membership is changed in an actual complete-response fixture."}
    if not correct_way_rejected or not parent_omission_rejected or not changed_node_rejected or len(rows) != 2:
        raise ValueError("Shared-edge source controls failed")
    result = {"version": 1, "issue": 1341, "method_id": "osm-shared-edge-source-membership",
        "execution": {"captured_code_commit": COMMIT,
            "trusted_reader_helper": {"path": "scripts/evidence/immutable.py", "commit": HELPER_COMMIT, "sha256": EXPECTED_HELPER},
            "executed_modules": [{"module":name,"path":path,"commit":LEGACY_COMMIT,
                "bytes":next(f["bytes"] for f in manifest["baseline"]["files"] if f["path"]==path and f["commit"]==LEGACY_COMMIT),
                "sha256":next(f["sha256"] for f in manifest["baseline"]["files"] if f["path"]==path and f["commit"]==LEGACY_COMMIT)}
                for name,path in LEGACY_MODULES.items()],
            "runtime": runtime_receipt(),
            "code": code_receipt([__file__, __file__.replace("shared_edge.py", "authenticated.py")]),
            "input_files": [{"path": path, "commit": commit, "sha256": row["sha256"], "bytes": row["bytes"]}
                for path, commit in [(IRN, COMMIT), (PAK, COMMIT),
                    *((WAYS_DIR + f"osm-way-{w}-relations.json", COMMIT) for w in WAYS)]
                for row in manifest["baseline"]["files"] if row["path"] == path and row["commit"] == commit]},
        "shared_component_ways": rows,
        "limit": "Exact node identity and membership establish topology in these retrieved OSM records only. No legal sovereignty, official boundary, effective date, positional accuracy, physical-water or historical claim is established."}
    records = writer.publish({"result.json": result, "positive-control.json": positive, "negative-control.json": negative})
    print(json.dumps({"vintage": vintage, "records": records, "ways": rows, "controls": {"positive": positive, "negative": negative}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", required=True)
    run(parser.parse_args().vintage)

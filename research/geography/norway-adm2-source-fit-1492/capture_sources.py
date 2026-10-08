#!/usr/bin/env python3
"""Admit current official source bytes and exact 15 source-comparison records."""
import gzip
import hashlib
import json
import os
import resource
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/norway-adm2-source-fit-1492/"
COMMIT = "088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
BASELINE_SHA = "45d4356a46beddea43bfbd20231e0bf3671aa349643de29d0fa088ed5fbf5713"
VINTAGE = "official-source-capture-20261008"
OUTPUTS = ["adm1-api.json", "adm2-api.json", "adm1-simplified.geojson",
           "adm2-simplified.geojson", "selected-source-rows.json"]
API_URLS = {
    "adm1": "https://www.geoboundaries.org/api/current/gbOpen/NOR/ADM1/",
    "adm2": "https://www.geoboundaries.org/api/current/gbOpen/NOR/ADM2/",
}
EXPECTED = {
    "adm1": {"bytes": 3216652, "sha256": "a24bd867e42c8f2d7bdd07e723594f2d55736d50de8cf1e92062ae443a0f0f72", "features": 11},
    "adm2": {"bytes": 4724258, "sha256": "ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e", "features": 431},
}
FAMILY = "gap-source-batch:3f21c83705d3cef5988b1295"
ISSUE_SELECTED = [
    "physical-component:153efbdb9c28eaba9ef8c4c834577ea44c875c2412493c2581530c2d9c7085f1",
    "physical-component:1f453e7a436aa2f6a68edfb7433d3d1ec05c72b37ba78fac9b3d2542bc085efb",
    "physical-component:1f5426f5180aa4f5b7fd9991b5ae4816d56cb642c31d0937a4977da516f28f2b",
    "physical-component:4f57d0af8235d8f547395c5d94bfeeb57e8e11168f65b7a566407213d17f1e5c",
    "physical-component:764b247eb21da38adac0b925bededbbb4dccaefa4b52b16976f20543a7ac3384",
    "physical-component:7bad7bdf9b1203fe6c676eb2efde10b09ce394ad7d6d554eb557709d7704df35",
    "physical-component:8fb9f3f0d7df1c96ac452792fd4a9dbc7a45a576437550dd5b198424ceca14a9",
    "physical-component:a82c3dc9980bf083cf15fb0edf1b98301259afb93761549c97ec57d73a41c5ce",
    "physical-component:a92cac9c4c3d3a91286eca0e4890becd63441647c7fe7c4cdcc5e1aa167d4803",
    "physical-component:b6ba064b4525f0c75459a8d1aa05c25e9740cc46b9964f96983d61d6a9b4253a",
    "physical-component:cc11d3c9c7f82d8c9073539568d8af915da17e21904a60a75d49eb5d2e63ae94",
    "physical-component:dc92c796890cece117d3a70e1422fc2682a46caf3db64f06b2935b46e31b7a9f",
    "physical-component:e0bd74d0efc769aa5b98ba28ca22d0b37692f3387d344e32c14516b0fe062904",
    "physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40",
    "physical-component:f082e1ba3a2d1267b17f803511ec164c9c8649fd3fb9cc2bc752a4c833659508",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stage_file(relative):
    root = ROOT / OWNED / "vintages"
    path = root / relative
    return path


def read_stage(name, expected_sha):
    path = stage_file(name)
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError("Stage input drift: " + str(path))
    receipt = json.loads((path.parent / "publication.json").read_bytes())
    desc = next((x for x in receipt.get("outputs", []) if x.get("path") == str(path.relative_to(ROOT))), None)
    if not desc or desc.get("bytes") != len(raw) or desc.get("sha256") != sha(raw):
        raise ValueError("Stage input is not in its immutable completion receipt")
    return raw


def iter_fragment_records(chunks):
    decoder = json.JSONDecoder()
    buffer = ""
    for path, chunk in chunks:
        buffer += chunk
        index = 0
        while index < len(buffer):
            while index < len(buffer) and (buffer[index].isspace() or buffer[index] in "[],"):
                index += 1
            if index >= len(buffer):
                buffer = ""
                break
            try:
                value, end = decoder.raw_decode(buffer, index)
            except json.JSONDecodeError as exc:
                if len(buffer) - exc.pos > 8 * 1024 * 1024:
                    raise
                buffer = buffer[index:]
                break
            index = end
            if isinstance(value, list):
                for item in value:
                    yield path, item
            else:
                yield path, value
        else:
            buffer = buffer[index:]
    if buffer.strip(" \t\r\n[],"):
        raise ValueError("Incomplete trailing source-comparison JSON")


def get_bytes(url, max_bytes):
    req = urllib.request.Request(url, headers={"User-Agent": "WorldAtlas evidence capture; research-only"})
    with urllib.request.urlopen(req, timeout=45) as response:
        raw = response.read(max_bytes + 1)
        headers = {k: v for k, v in response.headers.items()}
        final_url = response.geturl()
    if len(raw) > max_bytes:
        raise ValueError("Remote source exceeds its admitted file reserve: " + url)
    return raw, {"requested_url": url, "final_url": final_url, "response_headers": headers}


def main():
    started = time.monotonic()
    script_hash = sha(Path(__file__).read_bytes())
    admission_raw = (ROOT / OWNED / "vintages/baseline-20261008/baseline-admission.json").read_bytes()
    if sha(admission_raw) != BASELINE_SHA:
        raise SystemExit("Baseline admission changed")
    admission = json.loads(admission_raw)
    sys.path.insert(0, str(ROOT / "scripts"))
    from evidence.immutable import Baseline, NewVintage, canonical_json, MAX_FILE_BYTES

    baseline = Baseline(ROOT, COMMIT, admission["baseline_files"])
    writer = NewVintage(baseline, OWNED, VINTAGE, OUTPUTS)
    reserves = {"adm1-api.json": 256 * 1024, "adm2-api.json": 256 * 1024,
                "adm1-simplified.geojson": 8 * 1024 * 1024,
                "adm2-simplified.geojson": 8 * 1024 * 1024,
                "selected-source-rows.json": 16 * 1024 * 1024,
                "publication.json": 4096}
    for name, size in reserves.items():
        baseline.admit("reserved-output:" + name, size)

    family_raw = read_stage("family-scope-20261008/family-scope.json",
                            "63c6820d5091c7395c4de6396a6757b3c0921aee50dffb47de0c700611f90304")
    correction_raw = read_stage("issue-scope-correction-20261008/correction.json",
                                "17125f50d3e7f4de69677a7fc7f8c798c9b3ee162f7a0354eda2a19e8c400f0f")
    baseline.admit("captured-input:family-scope.json", len(family_raw))
    baseline.admit("captured-input:issue-correction.json", len(correction_raw))
    family_scope = json.loads(family_raw)["scope"]
    correction = json.loads(correction_raw)
    if family_scope["family_id"] != FAMILY or family_scope["complete_member_count"] != 400 or family_scope["complete_positive_length_neighbor_count"] != 36:
        raise SystemExit("Complete family source scope drifted")
    if correction["correction"]["new_id"] != "physical-component:eb2b6c25d1a2b8ead2bcb67f7e0423b5f1cc5609ac3f600bb98cd6d5cb11db40":
        raise SystemExit("Issue correction receipt does not point to the pinned source candidate")
    if correction["correction"]["occurrences_replaced"] != 2:
        raise SystemExit("Issue correction count changed")

    # The family scope includes the exact pinned route family record; the source
    # comparison corpus supplies detailed feature intersection/contact rows.
    selected = family_scope["family_record"]["source_fitness_required_compatible_land_component_ids"]
    if len(selected) != 15 or len(set(selected)) != 15 or set(selected) != set(ISSUE_SELECTED):
        raise SystemExit("Corrected issue roster and pinned complete-family route disagree")

    phase_start = time.monotonic()
    disk_before = shutil.disk_usage(ROOT).free
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_before = subprocess.check_output(["memory_pressure"], text=True)

    api_raw, api_receipts, product_raw, product_receipts = {}, {}, {}, {}
    retrieval_time = datetime.now(timezone.utc).isoformat()
    for tier in ("adm1", "adm2"):
        api_raw[tier], api_receipts[tier] = get_bytes(API_URLS[tier], 256 * 1024)
        baseline.admit("current-source-api:" + tier, len(api_raw[tier]))
        metadata = json.loads(api_raw[tier])
        if metadata.get("boundaryISO") != "NOR" or metadata.get("boundaryType") != tier.upper():
            raise SystemExit("Current official metadata has the wrong geography key")
        url = metadata.get("simplifiedGeometryGeoJSON")
        if not isinstance(url, str) or not url:
            raise SystemExit("Current API metadata omitted its simplified product URL")
        product_raw[tier], product_receipts[tier] = get_bytes(url, 8 * 1024 * 1024)
        baseline.admit("current-source-product:" + tier, len(product_raw[tier]))
        if sha(product_raw[tier]) != EXPECTED[tier]["sha256"] or len(product_raw[tier]) != EXPECTED[tier]["bytes"]:
            raise SystemExit("Current simplified source bytes differ from the issue's pinned product")
        parsed = json.loads(product_raw[tier])
        if parsed.get("type") != "FeatureCollection" or len(parsed.get("features", [])) != EXPECTED[tier]["features"]:
            raise SystemExit("Current simplified source feature count/type differs from the pinned product")

    # Authenticate and decode the complete component/source-comparison corpus.
    target_set = set(selected)
    found = {}
    component_prefix = "coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-"
    def chunks():
        for i in range(12):
            path = f"{component_prefix}{i:03d}.json.gz"
            compressed = baseline.pinned_bytes(path)
            declared = struct.unpack("<I", compressed[-4:])[0]
            baseline.admit(path + ":decoded", declared)
            decoded = gzip.decompress(compressed)
            if len(decoded) != declared:
                raise ValueError("Source-comparison shard decoded size changed")
            yield path, decoded.decode("utf-8")

    scanned_records = 0
    for path, record in iter_fragment_records(chunks()):
        scanned_records += 1
        if not isinstance(record, dict) or record.get("component") not in target_set:
            continue
        if record["component"] in found:
            raise SystemExit("Duplicate selected component source record")
        if record.get("family") != FAMILY:
            raise SystemExit("Selected source row belongs to a different family")
        found[record["component"]] = {"path": path, "record": record}
    if set(found) != target_set:
        raise SystemExit("Missing selected component source rows: " + repr(sorted(target_set-set(found))))

    # Rebind all 15 unique source IDs and their exact feature-index/geometry
    # contacts to the current byte-identical official product.
    features = json.loads(product_raw["adm2"])["features"]
    by_shape = {}
    for index, feature in enumerate(features):
        props = feature.get("properties", {})
        shape_id = props.get("shapeID") or props.get("shapeGroup")
        if shape_id:
            by_shape.setdefault(shape_id, []).append((index, feature))
    product_bindings = {}
    for component in selected:
        row = found[component]["record"]
        unique_subject = row.get("uniquely_covering_compatible_recorded_subject", {})
        unique_subject_id = unique_subject.get("id") if isinstance(unique_subject, dict) else None
        positive = row.get("positive_area_feature_ids")
        if not unique_subject_id or not isinstance(positive, list) or len(positive) != 1:
            raise SystemExit("Selected source row lacks one unique positive-area recorded subject")
        witnesses = row.get("feature_intersections")
        if not isinstance(witnesses, list) or not witnesses:
            raise SystemExit("Selected source row lacks complete source-feature contact rows")
        contact_subjects = set()
        for contact in witnesses:
            binding = contact.get("binding", {})
            shape_id = binding.get("shapeID")
            source_id = binding.get("source_id")
            if source_id != "gb:NOR:ADM2" or not shape_id:
                raise SystemExit("Source contact lacks a stable product feature binding")
            candidates = by_shape.get(shape_id, [])
            if len(candidates) != 1:
                raise SystemExit("Source shapeID does not resolve uniquely in the current full product")
            product_index, source_feature = candidates[0]
            source_sha = sha(canonical_json(source_feature))
            # Whole-feature raw-byte hashes are part of the archived producer's
            # binding; this reconstructed canonical record hash is a new receipt
            # field and is never presented as the original raw-byte digest.
            if binding.get("feature_index") != product_index:
                raise SystemExit("Current product feature order differs from the recorded binding")
            feature_subjects = [x.get("id") for x in binding.get("recorded_stable_subjects", [])]
            if len(feature_subjects) != 1:
                raise SystemExit("Source contact does not have one stable recorded subject")
            contact_subjects.add(feature_subjects[0])
            product_bindings.setdefault(shape_id, {"feature_index": product_index,
                "canonical_feature_sha256": source_sha,
                "recorded_stable_subject_ids": feature_subjects,
                "archived_original_geometry_sha256": binding.get("geometry_sha256"),
                "source_component_contacts": []})["source_component_contacts"].append({
                    "component_id": component,
                    "intersection_geometry_sha256": contact.get("intersection", {}).get("geometry_sha256"),
                    "intersection_planar_area_coordinate_units_squared": contact.get("intersection", {}).get("planar_area_coordinate_units_squared"),
                    "intersection_is_empty": contact.get("intersection", {}).get("is_empty")})
        positive_row = positive[0]
        if (positive_row.get("source_id") != "gb:NOR:ADM2"
                or positive_row.get("recorded_stable_subject_ids") != [unique_subject_id]
                or positive_row.get("shapeID") not in by_shape
                or len(by_shape[positive_row["shapeID"]]) != 1):
            raise SystemExit("Unique positive-area witness disagrees with the recorded compatible source subject")
        positive_index, positive_feature = by_shape[positive_row["shapeID"]][0]
        if positive_index != positive_row.get("feature_index"):
            raise SystemExit("Unique positive-area source index differs from the official product")
        if unique_subject_id not in contact_subjects:
            raise SystemExit("Recorded unique source subject is not among the preserved contact witnesses")
        row["revalidated_unique_recorded_subject_ids"] = [unique_subject_id]
        row["revalidated_source_feature_contact_subject_ids"] = sorted(contact_subjects)
        row["revalidated_unique_positive_witness"] = {
            "shapeID": positive_row["shapeID"], "feature_index": positive_index,
            "canonical_feature_sha256": sha(canonical_json(positive_feature))}

    source_result = {
        "version": 1,
        "status": "official-current-sources-and-selected-source-rows-captured",
        "issue": 1492,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "retrieval_started_at": retrieval_time,
        "baseline": {"commit": COMMIT, "admission_sha256": BASELINE_SHA,
                     "files": len(admission["baseline_files"]),
                     "pinned_file_bytes": admission["pinned_file_bytes"]},
        "family_context": {"family_id": FAMILY, "members": family_scope["complete_component_ids"],
                           "neighbors": family_scope["complete_positive_length_neighbor_ids"],
                           "selected_count": len(selected),
                           "selected_component_ids": selected,
                           "scope_artifact_sha256": sha(family_raw)},
        "issue_correction": correction,
        "source_metadata": {tier: {"api_url": API_URLS[tier],
            "api_capture": api_receipts[tier], "api_bytes": len(api_raw[tier]),
            "api_sha256": sha(api_raw[tier]),
            "product_capture": product_receipts[tier],
            "product_bytes": len(product_raw[tier]),
            "product_sha256": sha(product_raw[tier]),
            "matches_pinned_issue_product": True,
            "expected_bytes": EXPECTED[tier]["bytes"],
            "expected_sha256": EXPECTED[tier]["sha256"],
            "feature_count": EXPECTED[tier]["features"],
            "represented_year": json.loads(api_raw[tier]).get("boundaryYearRepresented"),
            "license": json.loads(api_raw[tier]).get("boundaryLicense"),
            "source": json.loads(api_raw[tier]).get("boundarySource")}
            for tier in ("adm1", "adm2")},
        "source_feature_bindings": product_bindings,
        "source_component_rows": [found[c] for c in selected],
        "corpus_scan": {"shards": 12, "records_scanned": scanned_records,
                         "decoded_bytes": sum(baseline.consumed.get(f"{component_prefix}{i:03d}.json.gz:decoded",0) for i in range(12))},
        "producer": {"path": str(Path(__file__).relative_to(ROOT)), "sha256": script_hash,
                     "python": sys.version, "elapsed_seconds": time.monotonic()-started},
        "admission": {"reserved_output_bytes": sum(reserves.values()),
                      "phase_bytes_before_publish": sum(baseline.consumed.values()),
                      "phase_limit_bytes": baseline.max_phase_bytes,
                      "disk_free_before_bytes": disk_before,
                      "disk_free_after_bytes": shutil.disk_usage(ROOT).free,
                      "physical_memory_bytes": os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"),
                      "memory_pressure_before": memory_before,
                      "process_max_rss_before_bytes": rss_before,
                      "process_max_rss_after_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      "phase_elapsed_seconds": time.monotonic()-phase_start},
        "limits": ["The archived source-comparison row is a derived overlay diagnostic; physical-component target geometries are captured separately from the complete original global physical-comparison result corpus.",
                   "Current API metadata describes 2013 ADM2 and 2022 ADM1 products; it does not establish present accuracy or any ownership/history/water assertion.",
                   "No repair, tolerance, snapping, buffering or geometry normalization is performed in this source capture stage."]
    }
    outputs = {"adm1-api.json": api_raw["adm1"], "adm2-api.json": api_raw["adm2"],
               "adm1-simplified.geojson": product_raw["adm1"], "adm2-simplified.geojson": product_raw["adm2"],
               "selected-source-rows.json": canonical_json(source_result)}
    for name, raw in outputs.items():
        if len(raw) > reserves[name] or len(raw) > MAX_FILE_BYTES:
            raise SystemExit("Output exceeds its pre-read output reserve: " + name)
    if sha(Path(__file__).read_bytes()) != script_hash:
        raise SystemExit("Producer code changed during run")
    records = writer.publish_bytes(outputs)
    print(json.dumps({"status": source_result["status"], "selected_records": len(found),
                      "source_feature_bindings": len(product_bindings), "outputs": records,
                      "phase_bytes": sum(baseline.consumed.values())}, indent=2))


if __name__ == "__main__":
    main()

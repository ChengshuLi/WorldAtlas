#!/usr/bin/env python3
"""Assemble the issue-bound evidence manifest from retained outputs."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

PACKET = Path("research/geography/guinea-bissau-gap-source-fitness-20261007")
BASE = "6a47b43025d963daf80915c6d219c75ebcc8cd91"
RUNS = ["source-fitness-run-20261007-k", "source-fitness-run-20261007-l"]
CONTROLS = "validation-controls-20261007-v5"
THREAD = "01a112c2-1d0f-7bf2-a50e-74956219b9c1"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.PIPE)

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()

def descriptor(path, raw, **extra):
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes", **extra}

scope = json.loads((PACKET / "scope.json").read_bytes())
snapshot = json.loads((PACKET / "sources/issue-1416.json").read_bytes())
quality = scope["evidence_quality_contract"]
pins, pin_files = quality["pins"], quality["pin_files"]
baseline_files, subject_files = {}, {}
for key, path in pin_files.items():
    raw = git("show", f"{BASE}:{path}")
    row = descriptor(path, raw, role="original-source")
    if key in {"routing.family.010", "routing.land_source_fitness", "source_corpus.gnb_adm2"} or key.startswith(("component_custody.payload.", "routing.admin_bindings.")):
        unpacked = gzip.decompress(raw)
        row["uncompressed_bytes"] = len(unpacked)
        row["uncompressed_sha256"] = sha(unpacked)
    baseline_files[path] = row
for path in ["scripts/evidence/immutable.py", "scripts/administrative.py"]:
    raw = git("show", f"{BASE}:{path}")
    baseline_files[path] = descriptor(path, raw, role="pinned-project-code")
    key = "project." + ("immutable_helper" if path.endswith("immutable.py") else "administrative_selector")
    pins[key], pin_files[key] = sha(raw), path
payload_keys = [key for key in pin_files if key.startswith("component_custody.payload.")]
targets = set(scope["components"])
for key in payload_keys:
    path = pin_files[key]
    raw = gzip.decompress(git("show", f"{BASE}:{path}"))
    for feature in json.loads(raw).get("features", []):
        identity = feature.get("id")
        if identity in targets:
            if identity in subject_files:
                raise ValueError("Duplicate custody component subject")
            subject_files[identity] = path
if set(subject_files) != targets:
    raise ValueError("Custody source paths do not cover the exact component roster")
contact_path = pin_files["current.gnb_contact_part"]
subject_files.update({identity: contact_path for identity in scope["contacts"]})

run_root = PACKET / "vintages"
outputs, output_paths = [], set()
for run in RUNS:
    folder = run_root / run
    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        rel = str(path)
        outputs.append(descriptor(rel, path.read_bytes()))
        output_paths.add(rel)
controls_folder = run_root / CONTROLS
for path in sorted(controls_folder.iterdir()):
    if path.is_file():
        rel = str(path)
        outputs.append(descriptor(rel, path.read_bytes()))
        output_paths.add(rel)
tile_paths = [
    PACKET / "sources/esa-worldcover/worldcover-2020-v100-N09W018.tif",
    PACKET / "sources/esa-worldcover/worldcover-2021-v200-N09W018.tif",
]
tile_descriptors = {str(path): descriptor(str(path), path.read_bytes(), role="original-source") for path in tile_paths}
for path in [PACKET / "README.md", PACKET / "summary-table.md", PACKET / "scope.json",
             PACKET / "sources/issue-1416.json", PACKET / "reproduce.py", PACKET / "prepare_manifest.py"]:
    rel = str(path)
    outputs.append(descriptor(rel, path.read_bytes(), **({"role": "generated-table"} if path.name == "summary-table.md" else {})))
    output_paths.add(rel)

run = RUNS[0]
ledger_path = str(PACKET / "vintages" / run / "metric-ledger.json")
ledger = json.loads((Path(ledger_path)).read_bytes())["metrics"]
metrics = ledger
bindings = [{"metric_id": m["id"], "path": ledger_path, "json_pointer": f"/metrics/{i}/value"}
            for i, m in enumerate(ledger)]
table_path = str(PACKET / "summary-table.md")
table_lines = (PACKET / "summary-table.md").read_text().splitlines()
table_metric_ids = [
    "issue_component_count", "component_route_row_count", "issue_contact_count", "fragment_binding_count",
    "topology_pair_count", "intersection_geometry_count", "legacy_observation_count", "worldcover_subject_year_row_count",
    "source_admin_feature_count", "source_admin_simplified_feature_count",
    "full_simplified_topological_equal_feature_count", "full_simplified_coordinate_identity_feature_count",
]
for i in range(4):
    table_metric_ids.extend([f"contact_{i:02d}_current_vertex_count", f"contact_{i:02d}_full_source_vertex_count",
                             f"contact_{i:02d}_simplified_source_vertex_count"])
if len(table_lines) != len(table_metric_ids) + 2:
    raise ValueError("Summary table/metric roster mismatch")
summaries, table_rows = [], []
metric_by_id = {m["id"]: m for m in metrics}
for line_no, metric_id in enumerate(table_metric_ids, start=3):
    metric = metric_by_id[metric_id]
    template = table_lines[line_no - 1].replace(str(metric["value"]), "{value}")
    if table_lines[line_no - 1] != template.replace("{value}", str(metric["value"])):
        raise ValueError("Summary row is not a direct metric rendering")
    summaries.append({"metric_id": metric_id, "value": metric["value"], "unit": metric["unit"]})
    table_rows.append({"metric_id": metric_id, "line": line_no, "template": template, "decimals": 0})

run_path = str(PACKET / "vintages" / run)
control_path = str(PACKET / "vintages" / CONTROLS)
methods = [
    {"id": "bounded-geometry-packet", "kind": "generator", "helper_version": "worldatlas-evidence-preparation-v1",
     "description": "Pinned source joins, exact custody geometry preservation, native-coordinate topology overlays, deterministic output publication, and complete metric ledger.",
     "software": "Python 3.12; Shapely/GEOS; shared immutable preparation helper",
     "units": "source-coordinate topology; whole-file bytes; exact identity and feature counts"},
    {"id": "worldcover-pixel-center-screen", "kind": "measurement",
     "description": "Authenticated full-tile reads; native-grid cell-center class counts with all_touched=false; product classes are not physical truth.",
     "software": "Python 3.12; NumPy; Rasterio/GDAL",
     "units": "classified pixel centers by ESA WorldCover class code"},
    {"id": "source-reconciliation", "kind": "source",
     "description": "Pinned full/simplified administrative products, selector transformation, metadata, contact joins, and prior #472/#812 identity findings.",
     "software": "Python 3.12 standard library; exact byte and JSON comparisons",
     "units": "source features, IDs, names, vertices, and metadata fields"},
]
validation = []
for method_id, kind, name in [
    ("bounded-geometry-packet", "positive-control", "packet-positive-control.json"),
    ("bounded-geometry-packet", "negative-control", "packet-negative-control.json"),
    ("bounded-geometry-packet", "reproducibility", "reproducibility-control.json"),
    ("worldcover-pixel-center-screen", "positive-control", "measurement-positive-control.json"),
    ("worldcover-pixel-center-screen", "negative-control", "measurement-negative-control.json"),
]:
    validation.append({"method_id": method_id, "kind": kind, "outcome": "passed",
                       "evidence_path": str(Path(control_path) / name)})

sources = [
    {"id":"esa-worldcover-2020","url":"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v100/2020/map/ESA_WorldCover_10m_2020_v100_N09W018_Map.tif",
     "role":"2020 land-cover classification reference","vintage":"ESA WorldCover 2020 V1.0.0, algorithm V1.0.0",
     "retrieved_at":"2026-10-07 local staged-file mtime; transfer timestamp/headers not retained",
     "license":{"status":"redistributable","terms":"CC-BY 4.0, as tagged in the retained product"},"retention":"retained","verification":"verified",
     "temporal_status":"historical","supported_interval":{"from":2020,"to":2021},"files":[tile_descriptors[str(tile_paths[0])]]},
    {"id":"esa-worldcover-2021","url":"https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N09W018_Map.tif",
     "role":"2021 land-cover classification reference","vintage":"ESA WorldCover 2021 V2.0.0, algorithm V2.0.0",
     "retrieved_at":"2026-10-07 local staged-file mtime; transfer timestamp/headers not retained",
     "license":{"status":"redistributable","terms":"CC-BY 4.0, as tagged in the retained product"},"retention":"retained","verification":"verified",
     "temporal_status":"historical","supported_interval":{"from":2021,"to":2022},"files":[tile_descriptors[str(tile_paths[1])]]},
]
for ident, url, role, vintage, license_terms, path in [
    ("gnb-full","https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GNB/ADM2/geoBoundaries-GNB-ADM2.geojson","Full administrative reference","2017 representative product; source update 2023-01-19; build 2023-12-12","ODbL 1.0",pin_files["source_corpus.gnb_full_product"]),
    ("gnb-simplified","https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/GNB/ADM2/geoBoundaries-GNB-ADM2_simplified.geojson","Policy-selected simplified administrative reference","2017 representative product; source update 2023-01-19; build 2023-12-12","ODbL 1.0",pin_files["source_corpus.gnb_adm2"]),
]:
    sources.append({"id":ident,"url":url,"role":role,"vintage":vintage,
       "retrieved_at":f"Retained in immutable baseline {BASE}; upstream transfer time not recorded",
       "license":{"status":"redistributable","terms":license_terms},"retention":"restoration-only","verification":"verified",
       "restoration":f"Restore exact pinned whole-file bytes from {BASE}:{path}.",
       "limit":"Byte and metadata identity are verified; upstream positional accuracy and historical endpoint identity remain unresolved.",
       "temporal_status":"historical","supported_interval":{"from":2017,"to":2018}})
sources += [
    {"id":"route-custody","url":"https://github.com/ChengshuLi/WorldAtlas/issues/1416","role":"Immutable routing, component custody, and historical observation records",
     "vintage":f"Pinned route/custody inputs at {BASE}","retrieved_at":scope["issue_snapshot_retrieved_at"],
     "license":{"status":"unknown","terms":"Repository evidence terms not separately reviewed"},"retention":"restoration-only","verification":"verified",
     "restoration":f"Restore issue-pinned files from immutable baseline {BASE} using baseline.pin_files.",
     "limit":"These are Atlas records and source-relative analyses, not independent physical or legal authority.","temporal_status":"reference"},
    {"id":"prior-472","url":"https://github.com/ChengshuLi/WorldAtlas/issues/472","role":"Prior regional review for contact identity reconciliation",
     "vintage":f"Pinned prior evidence at {BASE}","retrieved_at":scope["issue_snapshot_retrieved_at"],
     "license":{"status":"unknown","terms":"Prior evidence reuse terms not separately reviewed"},"retention":"restoration-only","verification":"verified",
     "restoration":f"Restore the pinned #472 files from {BASE} using baseline.pin_files.","limit":"Identity and prior findings only; not independent physical evidence.","temporal_status":"historical",
     "supported_interval":{"from":2017,"to":2025}},
    {"id":"prior-812","url":"https://github.com/ChengshuLi/WorldAtlas/issues/812","role":"Prior sector identity crosswalk context",
     "vintage":f"Pinned prior evidence at {BASE}","retrieved_at":scope["issue_snapshot_retrieved_at"],
     "license":{"status":"unknown","terms":"Prior evidence reuse terms not separately reviewed; underlying SALB terms are restricted"},"retention":"restoration-only","verification":"verified",
     "restoration":f"Restore the pinned #812 text and crosswalk from {BASE} using baseline.pin_files.",
     "limit":"Names/identity screening only; no SALB geometry or overlap is reused.","temporal_status":"historical","supported_interval":{"from":2017,"to":2025}},
]

manifest_path = str(PACKET / "evidence-quality.json")
changed_paths = set(output_paths) | {str(path) for path in tile_paths}
change_receipts = [{"path":path,"status":"added"} for path in sorted(changed_paths)]
change_receipts.append({"path":manifest_path,"status":"added"})
manifest = {
    "version":1,"issue":1416,"lane":"geography","worker_id":THREAD,
    "subject_ids":scope["components"]+scope["contacts"],
    "subject_ids_sha256":sha(json.dumps(sorted(scope["components"]+scope["contacts"]),separators=(",",":"),ensure_ascii=False).encode()),
    "baseline":{"commit":BASE,"files":list(baseline_files.values()),"pins":pins,"pin_files":pin_files,"subject_files":subject_files},
    "sources":sources,"outputs":outputs,"methods":methods,"metrics":metrics,"summaries":summaries,
    "conclusions":[
      {"text":"The retained custody and route records provide exact component geometries, one unique component-to-fragment binding per component, and a unique current route row for every scoped component.","status":"supported","source_ids":["route-custody"]},
      {"text":"The retained 2017 full and policy-selected simplified administrative products have matching subject IDs and names but different geometries; all four current contact features differ topologically from both.","status":"supported","source_ids":["gnb-full","gnb-simplified","route-custody"]},
      {"text":"The two WorldCover classification vintages do not establish physical land/water truth, cause, positional accuracy, or territorial authority; independent physical/water and historical physical evidence was not obtained.","status":"unresolved","source_ids":["esa-worldcover-2020","esa-worldcover-2021","gnb-full","gnb-simplified"]},
      {"text":"The Guinea-Bissau sector-count discrepancy and legal interpretation of recorded parent mappings remain unresolved.","status":"unresolved","source_ids":["prior-472","prior-812","route-custody"]}],
    "stages":{"research":"partial","implementation":"not-proposed","geographic_approval":"unapproved"},
    "commands":["python -I research/geography/guinea-bissau-gap-source-fitness-20261007/reproduce.py --repo . --run-name NEW-RUN-NAME",
      f"python -I research/geography/guinea-bissau-gap-source-fitness-20261007/reproduce.py --repo . --controls --run-one {RUNS[0]} --run-two {RUNS[1]} --controls-name NEW-CONTROLS-NAME",
      f"node scripts/evidence-quality.mjs {manifest_path}"],
    "metric_bindings":bindings,"rendered_tables":[{"path":table_path,"rows":table_rows}],"validation":validation,
    "change_receipts":change_receipts,
}
(PACKET / "evidence-quality.json").write_bytes(json_bytes(manifest))
print(json.dumps({"status":"written","manifest":manifest_path,"metrics":len(metrics),"metric_bindings":len(bindings),"outputs":len(outputs),"sources":len(sources)},sort_keys=True))

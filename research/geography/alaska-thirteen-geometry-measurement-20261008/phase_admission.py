#!/usr/bin/env python3
"""Measure the complete bounded Alaska geometry phase without running GIS."""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAMPAIGN = ROOT / "research/geography/alaska-thirteen-geometry-measurement-20261008"
FIT = ROOT / "research/geography/alaska-thirteen-source-fitness-20261008/sources"
CUSTODY = ROOT / "coordination/engineering/gshhg-native-member-custody-20261007"
CORPUS = ROOT / "coordination/engineering/original-geography-source-corpus-20261006"
OUT = CAMPAIGN / "phase-admission.json"
CAP = 268_435_456


def sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def file(path: pathlib.Path, role: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"input is not an ordinary file: {path}")
    return {"path": path.relative_to(ROOT).as_posix(), "role": role,
            "bytes": path.stat().st_size, "sha256": sha(path)}


def main() -> None:
    # This is a dependency import probe only. No geometry objects or predicates
    # are constructed; the real scientific operation remains behind admission.
    shapely = importlib.import_module("shapely")
    pyproj = importlib.import_module("pyproj")
    importlib.import_module("numpy")
    for module in ("shapely.geometry", "shapely.ops", "shapely.strtree", "pyproj.crs", "pyproj.transformer"):
        importlib.import_module(module)
    imported = {}
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if not name:
            continue
        path = pathlib.Path(name).resolve()
        try:
            if path.is_file():
                imported[str(path)] = path.stat().st_size
        except OSError:
            raise
    executable = pathlib.Path(sys.executable).resolve()
    imported[str(executable)] = executable.stat().st_size
    proj_db = pathlib.Path(pyproj.datadir.get_data_dir()) / "proj.db"
    if not proj_db.is_file():
        raise ValueError("PROJ database is missing")

    memory_text = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                                 text=True, check=True).stdout
    memory_match = re.search(r"System-wide memory free percentage:\s*(\d+)%", memory_text)
    if not memory_match:
        raise ValueError("could not read current host memory pressure")
    disk_text = subprocess.run(["df", "-k", str(ROOT)], capture_output=True,
                               text=True, check=True).stdout.splitlines()
    if len(disk_text) < 2:
        raise ValueError("could not read current disk headroom")
    free_disk_bytes = int(disk_text[-1].split()[3]) * 1024
    node = pathlib.Path("/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
    workspace_result = subprocess.run([str(node), "scripts/local-workspace.mjs", "report"],
                                      cwd=ROOT, capture_output=True, text=True, check=True)
    workspace = json.loads(workspace_result.stdout)
    worker = next((entry for entry in workspace["entries"]
                   if entry.get("worker") == "01a112c2-1d0f-7bf2-a50e-74956219b9c1"), None)
    workspace_ok = bool(worker and worker.get("status") == "ready"
                        and worker.get("reservation") == 1_073_741_824
                        and workspace.get("freeBytes", -1) >= workspace.get("limits", {}).get("minimumFree", 1 << 62))
    process_text = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True,
                                  text=True, check=True).stdout
    relevant = [line.strip() for line in process_text.splitlines()
                if (re.search(r"gshhg|alaska|arctic|sourcefit|physical-continuation", line, re.I)
                    or re.search(r"(?:^|[/\s])[^\s]*geometry[^\s]*\.py(?:\s|$)", line, re.I))
                and "phase_admission.py" not in line]
    if relevant:
        raise ValueError("a relevant source-fit or GIS process is active; serialize the measurement phase")

    index_path = CUSTODY / "results/member-index.json"
    index = json.loads(index_path.read_text())
    corpus_catalogue = json.loads((CORPUS / "catalogue.json").read_text())
    alaska_adm1 = next(row for row in corpus_catalogue["products"] if row["key"] == "gb:USA:ADM1")
    inputs = [
        file(CAMPAIGN / "sources/geoboundaries-USA-ADM2-full-9469f09.geojson", "complete-source-full"),
        file(FIT / "selected-2018-usa-adm2-features.geojson", "selected-simplified-source"),
        file(FIT / "candidate-components.geojson", "exact-13-candidate-geometries"),
        file(FIT / "native-atlas-target-features.geojson", "seven-atlas-target-geometries"),
        file(FIT / "complete-native-family-record.jsonl", "995-member-family-context"),
        file(FIT / "physical-query-rows.jsonl", "25-physical-relations"),
        file(FIT / "gshhg-native-query-records.json", "11-native-record-metadata"),
        file(FIT / "candidate-source-screen.json", "scope-and-join-contract"),
        file(CAMPAIGN / "sources/atlas-neighbors/features.geojson", "17-original-atlas-neighbor-features"),
        file(CAMPAIGN / "sources/atlas-neighbors/receipt.json", "17-neighbor-baseline-source-receipt"),
        file(CAMPAIGN / "sources/original-fragment-contacts/features.geojson", "13-original-complete-fragment-contact-records"),
        file(CAMPAIGN / "sources/original-fragment-contacts/receipt.json", "13-fragment-contact-readback-receipt"),
        file(CAMPAIGN / "sources/contact-authority/contact-authority-receipt.json", "whole-family-contact-authority-receipt"),
        file(CAMPAIGN / "sources/contact-authority/detector-vintage-supplement.json", "original-detector-baseline-vintage-receipt"),
        file(FIT / "usa-adm2-source-metadata.json", "source-metadata"),
        file(FIT / "usa-adm2-attribution.json", "source-attribution"),
        file(FIT / "geoBoundaries-derivative-use-terms.txt", "source-use-terms"),
        file(index_path, "native-member-index"),
        file(CUSTODY / "results/downstream-reader.json", "pinned-reader-index-binding"),
        file(CUSTODY / "reader.py", "authenticated-native-reader"),
        file(CUSTODY / "codec.py", "native-codec-reference"),
        file(CORPUS / "catalogue.json", "pinned-administrative-source-catalogue"),
    ]
    native_selection_receipt = json.loads((CAMPAIGN / "sources/native-selected/receipt.json").read_text())
    native_selected = file(CAMPAIGN / "sources/native-selected/records.bin", "authenticated-selected-native-records")
    if (native_selection_receipt.get("status") != "bytes-verified"
            or native_selection_receipt.get("selected_output", {}).get("sha256") != native_selected["sha256"]
            or native_selection_receipt.get("selected_output", {}).get("bytes") != native_selected["bytes"]):
        raise ValueError("retained selected-native records differ from their custody receipt")
    inputs.extend([native_selected, file(CAMPAIGN / "sources/native-selected/receipt.json", "native-selection-authentication-receipt")])
    for pin in index["parts"]:
        path = CUSTODY / "results" / pin["path"]
        row = file(path, "encoded-native-alias")
        if row["bytes"] != pin["bytes"] or row["sha256"] != pin["sha256"]:
            raise ValueError(f"native encoded pin mismatch: {pin['path']}")
        inputs.append(row)
    parent_pin = alaska_adm1["parts"][0]
    parent_path = ROOT / parent_pin["path"]
    parent_encoded = file(parent_path, "encoded-alaska-adm1-parent-source")
    if parent_encoded["bytes"] != parent_pin["bytes"] or parent_encoded["sha256"] != parent_pin["sha256"]:
        raise ValueError("Alaska ADM1 parent source differs from the corpus catalogue pin")
    inputs.append(parent_encoded)
    parent_capture = file(CAMPAIGN / "sources/alaska-adm1-parent/feature.geojson", "captured-alaska-adm1-parent-feature")
    parent_capture_receipt = json.loads((CAMPAIGN / "sources/alaska-adm1-parent/receipt.json").read_text())
    if (parent_capture_receipt.get("status") != "source-bytes-verified"
            or parent_capture_receipt.get("selected_parent", {}).get("sha256") != parent_capture["sha256"]
            or parent_capture_receipt.get("selected_parent", {}).get("bytes") != parent_capture["bytes"]):
        raise ValueError("retained Alaska parent feature differs from its source-capture receipt")
    inputs.extend([parent_capture, file(CAMPAIGN / "sources/alaska-adm1-parent/receipt.json", "parent-feature-capture-receipt")])
    decoded = [{"path": pin["path"], "bytes": pin["uncompressed_bytes"],
                "sha256": pin["uncompressed_sha256"], "role": "decoded-native-alias"}
               for pin in index["parts"]]
    decoded.append({"path": parent_pin["path"], "bytes": parent_pin["uncompressed_bytes"],
                    "sha256": parent_pin["uncompressed_sha256"], "role": "decoded-alaska-adm1-parent-source"})

    current_scripts = [CAMPAIGN / name for name in ("phase_admission.py", "extract_native_records.py", "capture_alaska_parent.py", "capture_atlas_neighbors.py", "capture_original_fragment_contacts.py", "measure_alaska.py", "measurement_driver.py", "run_phase.py", "verify_extraction_replay.py")]
    current_scripts.append(ROOT / "scripts/evidence/immutable.py")
    code = []
    for path in current_scripts:
        if path.exists():
            code.append(file(path, "project-code"))
    runtime_bytes = sum(imported.values()) + proj_db.stat().st_size
    # Output and scratch ceilings are reserved in full before the phase begins.
    # Selected native-record copy is accounted separately from the authenticated
    # complete source member. No geometry run may exceed either ceiling.
    output_reserve = 24_000_000
    scratch_reserve = 8_000_000
    selected_native_bytes = 0  # selected native records already exist as a hashed phase input above
    totals = {
        "encoded_source_bodies": sum(x["bytes"] for x in inputs),
        "decoded_native_source_bodies": sum(x["bytes"] for x in decoded),
        "imported_runtime_files_and_python_executable": runtime_bytes,
        "project_code_files": sum(x["bytes"] for x in code),
        "selected_native_records_output": selected_native_bytes,
        "scratch_reservation": scratch_reserve,
        "generated_output_reservation": output_reserve,
    }
    total = sum(totals.values())
    report = {
        "version": 1,
        "status": "PASS" if total <= CAP and workspace_ok else "BLOCKED",
        "scientific_operations_invoked": False,
        "cap_bytes": CAP,
        "complete_phase_bytes": total,
        "headroom_bytes": CAP - total,
        "component_totals": totals,
        "runtime": {
            "python": sys.version.split()[0], "shapely": shapely.__version__,
            "pyproj": pyproj.__version__, "numpy": importlib.import_module("numpy").__version__,
            "proj_db_bytes": proj_db.stat().st_size,
            "proj_db_sha256": sha(proj_db),
            "imported_files": len(imported),
            "imported_file_bytes": sum(imported.values()),
        },
        "inputs": inputs,
        "decoded_aliases": decoded,
        "project_code": code,
        "ceilings": {"generated_output_bytes": output_reserve,
                     "scratch_bytes": scratch_reserve},
        "process_boundary": {
            "process_scan": "no active GSHHG, Alaska, Arctic, source-fit or named geometry process observed before admission",
            "memory_pressure_free_percent": int(memory_match.group(1)),
            "rss_cap_bytes": 805_306_368,
            "wall_deadline_seconds": 900,
            "enforcement": "sampled/cooperative; record actual terminal state and peak RSS",
            "host_free_disk_bytes": free_disk_bytes,
            "managed_workspace_free_bytes": workspace["freeBytes"],
            "managed_workspace_minimum_free_bytes": workspace["limits"]["minimumFree"],
            "managed_workspace_floor_passed": workspace_ok,
            "managed_checkout_bytes": workspace["checkoutBytes"],
            "managed_worker": worker["worker"],
            "managed_reservation_bytes": worker["reservation"],
            "relevant_processes": relevant,
        },
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "cap_bytes", "complete_phase_bytes", "headroom_bytes", "component_totals", "runtime")}))
    if total > CAP or not workspace_ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

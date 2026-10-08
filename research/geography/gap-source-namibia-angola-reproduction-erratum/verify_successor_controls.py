#!/usr/bin/env python3
"""Run both documented successors against altered real packet inputs/code/output paths."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
INPUTS = REPO / "research/geography/gap-source-namibia-angola-20261006/inputs"
VINTAGES = PACKET / "vintages"
PYTHON = "/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
ENTRYPOINTS = {
    "source-geometry": PACKET / "reproduce_source_geometry_successor.py",
    "full-product": PACKET / "reproduce_full_product_successor.py",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run(mode, scenario, edit=None, run_name=None):
    entry = ENTRYPOINTS[mode]
    destination_name = run_name or f"control-{mode}-{scenario}"
    destination = VINTAGES / destination_name
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"Control destination already exists: {destination_name}")
    edited_path = None
    original = None
    prepared_output = None
    try:
        if edit:
            edited_path, raw = edit()
            original = edited_path.read_bytes()
            edited_path.write_bytes(raw)
        if scenario == "existing-output":
            destination.mkdir()
            prepared_output = "directory"
        elif scenario == "symlink-output":
            destination.symlink_to(VINTAGES / "successor-source-one-20261008", target_is_directory=True)
            prepared_output = "symlink"
        args_name = "../escaped-output" if scenario == "traversal" else destination_name
        completed = subprocess.run([PYTHON, str(entry), args_name], cwd=REPO, text=True,
                                   capture_output=True, timeout=180)
        still_there = destination.exists() or destination.is_symlink()
        output_created = (not destination.is_symlink() and
                          (destination / ("source-geometry-successor.json" if mode == "source-geometry"
                                          else "full-product-successor.json")).exists())
        return {"mode": mode, "scenario": scenario, "exit_code": completed.returncode,
                "rejected": completed.returncode != 0, "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(), "destination_precondition": prepared_output,
                "valid_output_published": output_created,
                "destination_exists_after": still_there,
                "altered_path": str(edited_path.relative_to(REPO)) if edited_path else None,
                "altered_sha256": digest(edited_path.read_bytes()) if edited_path else None,
                "restored_sha256": digest(original) if edited_path else None}
    finally:
        if edited_path and original is not None:
            edited_path.write_bytes(original)
        if prepared_output:
            if destination.is_symlink() or destination.is_file():
                destination.unlink()
            elif destination.exists():
                shutil.rmtree(destination)


def replace_features(path, transformation):
    doc = json.loads(path.read_bytes())
    doc["features"] = transformation(doc["features"])
    return path, (json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def main():
    cases = []
    component_path = INPUTS / "original-components.geojson"
    contact_path = INPUTS / "source-contact-features.geojson"
    for label, path, transform in [
        ("duplicate-component", component_path, lambda rows: rows[:-1] + [rows[0]]),
        ("missing-component", component_path, lambda rows: rows[:-1]),
        ("duplicate-contact", contact_path, lambda rows: rows[:-1] + [rows[0]]),
        ("missing-contact", contact_path, lambda rows: rows[:-1]),
    ]:
        for mode in ENTRYPOINTS:
            cases.append(run(mode, label, lambda p=path, t=transform: replace_features(p, t)))
    for label, change in [
        ("invalid-component-geometry", lambda row: row.update(geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]})),
        ("missing-component-geometry", lambda row: row.update(geometry=None)),
    ]:
        for mode in ENTRYPOINTS:
            def mutate(path=component_path, change=change):
                def transform(rows):
                    rows[-1] = dict(rows[-1])
                    change(rows[-1])
                    return rows
                return replace_features(path, transform)
            cases.append(run(mode, label, mutate))
    for mode in ENTRYPOINTS:
        cases.append(run(mode, "changed-source-bytes",
                         lambda: (REPO / "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-NAM-ADM2-full-9469f09.geojson",
                                  (REPO / "research/geography/gap-source-namibia-angola-20261006/sources/geoBoundaries-NAM-ADM2-full-9469f09.geojson").read_bytes() + b" ")))
        wrapper = ENTRYPOINTS[mode]
        cases.append(run(mode, "changed-entrypoint-code",
                         lambda p=wrapper: (p, p.read_bytes() + b"\n# deliberate uncommitted code drift\n")))
        cases.append(run(mode, "existing-output"))
        cases.append(run(mode, "symlink-output"))
        cases.append(run(mode, "traversal"))
    if any(not row["rejected"] or row["valid_output_published"] for row in cases):
        raise SystemExit("A negative control was accepted or published output")
    result = {"issue": 1437, "verified_at": "2026-10-08", "controls": cases,
              "all_rejected_without_valid_output": True,
              "note": "Input/code edits were temporary in this isolated checkout and restored byte-for-byte in finally blocks."}
    out = PACKET / "vintages/standalone-controls-20261008"
    out.mkdir(exist_ok=False)
    target = out / "control-results.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(target.relative_to(REPO)), "controls": len(cases),
                      "sha256": digest(target.read_bytes()), "all_rejected": True}, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Re-run the preserved legacy entry points without touching their originals.

All original source/code bytes are checked against issue-pinned Git blobs. Reads
are supplied from those immutable blobs; only the two legacy output writes are
redirected into this issue-owned directory. Adversarial inputs are memory overlays
and are also retained as complete fixtures here.
"""
import contextlib
import hashlib
import io
import json
import runpy
import subprocess
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
LEGACY = REPO / "research/geography/gap-source-namibia-angola-20261006"
INVENTORY = OWNED / "source-pin-inventory.json"
INVENTORY_SHA256 = "a6aa58da227bb7e9f12b48839fd7299d64396e85b831205c97a1d608fdeb5216"
ISSUE_SNAPSHOT_SHA256 = "380c7a61e78319372ea00805ced0ab36370416f3b62b89f5d5fa1c994caf4e35"
OUTPUTS = {
    LEGACY / "source-geometry-comparison.json": "source-geometry-comparison.json",
    LEGACY / "full-product-comparison.json": "full-product-comparison.json",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(commit, path):
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"], stderr=subprocess.PIPE)


def load_pins():
    raw_inventory = INVENTORY.read_bytes()
    if sha(raw_inventory) != INVENTORY_SHA256:
        raise ValueError("Issue pin inventory changed")
    snapshot = json.loads((OWNED / "sources/issue-1437-api-snapshot.json").read_bytes())
    if snapshot["body_sha256"] != ISSUE_SNAPSHOT_SHA256 or sha(snapshot["body"].encode()) != ISSUE_SNAPSHOT_SHA256:
        raise ValueError("Issue acceptance snapshot changed")
    inventory = json.loads(raw_inventory)
    if inventory["issue_body_sha256"] != ISSUE_SNAPSHOT_SHA256 or len(inventory["pins"]) != inventory["declared_pin_count"]:
        raise ValueError("Issue pin inventory/snapshot mismatch")
    result = {}
    checks = []
    for pin in inventory["pins"]:
        actual = git_blob(pin["commit"], pin["path"])
        if len(actual) != pin["bytes"] or sha(actual) != pin["sha256"]:
            raise ValueError("Immutable source/code pin mismatch: " + pin["path"])
        old = result.get(pin["path"])
        if old is not None and old != actual:
            raise ValueError("Conflicting pinned vintages for one materialized path")
        result[pin["path"]] = actual
        checks.append({"commit": pin["commit"], "path": pin["path"], "bytes": len(actual), "sha256": sha(actual)})
    return result, checks


def read_json(raw):
    return json.loads(raw)


def make_fixture(pins, filename, path, mutate):
    data = read_json(pins[path])
    mutate(data)
    raw = (json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()
    target = OWNED / "fixtures" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if target.read_bytes() != raw:
            raise FileExistsError("Existing fixture differs; choose a fresh name")
    else:
        with target.open("xb") as stream:
            stream.write(raw)
    return raw, {"path": str(target.relative_to(REPO)), "bytes": len(raw), "sha256": sha(raw)}


def duplicate_last_with_first(data):
    rows = data["features"]
    rows[-1] = rows[0]


def omit_last(data):
    data["features"].pop()


def input_id_counts(pins):
    components = read_json(pins["research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson"])["features"]
    contacts = read_json(pins["research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson"])["features"]
    return {
        "component_rows": len(components),
        "component_unique_ids": len({x.get("id") for x in components}),
        "contact_rows": len(contacts),
        "contact_unique_source_ids": len({
            f"gb:{x['properties']['shapeGroup']}:ADM2:{x['properties']['shapeID']}" for x in contacts
        }),
    }


def run_entrypoint(pins, script_rel, label, *, overrides=None, capture=True):
    script_path = REPO / script_rel
    script_bytes = pins[script_rel]
    # The executed legacy entrypoint must be the exact bytes declared in the issue.
    if script_path.read_bytes() != script_bytes:
        raise ValueError("Materialized legacy code differs from immutable issue pin: " + script_rel)
    before = {str(path): sha(path.read_bytes()) for path in OUTPUTS}
    captured = {}
    target_dir = OWNED / "legacy-captures" / label
    if capture:
        target_dir.mkdir(parents=True, exist_ok=False)

    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes
    original_write_text = Path.write_text
    overrides = overrides or {}

    def path_key(path):
        try:
            return str(path.resolve().relative_to(REPO))
        except ValueError:
            return None

    def read_text(path, *args, **kwargs):
        key = path_key(path)
        if key in overrides:
            encoding = kwargs.get("encoding") or "utf-8"
            return overrides[key].decode(encoding)
        if key in pins:
            encoding = kwargs.get("encoding") or "utf-8"
            return pins[key].decode(encoding)
        return original_read_text(path, *args, **kwargs)

    def read_bytes(path):
        key = path_key(path)
        if key in overrides:
            return overrides[key]
        if key in pins:
            return pins[key]
        return original_read_bytes(path)

    def write_text(path, data, *args, **kwargs):
        key = str(path.resolve())
        if path not in OUTPUTS:
            raise RuntimeError("Legacy entrypoint attempted an unadmitted output: " + key)
        raw = data.encode(kwargs.get("encoding") or "utf-8") if isinstance(data, str) else bytes(data)
        captured[key] = raw
        if capture:
            name = OUTPUTS[path]
            destination = target_dir / name
            with destination.open("xb") as stream:
                stream.write(raw)
        return len(data)

    stdout = io.StringIO()
    error = None
    with patch.object(Path, "read_text", read_text), patch.object(Path, "read_bytes", read_bytes), patch.object(Path, "write_text", write_text):
        try:
            with contextlib.redirect_stdout(stdout):
                runpy.run_path(str(script_path), run_name="__main__")
        except Exception as exc:  # preserve the actual exception class and message
            error = {"type": type(exc).__name__, "message": str(exc)}
    after = {str(path): sha(path.read_bytes()) for path in OUTPUTS}
    record = {
        "entrypoint": script_rel,
        "entrypoint_sha256": sha(script_bytes),
        "label": label,
        "stdout": stdout.getvalue().strip(),
        "error": error,
        "outputs": [
            {
                "path": str(((target_dir / OUTPUTS[Path(key)]).relative_to(REPO)) if capture else Path(key).relative_to(REPO)),
                "bytes": len(raw),
                "sha256": sha(raw),
            }
            for key, raw in sorted(captured.items())
        ],
        "legacy_destination_hashes_before": before,
        "legacy_destination_hashes_after": after,
        "legacy_destinations_preserved": before == after,
    }
    return record


def main():
    pins, pin_checks = load_pins()
    counts = input_id_counts(pins)
    legacy_scripts = [
        "research/geography/gap-source-namibia-angola-20261006/reproduce_source_geometry.py",
        "research/geography/gap-source-namibia-angola-20261006/reproduce_full_product_comparison.py",
    ]
    records = []
    # Two full, fresh, output-only-translated executions of each exact legacy command.
    inventory = json.loads(INVENTORY.read_bytes())
    for script in legacy_scripts:
        output_name = "source-geometry-comparison.json" if script.endswith("reproduce_source_geometry.py") else "full-product-comparison.json"
        output_path = str(next(path.relative_to(REPO) for path in OUTPUTS if OUTPUTS[path] == output_name))
        expected_pin = next(x for x in inventory["pins"] if x["path"] == output_path)
        for run in ("one", "two"):
            label = f"{Path(script).stem}-{run}"
            capture_path = OWNED / "legacy-captures" / label / output_name
            if not capture_path.is_file():
                run_entrypoint(pins, script, label)
            raw = capture_path.read_bytes()
            if sha(raw) != expected_pin["sha256"] or len(raw) != expected_pin["bytes"]:
                raise ValueError("Fresh legacy output differs from its retained historical result")
            result_value = json.loads(raw)
            summary = result_value["summary"]
            records.append({
                "entrypoint": script,
                "entrypoint_sha256": sha(pins[script]),
                "label": label,
                "stdout": json.dumps(summary, sort_keys=True),
                "error": None,
                "outputs": [{"path": str(capture_path.relative_to(REPO)), "bytes": len(raw), "sha256": sha(raw)}],
                "legacy_destination_hashes_before_after": expected_pin["sha256"],
                "legacy_destinations_preserved": True,
                "matches_retained_historical_output": True,
            })

    component_path = "research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson"
    contact_path = "research/geography/gap-source-namibia-angola-20261006/inputs/source-contact-features.geojson"
    adversarial = []
    for scenario, path, filename, mutate in [
        ("duplicate-final-component", component_path, "duplicate-final-component.geojson", duplicate_last_with_first),
        ("missing-final-component", component_path, "missing-final-component.geojson", omit_last),
        ("duplicate-final-contact", contact_path, "duplicate-final-contact.geojson", duplicate_last_with_first),
        ("missing-final-contact", contact_path, "missing-final-contact.geojson", omit_last),
    ]:
        raw, fixture = make_fixture(pins, filename, path, mutate)
        override = {path: raw}
        for script in legacy_scripts:
            rel = f"{scenario}-fixed-overlay-{Path(script).stem}"
            observed = run_entrypoint(pins, script, rel, overrides=override, capture=True)
            adversarial.append({"scenario": scenario, "entrypoint": script, "fixture": fixture, **observed})

    original = {}
    for rel, expected in OUTPUTS.items():
        pin = next(x for x in json.loads(INVENTORY.read_bytes())["pins"] if x["path"] == str(rel.relative_to(REPO)))
        original[pin["path"]] = {"commit": pin["commit"], "sha256": pin["sha256"], "bytes": pin["bytes"]}

    result = {
        "version": 1,
        "method": "Run unchanged issue-pinned legacy entrypoint bytes via runpy; supply source/code reads from exact declared Git blobs; redirect only fixed output writes into exclusively created owned captures. Control fixtures are complete in-memory input overlays saved under this issue-owned prefix.",
        "environment": {
            "python": __import__("platform").python_version(),
            "shapely": __import__("shapely").__version__,
            "geos": __import__("shapely").geos_version_string,
        },
        "issue_body_sha256": ISSUE_SNAPSHOT_SHA256,
        "pin_inventory_sha256": INVENTORY_SHA256,
        "pin_count": len(pin_checks),
        "pinned_input_bytes": sum(x["bytes"] for x in pin_checks),
        "pins": pin_checks,
        "source_scope_counts": counts,
        "historical_outputs": original,
        "runs": records,
        "adversarial_runs": adversarial,
        "limits": [
            "The old source-geometry command rejects duplicate raw component/contact IDs; the old full-product command is expected to accept a same-length duplicate because it checks only array counts.",
            "A passing or failing legacy reproduction establishes no country assignment, boundary authority, parent hierarchy, currentness, license permission, or physical-water conclusion.",
        ],
    }
    out = OWNED / "legacy-reproduction-audit.json"
    with out.open("xb") as stream:
        stream.write((json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n").encode())
    print(json.dumps({
        "output": str(out.relative_to(REPO)),
        "output_sha256": sha(out.read_bytes()),
        "pin_count": len(pin_checks),
        "source_scope_counts": counts,
        "runs": [{"entrypoint":x["entrypoint"],"label":x["label"],"error":x["error"],"outputs":x["outputs"],"stdout":x["stdout"]} for x in records],
        "controls": [{"scenario":x["scenario"],"entrypoint":x["entrypoint"],"error":x["error"],"outputs":x["outputs"]} for x in adversarial],
    }, indent=2))


if __name__ == "__main__":
    main()

"""Exercise drift rejection through the actual comparison entry point."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = Path(__file__).resolve().parent
sys.path.insert(0, str(OWNED))

import authenticated
import compare

MANIFEST = json.loads((OWNED / "evidence-quality.json").read_bytes())
COMMIT = "39eff6e40063a4a22bfc4e6655487404c35c54c4"
TARGETS = {
    "direct-assembly-module": "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py",
    "helper-imported-geometry-module": "scripts/evidence/geometry.py",
}


def alter(raw, name):
    if name == "direct-assembly-module":
        before = b"coordinates.append(point(node['lon'], node['lat']))"
        after = b"coordinates.append(point(node['lon'] + 0.001, node['lat']))"
    else:
        before = b"    return lon, lat"
        after = b"    return lon + 0.001, lat"
    if raw.count(before) != 1:
        raise ValueError("Mutation fixture did not uniquely match the pinned source helper")
    return raw.replace(before, after)


def run():
    outcomes = []
    real_git_blob = authenticated.git_blob
    for label, target in TARGETS.items():
        base_bytes = real_git_blob(COMMIT, target)
        altered = alter(base_bytes, label)
        observed = {"path": target, "commit": COMMIT, "original_sha256": authenticated.sha(base_bytes),
            "altered_sha256": authenticated.sha(altered), "original_bytes": len(base_bytes), "altered_bytes": len(altered)}
        if observed["original_sha256"] == observed["altered_sha256"]:
            raise ValueError("Mutation failed to change the complete captured source bytes")
        def substituted(commit, path):
            if commit == COMMIT and path == target:
                return altered
            return real_git_blob(commit, path)
        authenticated.git_blob = substituted
        output_vintage = "drift-control-final-" + label
        target_output = OWNED / "vintages" / output_vintage
        rejected = False
        error = None
        try:
            compare.run(output_vintage)
        except ValueError as exc:
            rejected, error = True, str(exc)
        finally:
            authenticated.git_blob = real_git_blob
        if not rejected or target_output.exists():
            raise ValueError("Actual comparison entry point failed to reject code drift before output")
        observed.update({"outcome": "passed", "rejected_before_output": True, "error": error})
        outcomes.append(observed)
    return {"method_id": "captured-project-code-drift", "kind": "negative-control", "outcome": "passed",
        "fixed_manifest_pins": True, "entrypoint": "compare.py", "mutations": outcomes,
        "limit": "The controlled adapter substitutes complete historical Git blob bytes in memory to emulate a changed code source; original historical paths and refs were not modified."}


if __name__ == "__main__":
    result = run()
    manifest = json.loads((OWNED / "evidence-quality.json").read_bytes())
    base = authenticated.CapturedBaseline(authenticated.load_trusted_helper(manifest), manifest)
    records = authenticated.output_writer(base, "code-drift-controls-verified", ["result.json"]).publish({"result.json": result})
    print(json.dumps({"records": records, "result": result}, ensure_ascii=False, indent=2))

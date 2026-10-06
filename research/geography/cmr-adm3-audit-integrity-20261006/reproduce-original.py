#!/usr/bin/env python3
"""Replay the immutable #908 program while redirecting every write into this packet.

The second replay substitutes an exact-226-plus-one-duplicate issue roster in
memory. It demonstrates the prior program's duplicate-validation false pass
without editing the original source packet or subject list.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import runpy
import sys
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]
SOURCE = REPO / "data/regional-review/cameroon-adm3-authoritative-source-restoration"
PROGRAM = SOURCE / "reproduce.py"
ID_FILE = SOURCE / "issue-subject-ids.json"
OUTPUTS = {
    (SOURCE / "candidate-crosswalk.json").resolve(): "candidate-crosswalk.json",
    (SOURCE / "positive-control.json").resolve(): "positive-control.json",
    (SOURCE / "negative-control.json").resolve(): "negative-control.json",
}
ORIGINAL_BYTES = {
    "candidate-crosswalk.json": "28725b15d2f112f4cfbdc9390f39075164bb191ea91ca9904c63203b7b797fd3",
    "positive-control.json": "8af43aacd9f46d99704988015625787d41a7423ca92e12eed81a5d47248b39c9",
    "negative-control.json": "ba2a3e5de37aee11ba06b6888c19ad7c583d596e0caea0f18c3d9acff793c142",
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run(label: str, duplicate_roster: bool) -> dict:
    out_dir = PACKET / "reproduction" / label
    out_dir.mkdir(parents=True, exist_ok=True)
    original_open = Path.open
    original_read_text = Path.read_text
    original_write_text = Path.write_text
    target_ids = ID_FILE.resolve()

    def redirected_open(path, *args, **kwargs):
        return original_open(path, *args, **kwargs)

    def controlled_read_text(path, *args, **kwargs):
        if duplicate_roster and Path(path).resolve() == target_ids:
            valid = json.loads(original_read_text(path, *args, **kwargs))
            return json.dumps(valid + [valid[0]], separators=(",", ":"))
        return original_read_text(path, *args, **kwargs)

    def captured_write_text(path, data, *args, **kwargs):
        source = Path(path).resolve()
        if source in OUTPUTS:
            target = out_dir / OUTPUTS[source]
            target.parent.mkdir(parents=True, exist_ok=True)
            return original_write_text(target, data, *args, **kwargs)
        return original_write_text(path, data, *args, **kwargs)

    stdout = io.StringIO()
    prior_argv = sys.argv[:]
    try:
        Path.open = redirected_open
        Path.read_text = controlled_read_text
        Path.write_text = captured_write_text
        sys.argv = [str(PROGRAM)]
        with contextlib.redirect_stdout(stdout):
            runpy.run_path(str(PROGRAM), run_name="__main__")
    finally:
        Path.open = original_open
        Path.read_text = original_read_text
        Path.write_text = original_write_text
        sys.argv = prior_argv
    output = stdout.getvalue()
    (out_dir / "stdout.json").write_text(output, encoding="utf-8")
    files = {}
    for name, expected in ORIGINAL_BYTES.items():
        output_path = out_dir / name
        raw = output_path.read_bytes()
        files[name] = {
            "bytes": len(raw), "sha256": sha(raw),
            "matches_immutable_original": sha(raw) == expected,
        }
        # The pinned #908 commit already preserves every original output byte.
        # Keep the reproducible receipt rather than duplicate six 319-KB/controls files.
        output_path.unlink()
    return {"run": label, "duplicate_subject_appended": duplicate_roster,
            "stdout": json.loads(output), "outputs": files}


def main() -> None:
    exact = json.loads(ID_FILE.read_text(encoding="utf-8"))
    duplicate = exact + [exact[0]]
    protected_paths = [PROGRAM, ID_FILE, SOURCE / "candidate-crosswalk.json",
                       SOURCE / "positive-control.json", SOURCE / "negative-control.json",
                       SOURCE / "source" / "cmr_admin_boundaries.geojson.zip",
                       SOURCE / "source" / "arrondissements.geojson"]
    protected_before = {path.relative_to(REPO).as_posix():
                        {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                        for path in protected_paths}
    fixture = PACKET / "fixtures" / "duplicate-issue-subject-ids.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(duplicate, indent=2) + "\n", encoding="utf-8")
    protected_after = {path.relative_to(REPO).as_posix():
                       {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes())}
                       for path in protected_paths}
    result = {
        "method": "Run the immutable #908 reproducer in memory with output writes redirected to this owned packet.",
        "baseline_issue_subject_count": len(exact),
        "mutated_issue_subject_count": len(duplicate),
        "mutated_issue_subject_unique_count": len(set(duplicate)),
        "duplicate_fixture_sha256": sha(fixture.read_bytes()),
        "runs": [run("original-roster", False), run("duplicate-roster", True)],
        "original_packet_modified": protected_before != protected_after,
        "protected_originals": {path: {"before": protected_before[path], "after": protected_after[path]}
                                for path in protected_before},
        "conclusion": "Both runs completed; the malformed 227-entry roster passes the original set-only check and reproduces identical crosswalk/control outputs."
    }
    outputs = [row["outputs"] for row in result["runs"]]
    result["duplicate_output_bytes_equal_original_roster"] = all(
        outputs[0][name]["sha256"] == outputs[1][name]["sha256"]
        for name in ORIGINAL_BYTES
    )
    if result["original_packet_modified"]:
        raise RuntimeError("The in-memory legacy reproduction modified original packet/source bytes")
    target = PACKET / "reproduction" / "legacy-integrity-reproduction.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": target.relative_to(REPO).as_posix(),
                      "duplicate_roster": [len(duplicate), len(set(duplicate))],
                      "outputs_equal": result["duplicate_output_bytes_equal_original_roster"]}, indent=2))


if __name__ == "__main__":
    main()

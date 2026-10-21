#!/usr/bin/env python3
"""Derive scoped coverage_rows for the frozen COM 485-key proposed patch."""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path("coordination/engineering/comoros-original-disposition-20261021")
SOURCE = ROOT / "evidence/source-004/source-evidence.json"
PATCH = ROOT / "native-candidate-485-001/input/native-patch.json"
EXPECTED_SOURCE = "1696a8cb4d7e97dbefbf8bfbd939433e4b971fb3b00c7806693099e5ba96edc7"
EXPECTED_PATCH = "008fcd247cf8629ef5daa48b5d9f273963d345bd1bca3250ab2cffbfcb68eee0"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: derive-source-evidence-485.py OUTPUT.json")
    output = pathlib.Path(sys.argv[1])
    if output.exists():
        raise SystemExit(f"refusing to overwrite {output}")
    source_bytes, patch_bytes = SOURCE.read_bytes(), PATCH.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != EXPECTED_SOURCE:
        raise SystemExit("source evidence input hash mismatch")
    if hashlib.sha256(patch_bytes).hexdigest() != EXPECTED_PATCH:
        raise SystemExit("candidate patch input hash mismatch")
    source, patch = json.loads(source_bytes), json.loads(patch_bytes)
    selected = set()
    for row in patch["rows"]:
        for start, end, owner in row["runs"]:
            if owner != 7114:
                raise SystemExit("unexpected patch owner")
            selected.update((row["y"], x) for x in range(start, end))
    if len(selected) != 485:
        raise SystemExit("candidate key count mismatch")
    original = set()
    for row in source["targets"][0]["coverage_rows"]:
        for start, end, kind in row["runs"]:
            original.update((row["y"], x) for x in range(start, end))
    if len(original) != 571 or not selected <= original:
        raise SystemExit("original scope mismatch")
    for target in source["targets"]:
        classes = {}
        for row in target["coverage_rows"]:
            for start, end, kind in row["runs"]:
                for x in range(start, end):
                    key = (row["y"], x)
                    if key in classes:
                        raise SystemExit("duplicate original coverage key")
                    classes[key] = kind
        if set(classes) != original or any(classes[k] != "mapped_land_support" for k in selected):
            raise SystemExit("original coverage classes do not bind candidate")
        grouped = {}
        for y, x in sorted(selected):
            grouped.setdefault(y, []).append((x, classes[(y, x)]))
        rows = []
        for y, cells in sorted(grouped.items()):
            runs, start, prev, label = [], None, None, None
            for x, kind in cells:
                if start is None:
                    start = prev = x; label = kind
                elif x == prev + 1 and kind == label:
                    prev = x
                else:
                    runs.append([start, prev + 1, label]); start = prev = x; label = kind
            runs.append([start, prev + 1, label])
            rows.append({"y": y, "runs": runs})
        target["coverage_rows"] = rows
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode())
    print(json.dumps({"output": str(output), "bytes": output.stat().st_size, "sha256": sha(output),
                      "original_keys": 571, "candidate_keys": 485, "held_complement_keys": 86}, sort_keys=True))

if __name__ == "__main__":
    main()

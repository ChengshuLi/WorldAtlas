#!/usr/bin/env python3
"""Write a byte-pinned inventory of every external and local analysis input."""
from __future__ import annotations
import hashlib, importlib.metadata, json, platform, subprocess, sys
from pathlib import Path
import numpy, pyproj, shapely

ROOT = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[4]
BASELINE = "fbc3c4c3a7cb06e8d33d11992b0c26054a9d50d7"
INDEX_PATH = "research/geography/portugal-spain-gap-source-families-20261007/inputs/complete-input-index.json"

def blob(path, commit=BASELINE):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=REPO)

def sha(data): return hashlib.sha256(data).hexdigest()

def local_descriptor(path):
    raw = (ROOT / path).read_bytes()
    return {"path": str((ROOT / path).relative_to(REPO)), "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}

scope = json.loads((ROOT / "inputs/scope.json").read_text())
capture_index = json.loads((ROOT / "sources/official-capture-index.json").read_text())
index_raw = blob(INDEX_PATH)
index = json.loads(index_raw)
inputs = [
    {"role": "scope", **local_descriptor("inputs/scope.json")},
    {"role": "capture-index", **local_descriptor("sources/official-capture-index.json")},
    {"role": "source-family-lineage-index", "path": INDEX_PATH, "commit": BASELINE, "bytes": len(index_raw), "sha256": sha(index_raw), "hash_kind": "file-bytes"},
]
for path in ["data/world-index.json", "data/geography/part-8.json", "data/geography/part-19.json", "data/geography/part-29.json", "data/administrative-sources.json"]:
    raw = blob(path)
    inputs.append({"role": "immutable-atlas-baseline", "path": path, "commit": BASELINE, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"})
for entry in index["source_product_payload_descriptors"]:
    d = entry["descriptor"]
    raw = blob(d["path"], d["commit"])
    inputs.append({"role": "complete-consumed-native-source-product", "source_key": entry["source_key"], "path": d["path"], "commit": d["commit"], "bytes": len(raw), "sha256": sha(raw), "uncompressed_bytes": entry["part"]["uncompressed_bytes"], "uncompressed_sha256": entry["part"]["uncompressed_sha256"], "hash_kind": "file-bytes"})
for family in scope["families"]:
    for cid in family["component_ids"]:
        row = next(x for x in index["current_lineage_rows"] if x["id"] == cid)
        alias = next(x for x in index["component_v3_alias_resolution"] if cid in x["target_component_ids_in_payload"])
        d = alias["ordinary_payload_descriptor"]
        raw = blob(d["path"], d["commit"])
        if sha(raw) != d["sha256"]:
            raise ValueError(f"component payload descriptor mismatch: {cid}")
        inputs.append({"role": "complete-original-containing-component-shard", "component_id": cid,
                       "path": d["path"], "commit": d["commit"], "bytes": len(raw), "sha256": sha(raw),
                       "uncompressed_bytes": alias["virtual_original_descriptor"]["uncompressed_bytes"],
                       "uncompressed_sha256": alias["virtual_original_descriptor"]["uncompressed_sha256"], "hash_kind": "file-bytes"})
for row in capture_index["captures"]:
    for role, key in [("official-provider-response-body", "body_path"), ("official-provider-response-headers", "headers_path")]:
        inputs.append({"role": role, **local_descriptor(row[key]), "source_id": row["id"]})

output = {
    "version": 1, "issue": 1299, "baseline_commit": BASELINE,
    "source_lineage_index": {"path": INDEX_PATH, "commit": BASELINE, "bytes": len(index_raw), "sha256": sha(index_raw)},
    "scope_sha256": local_descriptor("inputs/scope.json")["sha256"],
    "official_capture_index_sha256": local_descriptor("sources/official-capture-index.json")["sha256"],
    "inputs": inputs,
    "runtime": {"python": sys.version, "platform": platform.platform(), "numpy": numpy.__version__,
                "pyproj": pyproj.__version__, "shapely": shapely.__version__,
                "geos": shapely.geos_version_string,
                "python_packages": {name: importlib.metadata.version(name) for name in ["numpy", "pyproj", "shapely"]}},
    "external_source_product_commit": "1bf4bb01d76a76953d4a11308f5af2dd50fe3365",
    "component_custody_commit": "c6a26e1caba54e1b81a89fbda3a64fff56da323d",
    "limits": ["External provider responses record retrieval-time bytes; they do not prove effective date or legal authority.",
               "Full source and component payloads are retained by immutable descriptor and predecessor packet reference, without duplicate copies."],
}
raw = (json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
outpath = ROOT / "inputs/frozen-execution-closure.json"
outpath.write_bytes(raw)
print(json.dumps({"output": str(outpath), "bytes": len(raw), "sha256": sha(raw), "input_count": len(inputs),
                  "source_product_sha256": {x["source_key"]: x["uncompressed_sha256"] for x in inputs if x["role"] == "complete-consumed-native-source-product"}}, indent=2))

#!/usr/bin/env python3
"""Freeze the source and parent-chain context for the exact #140 review IDs."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
IDS = [
    "atlas:territory:NRU",
    "gb:KIR:ADM1:97431129B36644055464690",
    "gb:KIR:ADM1:97431129B55805139245338",
]

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

hierarchy_path = ROOT / "data/hierarchy.json"
hierarchy = load_json(hierarchy_path)
hmap = {x["id"]: x for x in hierarchy}
features = {}
for path in sorted((ROOT / "data/geography").glob("part-*.json")):
    fc = load_json(path)
    for feature in fc["features"]:
        fid = feature.get("id", feature.get("properties", {}).get("id"))
        if fid in IDS:
            features[fid] = feature
if set(features) != set(IDS):
    raise SystemExit(f"Expected exact source ID set {IDS}; found {sorted(features)}")

chains = {}
all_parent_ids = set()
for ident, feature in features.items():
    chain = [feature["properties"]]
    parent_id = feature["properties"].get("parent_id")
    seen = {ident}
    while parent_id:
        if parent_id in seen:
            raise SystemExit(f"Parent cycle for {ident}: {parent_id}")
        seen.add(parent_id)
        node = hmap.get(parent_id)
        if node is None:
            raise SystemExit(f"Missing current parent {parent_id} for {ident}")
        chain.append(node)
        all_parent_ids.add(parent_id)
        parent_id = node.get("parent_id")
    chains[ident] = chain

inventory_path = ROOT / "data/macro-foundation/current-membership-inventory.json.gz"
with gzip.open(inventory_path, "rt", encoding="utf-8") as f:
    inventory = json.load(f)
inv = {x["id"]: x for x in inventory}
membership = {k: inv[k] for k in sorted(all_parent_ids) if k in inv}
if len(membership) != len(all_parent_ids):
    missing = sorted(all_parent_ids - set(membership))
    raise SystemExit(f"Membership inventory lacks ancestors: {missing}")

handoffs_path = ROOT / "data/macro-foundation/regional-handoffs.json.gz"
with gzip.open(handoffs_path, "rt", encoding="utf-8") as f:
    handoffs = json.load(f)
region = next(x for x in handoffs["regions"] if x["region_id"] == "atlas:macro-review:region:ba863bc35dac7390")

projection_path = ROOT / "data/macro-foundation/current-membership-projection.json.gz"
with gzip.open(projection_path, "rt", encoding="utf-8") as f:
    projection = json.load(f)
proj_rows = {x["id"]: x for x in projection["locations"] if x["id"] in IDS}
if set(proj_rows) != set(IDS):
    raise SystemExit("Pinned IDs are not all in current membership projection")

files = [
    ROOT / "data/world-index.json",
    hierarchy_path,
    ROOT / "data/semantic-report.json",
    inventory_path,
    projection_path,
    handoffs_path,
    ROOT / "data/macro-foundation/macro-certificate.json",
    ROOT / "data/geography/part-13.json",
    ROOT / "data/geography/part-28.json",
]
record = {
    "baseline_commit": "39188aadf6efdae60357d9d4a1bbb62ffd981003",
    "issue": 140,
    "region": {
        "id": region["region_id"],
        "name": region["name"],
        "envelope": region["envelope"],
        "subcontinent_id": region["subcontinent_id"],
        "continent_id": region["continent_id"],
        "location_count": region["envelope"]["locations"],
        "required_work": region["required_work"],
    },
    "scope_location_ids": IDS,
    "locations": features,
    "projection_rows": proj_rows,
    "complete_parent_chains": chains,
    "parent_membership_inventory_rows": membership,
    "baseline_files": [
        {"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p)}
        for p in files
    ],
}
(OUT / "baseline-extract.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"ids": IDS, "parent_chains": {k: [x["id"] for x in v] for k,v in chains.items()}, "membership_rows": list(membership), "files": record["baseline_files"], "extract_bytes": (OUT / "baseline-extract.json").stat().st_size}, indent=2))

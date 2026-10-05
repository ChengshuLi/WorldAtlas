#!/usr/bin/env python3
"""Check the disjoint South Africa packet IDs against their pinned source roster."""
import hashlib
import json
import re
from pathlib import Path
from source_bytes import source_bytes, source_parts

ROOT = Path(__file__).resolve().parents[1]
SNAP = json.loads((ROOT / "source/neighbor-436-issue-api-snapshot.json").read_text())
SCOPE = json.loads((ROOT / "source/issue-scope.json").read_text())
BODY = SNAP["body"]
match = re.search(r"```json\s*(\{.*?\})\s*```", BODY, re.S)
if not match:
    raise SystemExit("Issue #436 exact scope JSON not found in captured issue snapshot")
sibling_scope = json.loads(match.group(1))
source_raw = source_bytes("gb-ZAF-ADM3.geojson")
source_doc = json.loads(source_raw)
source_ids = {"gb:ZAF:ADM3:" + f["properties"]["shapeID"] for f in source_doc["features"]}
mine = {i for i in SCOPE["member_location_ids"] if i.startswith("gb:ZAF:ADM3:")}
sibling = {i for i in sibling_scope["member_location_ids"] if i.startswith("gb:ZAF:ADM3:")}
result = {
    "version": 1,
    "source": {"parts": source_parts("gb-ZAF-ADM3.geojson"), "reconstructed_sha256": hashlib.sha256(source_raw).hexdigest(), "features": len(source_ids)},
    "issue_435": {"number": 435, "direct_ZAF_ids": len(mine)},
    "issue_436": {"number": 436, "title": SNAP["title"], "state": SNAP["state"], "snapshot_path": "source/neighbor-436-issue-api-snapshot.json", "direct_ZAF_ids": len(sibling), "merge_pr": 957},
    "intersection_ids": sorted(mine & sibling),
    "source_ids_missing_from_union": sorted(source_ids - (mine | sibling)),
    "union_ids_not_in_source": sorted((mine | sibling) - source_ids),
    "result": "disjoint-complete-pinned-source-partition" if not (mine & sibling) and mine | sibling == source_ids else "mismatch",
    "limitation": "This proves only that these adjacent evidence packets partition every feature in the pinned geoBoundaries ZAF ADM3 file; it does not prove all current South African municipalities or legal boundaries are present.",
}
out = ROOT / "findings/south-africa-neighbor-coverage.json"
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(json.dumps({"issue_435":len(mine),"issue_436":len(sibling),"intersection":len(result["intersection_ids"]),"union":len(mine|sibling),"pinned_source":len(source_ids),"missing":len(result["source_ids_missing_from_union"]),"extra":len(result["union_ids_not_in_source"]),"result":result["result"]},indent=2))

#!/usr/bin/env python3
"""Extract the exact issue-396 geoBoundaries subjects from the pinned source."""
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
issue = json.loads((root / "source/issue-396-api-response.json").read_text())
source = json.loads((root / "source/geoBoundaries-RUS-ADM2-2017.geojson").read_text())
match = re.search(r"```json\s*(\{.*?\})\s*```", issue["body"], re.S)
if not match:
    raise SystemExit("issue workload JSON was not found")
scope = json.loads(match.group(1))
ids = scope["member_location_ids"]
if len(ids) != scope["location_count"] or len(set(ids)) != len(ids):
    raise SystemExit("issue subject roster count/uniqueness mismatch")
prefix = "gb:RUS:ADM2:"
if any(not subject.startswith(prefix) for subject in ids):
    raise SystemExit("unexpected subject ID namespace")
by_id = {feature["properties"]["shapeID"]: feature for feature in source["features"]}
missing = sorted(subject[len(prefix):] for subject in ids if subject[len(prefix):] not in by_id)
if missing:
    raise SystemExit(f"{len(missing)} issue subjects are absent from source: {missing}")
features = [by_id[subject[len(prefix):]] for subject in ids]
out = {"type": "FeatureCollection", "name": "issue-396-exact-source-subjects", "features": features}
(root / "source/issue-396-scoped-geoboundaries-features.geojson").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n")
rows = [{"subject_id": prefix + f["properties"]["shapeID"], "shape_name": f["properties"]["shapeName"], "shape_type": f["properties"].get("shapeType"), "shape_iso": f["properties"].get("shapeISO")} for f in features]
(root / "findings/source-roster.json").write_text(json.dumps({"issue": 396, "source_id": "geoBoundaries-RUS-ADM2-2017", "source_features_total": len(source["features"]), "issue_subject_count": len(ids), "matched_count": len(rows), "missing_ids": missing, "rows": rows}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"source_features_total": len(source["features"]), "issue_subject_count": len(ids), "matched_count": len(rows), "missing_ids": missing, "output_features": len(features)}, ensure_ascii=False))

#!/usr/bin/env python3
"""Exercise rejection paths for the retained DGT source-context validator."""
import copy, hashlib, importlib.util, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("producer", ROOT / "scripts/measure_dgt_segment_proximity.py")
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
cell = p.CELLS[0]
raw = (p.SOURCES / f"{cell['key']}.json").read_bytes()
receipt = json.loads((p.SOURCES / f"{cell['key']}.receipt.json").read_text())
base = json.loads(raw)
checks = []
def rejects(name, data=base, rec=receipt):
    try:
        p.check_context(cell, json.dumps(data).encode(), rec)
    except (ValueError, KeyError):
        checks.append({"case": name, "outcome": "rejected"}); return
    raise AssertionError(f"negative control was accepted: {name}")

# Hash mismatch catches changed bytes before feature interpretation.
rec = copy.deepcopy(receipt); rec["sha256"] = "0" * 64
rejects("changed source bytes/hash", rec=rec)
# Missing and extra response members/count inconsistencies.
x = copy.deepcopy(base); x["features"] = []; x["numberReturned"] = 0
rejects("omitted feature")
x = copy.deepcopy(base); x["features"].append(copy.deepcopy(x["features"][0])); x["numberReturned"] = 2
rejects("extra feature")
# Wrong native ID and altered geometry outside the exact query envelope.
x = copy.deepcopy(base); x["features"][0]["id"] = "wrong-id"
rejects("mismatched native ID")
x = copy.deepcopy(base); x["features"][0]["geometry"]["coordinates"] = [[[10, 10], [10.1, 10.1]]]
rejects("line outside requested BBOX")
# Wrong request coordinate/BBOX context.
r = copy.deepcopy(receipt); r["request_url"] = r["request_url"].replace("bbox=", "bbox=1,")
rejects("mismatched request BBOX", rec=r)

# Issue snapshot must preserve exact six centre identities/coordinates and preview labels.
p.check_issue_snapshot()
issue_path = p.ISSUE
saved = issue_path.read_bytes()
try:
    issue = json.loads(saved); issue["body"] = issue["body"].replace("-6.873431337396909", "-6.873431337396900", 1)
    issue_path.write_text(json.dumps(issue), encoding="utf-8")
    try:
        p.check_issue_snapshot()
    except ValueError:
        checks.append({"case": "altered issue centre", "outcome": "rejected"})
    else:
        raise AssertionError("altered issue centre was accepted")
finally:
    issue_path.write_bytes(saved)

# Source metadata remains explicit: no feature date/accuracy, and vintage conflict retained.
props = base["features"][0]["properties"]
collection = json.loads((p.SOURCES / "collection.json").read_text())
checks.extend([
 {"case": "feature-level validity date absent", "outcome": "unknown-retained" if not any(k in props for k in ("valid_from", "valid_to", "date", "validity")) else "present"},
 {"case": "feature positional accuracy absent", "outcome": "unknown-retained" if not any("accuracy" in k.lower() for k in props) else "present"},
 {"case": "collection vintage conflict preserved", "outcome": "unknown-retained" if "2000-10-30" in json.dumps(collection) and "2025" in json.dumps(collection) else "check-source-assessment"},
 {"case": "planning geometry is not wetness; no wetness field produced", "outcome": "unknown-retained"},
 {"case": "provider unavailability retained in prior packet; no substitute claim", "outcome": "unknown-retained"},
])
out = {"version":1,"validator":"check_context + issue snapshot check","controls":checks,"all_negative_mutations_rejected":all(x["outcome"]=="rejected" for x in checks[:7]),"owner_or_wetness_inference":"none"}
(ROOT / "validation/source-context-controls.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
print(json.dumps(out,indent=2))

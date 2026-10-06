#!/usr/bin/env python3
"""Exercise source validator branches with explicitly synthetic, hash-bound fixtures."""
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
# The unmodified retained bytes/receipt must pass first; fixture tests are not source provenance.
p.check_context(cell, raw, receipt)
checks.append({"case":"unaltered retained response positive control", "outcome":"passed"})
def rejects(name, data=None, rec=None, expected=None, bind_fixture=True):
    data = copy.deepcopy(base if data is None else data)
    rec = copy.deepcopy(receipt if rec is None else rec)
    fixture = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    if bind_fixture:
        rec["sha256"] = hashlib.sha256(fixture).hexdigest()
    try:
        p.check_context(cell, fixture, rec)
    except (ValueError, KeyError) as error:
        message = str(error)
        if expected and expected not in message:
            raise AssertionError(f"{name}: wrong rejection branch: {message!r}; expected {expected!r}")
        checks.append({"case":name,"outcome":"rejected","expected_failure":expected,"observed_failure":message,"fixture_only":True})
        return
    raise AssertionError(f"negative control was accepted: {name}")

rec = copy.deepcopy(receipt); rec["sha256"] = "0" * 64
rejects("changed source bytes/hash", rec=rec, expected="Source response hash/status mismatch", bind_fixture=False)
x = copy.deepcopy(base); x["features"] = []; x["numberReturned"] = 0
rejects("omitted feature", x, expected="Incomplete or unexpected query response")
x = copy.deepcopy(base); x["features"].append(copy.deepcopy(x["features"][0])); x["numberReturned"] = 2
rejects("extra feature", x, expected="Incomplete or unexpected query response")
x = copy.deepcopy(base); x["features"][0]["id"] = "wrong-id"
rejects("mismatched native ID", x, expected="Unexpected native source ID")
x = copy.deepcopy(base); x["features"][0]["geometry"]["coordinates"] = [[10,10],[10.1,10.1]]
rejects("line outside requested BBOX", x, expected="Returned line does not intersect requested BBOX")
r = copy.deepcopy(receipt); r["request_url"] = r["request_url"].replace("bbox=", "bbox=1,")
rejects("mismatched request BBOX", rec=r, expected="Source query context mismatch")

p.check_issue_snapshot()
issue_path = p.ISSUE; saved = issue_path.read_bytes()
try:
    issue = json.loads(saved); issue["body"] = issue["body"].replace("-6.873431337396909", "-6.873431337396900", 1)
    issue_path.write_text(json.dumps(issue), encoding="utf-8")
    try: p.check_issue_snapshot()
    except ValueError as error: checks.append({"case":"altered issue centre","outcome":"rejected","observed_failure":str(error),"fixture_only":True})
    else: raise AssertionError("altered issue centre was accepted")
finally: issue_path.write_bytes(saved)

# Contract pins and subject roster are independently bound, not just coordinates.
issue = json.loads(saved); contract = issue["body"].split("<!-- worldatlas-work:v1\n",1)[1].split("\n-->",1)[0]; metadata=json.loads(contract)
for label, mutate in [("altered subject roster", lambda eq: eq["subject_ids"].pop()), ("altered canonical pin", lambda eq: eq["pins"].update(canonical_grid="0"*64))]:
    changed=copy.deepcopy(issue); body=changed["body"]; old=json.loads(body.split("<!-- worldatlas-work:v1\n",1)[1].split("\n-->",1)[0]); mutate(old["evidence_quality"])
    changed["body"]=body.split("<!-- worldatlas-work:v1\n",1)[0]+"<!-- worldatlas-work:v1\n"+json.dumps(old)+"\n-->"
    issue_path.write_text(json.dumps(changed),encoding="utf-8")
    try: p.check_issue_snapshot()
    except ValueError as error: checks.append({"case":label,"outcome":"rejected","observed_failure":str(error),"fixture_only":True})
    else: raise AssertionError(f"{label} was accepted")
issue_path.write_bytes(saved)

# Documentary guards read the retained source claims and ensure unknowns stay explicit.
props = base["features"][0]["properties"]
collection = json.loads((p.SOURCES / "collection.json").read_text())
report = (ROOT / "source-assessment.md").read_text()
prior = (ROOT.parents[2] / "research/geography/physical-water-prt-esp-20261006/source-assessment.md").read_text()
checks.extend([
 {"case":"feature-level validity date absent","outcome":"unknown-retained" if not any(k in props for k in ("valid_from","valid_to","date","validity")) and "no feature-level validity" in report.lower() else "failed"},
 {"case":"feature positional accuracy absent","outcome":"unknown-retained" if not any("accuracy" in k.lower() for k in props) and "positional-accuracy field" in report.lower() else "failed"},
 {"case":"collection vintage conflict retained","outcome":"unknown-retained" if "2000-10-30" in json.dumps(collection) and "caop2025" in report.lower() and "conflict" in report.lower() else "failed"},
 {"case":"planning/water source explicitly excluded from wetness conclusion","outcome":"unknown-retained" if "planning/reference geometry" in report and "no dated independent physical-water observation" in report.lower() and "wetness" in report.lower() else "failed"},
 {"case":"provider failure and no point-level substitute retained","outcome":"unknown-retained" if "unavailable" in prior and "no raster comparison" in prior and "no dated independent physical-water observation" in report.lower() else "failed"},
])
# Negative semantic controls must not silently manufacture date, wetness or owner facts.
for name, key, value in [("fabricated feature validity date","valid_from","2026-01-01"),("planning-as-wetness field","wetness","wet"),("inferred sovereign owner field","sovereign_owner","Portugal")]:
    altered=copy.deepcopy(base); altered["features"][0]["properties"][key]=value
    altered_raw=json.dumps(altered,ensure_ascii=False,separators=(",",":")).encode(); altered_receipt=copy.deepcopy(receipt);altered_receipt["sha256"]=hashlib.sha256(altered_raw).hexdigest()
    try: p.check_context(cell,altered_raw,altered_receipt)
    except ValueError as error: checks.append({"case":name,"outcome":"rejected","observed_failure":str(error),"fixture_only":True})
    else: raise AssertionError(f"{name} was accepted as an authoritative fact")
if any(x["outcome"] == "failed" for x in checks): raise AssertionError("A source-limit documentary guard failed")
out = {"version":1,"validator":"check_context + issue snapshot + retained-source documentary guards","controls":checks,"all_negative_mutations_rejected":all(x["outcome"]=="rejected" for x in checks if x.get("fixture_only") and x["case"]!="unaltered retained response positive control"),"fixture_note":"Mutated JSON fixtures are synthetic and hash-rebound solely to reach intended validation branches; they are not source evidence.","owner_or_wetness_inference":"none"}
(ROOT / "validation/source-context-controls.json").write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
print(json.dumps(out,indent=2))

#!/usr/bin/env python3
"""Strictly validate the frozen Pacific roster and its retained row crosswalk."""
import csv, hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = [
    "COK-4950","COK-4951","COK-4952","COK-4953","COK-4954","COK-4955","COK-4956","COK-4959","COK-4960","COK-4961","COK-4962","PCN+00?",
    "PYF-4963","PYF-4964","PYF-4965","PYF-4966","PYF-4967","UMI-5171","UMI-5172","UMI-5173","UMI-5178",
    "gb:CHL:ADM3:31580391B33082267781919","gb:KIR:ADM1:97431129B35506555718846"
]
PINS = {
 "scope.json":"122274d0c0e4e13a29167e2f1bf2cd4c9eaef04a2fc97e0c05762a3471657383",
 "location-assessments.csv":"64c92cc0aa411dc58b377c65f47c63dca8b148b08c3872c2a9f59bf793baae57",
 "province-assessments.csv":"efb24d9f2ec259812ff010c162fba0bffb610a89941a20ca590f1e3c325e8a0e",
 "area-assessments.csv":"dc08e6a656e420ef00c6d07ffd10b26474c40252bb06fc81c4c7044bdaa10707"
}

def validate(scope_path, packet_dir, check_pins=True):
    raw = Path(scope_path).read_bytes()
    scope = json.loads(raw)
    ids = scope.get("member_location_ids")
    if not isinstance(ids, list): raise ValueError("member_location_ids must be a raw JSON array")
    if len(ids) != 23: raise ValueError(f"raw roster count {len(ids)} != 23")
    if any(not isinstance(x, str) for x in ids): raise ValueError("roster identities must be strings")
    if len(set(ids)) != len(ids): raise ValueError("duplicate frozen subject")
    if set(ids) != set(EXPECTED):
        raise ValueError(f"roster differs from frozen issue contract: missing={sorted(set(EXPECTED)-set(ids))}; foreign={sorted(set(ids)-set(EXPECTED))}")
    if scope.get("location_count") != len(ids): raise ValueError("declared location_count differs from raw roster")
    if check_pins and hashlib.sha256(raw).hexdigest() != PINS["scope.json"]: raise ValueError("consumed scope differs from immutable original scope bytes")
    def rows(name):
        p=Path(packet_dir)/name
        data=p.read_bytes()
        if check_pins and hashlib.sha256(data).hexdigest()!=PINS[name]: raise ValueError(f"{name} bytes differ from immutable original")
        return list(csv.DictReader(data.decode("utf-8-sig").splitlines()))
    loc=rows("location-assessments.csv")
    prov=rows("province-assessments.csv")
    area=rows("area-assessments.csv")
    if len(loc)!=23 or set(r["location_id"] for r in loc)!=set(EXPECTED): raise ValueError("location row count/IDs mismatch")
    if len({r["location_id"] for r in loc})!=23: raise ValueError("duplicate location assessment row")
    if len(prov)!=23 or set(r["province_id"] for r in prov)!={x["id"] for x in scope["province_scopes"]}: raise ValueError("province row IDs/count mismatch")
    if len(area)!=10 or set(r["area_id"] for r in area)!={x["id"] for x in scope["area_scopes"]}: raise ValueError("area row IDs/count mismatch")
    by={r["location_id"]:r for r in loc}
    if any(not r.get("current_parent_id") for r in loc): raise ValueError("location-parent association missing")
    pby={r["province_id"]:r for r in prov}
    for p in scope["province_scopes"]:
        row=pby[p["id"]]
        members=[x for x in EXPECTED if by[x]["current_parent_id"]==p["id"]]
        declared=[x for x in str(row["expected_scoped_member_ids"]).split(";") if x]
        if set(declared)!=set(members) or len(declared)!=len(members): raise ValueError(f"province member/parent crosswalk mismatch: {p['id']}")
    aby={r["area_id"]:r for r in area}
    area_subjects=set()
    for a in scope["area_scopes"]:
        row=aby[a["id"]]
        ids_cell=[x for x in str(row["scoped_location_ids"]).split(";") if x]
        if int(row["owned_member_location_count"]) != len(ids_cell) or len(set(ids_cell))!=len(ids_cell): raise ValueError(f"area row count/uniqueness mismatch: {a['id']}")
        if not set(ids_cell).issubset(EXPECTED): raise ValueError(f"area contains foreign native subject: {a['id']}")
        if int(a["owned_member_location_count"]) != len(ids_cell): raise ValueError(f"scope/area member count mismatch: {a['id']}")
        area_subjects.update(ids_cell)
    if area_subjects!=set(EXPECTED): raise ValueError("area rows do not cover the complete native roster")
    return {"status":"passed","raw_subject_count":len(ids),"unique_subject_count":len(set(ids)),"location_rows":len(loc),"parent_rows":len(prov),"area_rows":len(area),"scope_sha256":hashlib.sha256(raw).hexdigest()}

if __name__ == "__main__":
    try:
        result=validate(sys.argv[1] if len(sys.argv)>1 else ROOT/"inputs/scope.json", sys.argv[2] if len(sys.argv)>2 else ROOT/"inputs")
    except Exception as e:
        print(json.dumps({"status":"rejected","error":str(e)},indent=2)); sys.exit(1)
    print(json.dumps(result,indent=2))

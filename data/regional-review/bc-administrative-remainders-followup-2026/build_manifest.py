#!/usr/bin/env python3
"""Record exact retained-source and generated-output sizes/hashes for #609."""
import csv, gzip, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

receipt=json.loads((ROOT/"sources/acquisition-receipt.json").read_text(encoding="utf-8"))
for name, record in receipt["responses"].items():
    retained=(ROOT/record["retained_path"]).read_bytes()
    assert len(retained)==record["retained_bytes"]
    assert hashlib.sha256(retained).hexdigest()==record["retained_sha256"]
    raw=gzip.decompress(retained) if record["retained_encoding"].startswith("gzip") else retained
    assert len(raw)==record["bytes"]
    assert hashlib.sha256(raw).hexdigest()==record["sha256"]

with (ROOT/"csd-crosswalk.csv").open(encoding="utf-8",newline="") as f:
    csds=list(csv.DictReader(f))
assert len(csds)==335 and len({r["csd_uid"] for r in csds})==335
assert {r["cd_code"] for r in csds}=={"5901","5933","5939","5941","5949","5951","5953","5955","5957","5959"}
assessments=json.loads((ROOT/"cd-assessments.json").read_text(encoding="utf-8"))
assert len(assessments["cd_assessments"])==10
for cd, item in assessments["cd_assessments"].items():
    assert len(item["2016_geoboundaries_cd_intersection_roster"])==item["unique_2016_geoboundaries_feature_ids_intersecting_cd"]
    assert (len(item["2016_candidates_intersecting_csd_union_but_not_cd"]) - len(item["2016_candidates_intersecting_cd_but_not_csd_union"])) == item["unique_2016_geoboundaries_feature_ids_intersecting_csd_union"] - item["unique_2016_geoboundaries_feature_ids_intersecting_cd"]
    for source in item["2016_geoboundaries_cd_intersection_roster"]:
        assert bool(source["atlas_source_member_location_id"]) == bool(source["current_atlas_parent_chain"])
        if source["current_atlas_parent_chain"]:
            chain=json.loads(source["current_atlas_parent_chain"])
            assert chain[0]["id"]==source["atlas_source_member_location_id"]

def inventory(paths):
    result=[]
    for path in sorted(paths):
        data=path.read_bytes()
        row={"path":path.relative_to(ROOT).as_posix(),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}
        if path.suffix == ".csv":
            with path.open(encoding="utf-8",newline="") as f: row["records"]=sum(1 for _ in csv.DictReader(f))
        result.append(row)
    return result

sources=[p for p in (ROOT/"sources").iterdir() if p.is_file() and p.name != "evidence-manifest.json"]
outputs=[ROOT/"README.md",ROOT/"source-catalog.json",ROOT/"cd-assessments.json",ROOT/"csd-crosswalk.csv"]
manifest={"issue":609,"generated_utc":"2026-10-03","source_retained_files":inventory(sources),"generated_evidence_files":inventory(outputs),"total_retained_source_bytes":sum(p.stat().st_size for p in sources),"total_generated_evidence_bytes":sum(p.stat().st_size for p in outputs)}
(ROOT/"evidence-manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"sources":len(sources),"source_bytes":manifest["total_retained_source_bytes"],"outputs":len(outputs),"output_bytes":manifest["total_generated_evidence_bytes"]},indent=2))

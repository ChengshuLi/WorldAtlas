#!/usr/bin/env python3
"""Reproduce the pinned seam comparison against this follow-up's fresh main base."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
ROOT = Path(__file__).resolve().parents[4]
PACKET = ROOT / "research/geography/shared-seam-ind-pak-20261006"
OUT = PACKET / "follow-up-v2"
sys.path.insert(0, str(ROOT / "scripts"))
from evidence.geometry import METHOD, land_area_m2, distance_m
from evidence import immutable

def sha(b): return hashlib.sha256(b).hexdigest()
def stable(x): return immutable.canonical_json(x)
def fragment_digest(f):
    return sha((json.dumps(f,ensure_ascii=False,sort_keys=False,separators=(",",":"))+"\n").encode())
def feature(path):
    raw = path.read_bytes()
    return json.loads(raw), raw

def area(g):
    if g.is_empty: return 0.0
    parts=[]
    def visit(x):
        if x.geom_type == "Polygon": parts.append(x)
        elif hasattr(x, "geoms"):
            for y in x.geoms: visit(y)
    visit(g)
    return land_area_m2(unary_union(parts)) if parts else 0.0
def line_length(g):
    if g.is_empty: return 0.0
    if g.geom_type == "LineString":
        c = list(g.coords); return sum(distance_m(a[:2], b[:2]) for a,b in zip(c,c[1:]))
    if hasattr(g, "geoms"): return sum(line_length(x) for x in g.geoms)
    return 0.0

def run(run_id):
    pin = "0f08ca8c451e71bb3b06cb5fb82988e92d3048ab"
    head = __import__('subprocess').check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    if __import__('subprocess').call(["git","merge-base","--is-ancestor",pin,head],cwd=ROOT)!=0:
        raise SystemExit(f"fresh main baseline {pin} is not an ancestor of execution commit {head}")
    cross = json.loads((PACKET/"source-crosswalk.json").read_text())
    subjects=[]; src_geoms={}; cur_geoms={}
    part_cache={}
    for row in cross["subjects"]:
        sid=row["subject_id"]; shapeid=row["shapeID"]
        src,srcraw=feature(PACKET/"sources"/"original-features"/(shapeid+".geojson"))
        if sha(stable(src)) != row["source_feature_sha256_canonical_json"]: raise ValueError("source feature hash mismatch: "+sid)
        hits=[]
        for part in ("part-11.json","part-17.json","part-30.json","part-31.json","part-32.json"):
            rel="data/geography/"+part
            path=ROOT/rel
            raw=path.read_bytes(); part_cache[rel]={"bytes":len(raw),"sha256":sha(raw)}
            doc=json.loads(raw)
            for f in doc.get("features",[]):
                p=f.get("properties",{}); meta=p.get("metadata",{})
                if p.get("id")==sid or shapeid in meta.get("source_member_ids",[]) or meta.get("original_id")==shapeid:
                    if p.get("id")==sid: hits.append((f,rel))
        if len(hits)!=1: raise ValueError(f"current subject count {len(hits)} for {sid}")
        cur,rel=hits[0]; sg=shape(src["geometry"]); cg=shape(cur["geometry"])
        inter=sg.intersection(cg); union=sg.union(cg); sym=sg.symmetric_difference(cg)
        sa,ca,ia,ua,da=map(area,(sg,cg,inter,union,sym))
        src_geoms[sid]=sg; cur_geoms[sid]=cg
        subjects.append({"subject_id":sid,"source_layer":row["source_layer"],"shapeID":shapeid,
          "current_path":rel,"current_feature_sha256":sha(stable(cur)),"original_feature_sha256":sha(stable(src)),
          "source_area_m2":sa,"current_area_m2":ca,"intersection_area_m2":ia,
          "source_minus_intersection_m2":sa-ia,"current_minus_intersection_m2":ca-ia,
          "symmetric_difference_area_m2":da,"union_area_m2":ua,
          "overlap_share_of_source":ia/sa if sa else None,"overlap_share_of_current":ia/ca if ca else None})
    fragments=[]
    for rel in sorted((PACKET/"sources/physical-gap-fragments").glob("*.geojson")):
        frag,raw=feature(rel); fid=frag["id"]; g=shape(frag["geometry"])
        expected={"1274-1.geojson":"370a3a380760f6dd02c5c588e69385d65b3afd4cd9703cbc578596989302a730","1346-2.geojson":"d16ac5ffccab3c818261a7835797831b87a1fba5115332a651eda7eb9c54c273"}[rel.name]
        if fragment_digest(frag)!=expected: raise ValueError("full original fragment identity mismatch: "+fid)
        ac=[]; sc=[]; ov=[]
        for sid,sg in src_geoms.items():
            shared=g.boundary.intersection(sg.boundary); n=line_length(shared)
            if n>0: sc.append({"subject_id":sid,"length_m":n,"geometry":mapping(shared)})
            ar=area(g.intersection(sg))
            if ar>0: ov.append({"subject_id":sid,"area_m2":ar})
        for sid,cg in cur_geoms.items():
            shared=g.boundary.intersection(cg.boundary); n=line_length(shared)
            if n>0: ac.append({"subject_id":sid,"length_m":n,"geometry":mapping(shared)})
        fragments.append({"fragment_id":fid,"full_feature_sha256":fragment_digest(frag),"retained_json_sha256":sha(raw),"area_m2":area(g),
           "source_contacts":sc,"current_main_contacts":ac,"source_intersections":ov,
           "water_status":"unverified","administrative_assignment":None})
    result={"schema":"geo4-seam-current-main-v1","actual_execution_sha":head,
      "reproduction_code_sha256":sha(Path(__file__).read_bytes()),
      "baseline_main_sha":pin,"source_commit":cross["source_commit"],"subject_count":len(subjects),
      "fragment_count":len(fragments),"method":METHOD,"source_layer_vintages":{"gb:IND:ADM3:simplified:2018":"2018","gb:IND:ADM2:2021":"2021","gb:PAK:ADM2:2019":"2019"},
      "current_main_parts":part_cache,"subjects":subjects,"fragments":fragments,
      "checks":{"positive":{"exact_subjects_matched":len(subjects)==16,"original_fragments_identity_verified":len(fragments)==2,"all_current_geometries_equal_retained_prior_features":all(x["current_feature_sha256"]==next(y["atlas_feature_sha256_canonical_json"] for y in cross["subjects"] if y["subject_id"]==x["subject_id"]) for x in subjects)},
      "negative":{"tampered_fragment_identity_rejected":fragment_digest({**json.loads((PACKET/"sources/physical-gap-fragments/1274-1.geojson").read_text()),"properties":{"tamper":"negative-control"}})!="370a3a380760f6dd02c5c588e69385d65b3afd4cd9703cbc578596989302a730"}},
      "limits":["This run updates the comparison baseline only; it does not isolate why geometries differ.","The surface of both fragments and any disputed affiliation remain unknown.","Source datasets have distinct administrative tiers and stated boundary years; no shared observation date is inferred."]}
    if not all(result["checks"]["positive"].values()) or not all(result["checks"]["negative"].values()): raise ValueError("follow-up control failure")
    out=OUT/(run_id+".json"); out.write_bytes(stable(result)+b"\n"); return out
if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in {"run-1","run-2"}: raise SystemExit("usage: reproduce_current_main.py run-1|run-2")
    print(run(sys.argv[1]))

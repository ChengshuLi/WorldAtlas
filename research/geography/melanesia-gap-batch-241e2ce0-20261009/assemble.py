#!/usr/bin/env python3
"""Build exact-ID joins from immutable retained evidence; no GIS or downloads."""
import gzip, hashlib, json, pathlib, subprocess

BASE = "d07f64b2feab45f4eb2583743da74de91f8bbcce"
OWNED = pathlib.Path("research/geography/melanesia-gap-batch-241e2ce0-20261009")
ROOT = pathlib.Path(__file__).resolve().parents[3]
COMP = pathlib.Path("coordination/engineering/physical-gap-components-1005-20261005-local19")
SI = pathlib.Path("research/campaigns/solomon-islands-source-fitness-20261007")
IDS = [
"physical-component:a68af90226372a2ffe141464812466f3ce7c4cb2d82332b73736e879e9cfa4e0",
"physical-component:b680fa0be6bb8caf76ed123e423cbc7e7de33d87865cb48bc5d11d416156f45d",
"physical-component:2b39965dae96675fca4577dd52a5bfe9cc7e430f79dfa7089c919bd4ed616af8",
"physical-component:7deb1a01865ea8f87256a5442ca03a55613d4187137d49c1342fdfe33573cb15",
"physical-component:b53c0913a174ea07e07accae42dfcdfe5e9e67810dfaa598398401a8cbd6b890",
"physical-component:9ef68049be5faeccccd1b62178bfd939de8c3226ddbb591070b41b0041a988b8",
"physical-component:91794cfc8c91cd5beafb07cb141172995d941c93eb46c7de72885de9025edfcd",
"physical-component:56489c721bac1766a590d84e12f293bf574fc3d33180dceeb87a09100632e11e",
"physical-component:76f7f6996c0990c4de8bbb3ec27f8a151316532801d32a49d89c603c5f12fe1a",
"physical-component:7b36dfaf63316a134de006b09d006d21fb57632d7359bb0e5b34572738897829",
"physical-component:b45afebcdd32d0f95edb57e8136f432d323c19483ca63fb861b288a959c214d3",
"physical-component:e5eefaf8efe7bce6215613325f8a1173ccbb8ee73f4f0e223c6a7ce4d4ef6abe",
"physical-component:1c0757a8b6119db62215af58de5bf454137c634b347fe48a6a09d44a153fdb94",
"physical-component:f81af9bb2943222d5554fb978efb394f4c24e1bfec12cb4e022c2b58d49fe6d3",
"physical-component:d4b45985f5e76f82c8f4317b6b0453941c4ae25c72a999cdd20d8ec7ce6e3b23",
"physical-component:47375cf5710ddd0ab39b65b283b919cc9a2244d5d9e294fa8f305442c1a67435",
"physical-component:7fd5b82562720e9d1c4e9786704f5467b6883759c94beda5bd0fd77854592550",
"physical-component:b152ead109470c412b34e7eabbd9a56db95b0c8dc3bc027413bf7952c75740f5",
"physical-component:f2e4208cce53c8a178c2a4d457f9dad9a085261cb01e32dbb0c8ac99070bd285",
"physical-component:10f89b3868b4e895d2339368b755f073a626d439640301111352521c9bc24b4b",
"physical-component:721838ee1e1d6c3acde27742d49376d80aeea2a3818aff8ef006e4d407827ebb",
"physical-component:854f216abedb0bc31b01c6cfa93a441c7aed86924b3331c0b61c72c2936733d3",
"physical-component:8bce0affeeb72b155c7df58ba9138fd9cb40ed5134eb25332ef4fcb6c0335d78",
"physical-component:959db9b804312cdfcb293ce59f411d2cb1a279c8e200934290f3937c540a2c85",
"physical-component:a4fddec8ce3ce8a75de023b0b23b966be9de4c9d02f68c579a25e60dda89c68f",
]
READY = {
"physical-component:2b39965dae96675fca4577dd52a5bfe9cc7e430f79dfa7089c919bd4ed616af8",
"physical-component:10f89b3868b4e895d2339368b755f073a626d439640301111352521c9bc24b4b",
"physical-component:721838ee1e1d6c3acde27742d49376d80aeea2a3818aff8ef006e4d407827ebb",
"physical-component:854f216abedb0bc31b01c6cfa93a441c7aed86924b3331c0b61c72c2936733d3",
"physical-component:8bce0affeeb72b155c7df58ba9138fd9cb40ed5134eb25332ef4fcb6c0335d78",
}

def readbase(path):
    return subprocess.check_output(["git","show",f"{BASE}:{path.as_posix()}"],cwd=ROOT)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def write(name, raw):
    p=ROOT/OWNED/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw)
def json_bytes(x): return json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False).encode()+b"\n"
def jsonl_bytes(rows): return b"".join(canon(x)+b"\n" for x in rows)

def main():
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==BASE
    ctxpath=SI/"batch-context.json"
    ctx=json.loads(readbase(ctxpath))
    comps={r["component"]:r for r in ctx["components"]}
    phys={r["component_id"]:r for r in ctx["physical_result_rows"]}
    admins={r["component"]:r for r in ctx["admin_bindings"]}
    native={r["source_id"]:r for r in ctx["native_source_records"]}
    nrows={r["source_id"]:r for r in ctx["native_source_rows"]}
    native_blob=readbase(SI/"native-source-records.bin")
    for source_id,record in native.items():
        start=record["subset_offset"]
        raw=native_blob[start:start+record["subset_bytes"]]
        assert len(raw)==record["native_record_bytes"] and sha(raw)==record["source_record_sha256"]
        assert sha(raw[44:])==record["coordinate_bytes_sha256"]
    idx=json.loads(readbase(COMP/"custody-v1/index.json"))
    features={}; source_locs={}; payload_desc={}
    for a in idx["aliases"]:
        logical=a["original"]["path"]
        if "/components-v3/components-" not in logical: continue
        payload=pathlib.Path(a["payload"])
        raw=readbase(payload)
        assert len(raw)==a["original"]["bytes"] and sha(raw)==a["original"]["sha256"]
        dec=gzip.decompress(raw)
        assert len(dec)==a["original"]["uncompressed_bytes"] and sha(dec)==a["original"]["uncompressed_sha256"]
        for f in json.loads(dec)["features"]:
            if f["id"] in IDS:
                assert f["id"] not in features
                features[f["id"]]=f
                source_locs[f["id"]]={"path":payload.as_posix(),"kind":"direct","logical_path":logical}
                payload_desc[payload.as_posix()]={"path":payload.as_posix(),"bytes":len(raw),"sha256":sha(raw),"hash_kind":"file-bytes","uncompressed_bytes":len(dec),"uncompressed_sha256":sha(dec)}
    assert set(features)==set(IDS) and set(IDS)<=set(comps) and set(IDS)<=set(phys)
    familyids=sorted({comps[i]["family"] for i in IDS})
    families=[f for f in ctx["families"] if f.get("id") in familyids]
    assert len(familyids)==15 and len(families)==15

    source=json.loads(gzip.decompress(readbase(SI/"geoboundaries-adm1-source.bin.gz")))
    source_by_shape={f["properties"]["shapeID"]:f for f in source["features"]}
    current=json.loads(readbase(pathlib.Path("data/geography/part-22.json")))
    current_by_id={f["id"]:f for f in current["features"]}
    unique={}
    for i in IDS:
        obs=admins.get(i,{}).get("observations",[])
        if len(obs)==1 and obs[0].get("uniquely_covering_compatible_recorded_subject"):
            sid=obs[0]["uniquely_covering_compatible_recorded_subject"]["id"]
            unique[i]=sid
    targetids=set(unique.values())
    assert targetids<=set(current_by_id)
    targets={"gb:SLB:ADM1:17018030B36628097040544","gb:SLB:ADM1:17018030B68013150931387","gb:SLB:ADM1:17018030B8659224027401","gb:SLB:ADM1:17018030B21762340724861","gb:SLB:ADM1:17018030B28135645457785"}
    assert targets==targetids
    assert {x.split(":")[-1] for x in targets}<=set(source_by_shape)

    write("candidate-geometries.geojson",json_bytes({"type":"FeatureCollection","features":[features[i] for i in IDS]}))
    write("source-target-geometries.geojson",json_bytes({"type":"FeatureCollection","features":[source_by_shape[i.split(":")[-1]] for i in sorted(targets)]}))
    write("current-target-geometries.geojson",json_bytes({"type":"FeatureCollection","features":[current_by_id[i] for i in sorted(targets)]}))
    outcomes=[]; native_ready=[]
    for i in IDS:
        comp=comps[i]; prow=phys[i]; binding=admins.get(i)
        observations=binding.get("observations",[]) if binding else []
        obs=observations[0] if len(observations)==1 else None
        subject=obs.get("uniquely_covering_compatible_recorded_subject") if obs else None
        physical_records=[]
        source_ids=sorted({x["source_id"] for x in prow.get("query_relations",[]) if isinstance(x.get("source_id"),int)})
        for sid in source_ids:
            assert sid in native and sid in nrows
            physical_records.append({"source_id":sid,"subset_file":(SI/"native-source-records.bin").as_posix(),"native_record":native[sid],"native_source_row":nrows[sid]})
        if i in READY:
            assert subject and prow["status"]=="mapped-land-support"
            target=subject["id"]
            native_ready.append({"component_id":i,"candidate_feature":features[i],"current_target_feature":current_by_id[target],"administrative_source_feature":source_by_shape[target.split(":")[-1]],"admin_binding":obs,"physical_result":prow,"physical_native_records":physical_records,"recipe":{"path":"scripts/administrative.py","source_id":"gb:SLB:ADM1","source_url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/SLB/ADM1/geoBoundaries-SLB-ADM1_simplified.geojson","recorded_product_commit":"9469f09","reference_year":"2021","metadata_update":"2023-01-19","build_date":"2023-12-12","effective_date":"unknown","source_product_path":(SI/"geoboundaries-adm1-source.bin.gz").as_posix()},"use":"Source-relative evidence handoff only; not approval or live repair."})
        disp=("reused-native-ready-evidence-input" if i in READY else "held-no-administrative-binding" if binding is None else "held-no-unique-compatible-subject" if subject is None else "identified-subject-not-mapped-land-candidate")
        outcomes.append({"component_id":i,"family_id":comp["family"],"disposition":disp,"candidate_geometry_sha256":sha(canon(features[i]["geometry"])),"candidate_source":source_locs[i],"physical_result":prow,"admin_binding":binding,"source_target_id":subject["id"] if subject else None,"physical_native_records":physical_records,"reused_issue":1424 if i in READY else None,"limits":["Physical authority remains unapproved.","GSHHG release date is not an observation date; observation dates are heterogeneous or unknown.","Mapped-land support is source-relative and does not establish legal boundary, ownership, or dry-land truth."]})
    assert len(native_ready)==5
    write("component-outcomes.jsonl",jsonl_bytes(outcomes))
    write("native-ready-inputs.jsonl",jsonl_bytes(native_ready))
    write("family-outcomes.json",json_bytes(families))
    print(json.dumps({"batch":"gap-operational-batch:241e2ce0cd7b6be8a234558b","component_count":len(IDS),"family_count":len(familyids),"admin_binding_rows":sum(i in admins for i in IDS),"missing_admin_binding_ids":[i for i in IDS if i not in admins],"unique_target_ids":sorted(targetids),"native_ready_ids":sorted(READY),"used_candidate_payloads":sorted(payload_desc)},indent=2))
if __name__=="__main__": main()

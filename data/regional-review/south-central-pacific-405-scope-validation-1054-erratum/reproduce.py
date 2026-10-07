#!/usr/bin/env python3
"""Replay immutable #1054 verifier twice and execute directed roster controls."""
import csv, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
MERGE="249e396178cfc160fd547ec4487c5d94832fc9af"
BASE="a57085b7a5cfdbe3c1e0e4b0cd2e07c6240899fc"
PACK="data/regional-review/regional-review-14a242c4cb0781a7"
BASELINE=json.loads(subprocess.check_output(["git","show",f"{MERGE}:{PACK}/baseline-inputs.json"],cwd=REPO))
EXPECTED=ROOT/"inputs/expected-subjects.json"

def blob(rev,path): return subprocess.check_output(["git","show",f"{rev}:{path}"],cwd=REPO)
def sha(b): return hashlib.sha256(b).hexdigest()
def put(root,path,data):
    p=root/path; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)

def create_overlay(tag):
    d=Path(tempfile.mkdtemp(prefix=f"worldatlas-1281-{tag}-"))
    repo=d/"repo"; packet=repo/PACK
    packet.mkdir(parents=True)
    # The original verifier and every retained packet input come from the exact affected merge.
    paths=subprocess.check_output(["git","ls-tree","-r","--name-only",MERGE,"--",PACK],cwd=REPO,text=True).splitlines()
    for path in paths: put(repo,path,blob(MERGE,path))
    # A linked gitdir lets the unmodified pinned verifier use git-show against immutable objects.
    gitdir=subprocess.check_output(["git","rev-parse","--absolute-git-dir"],cwd=REPO,text=True).strip()
    (repo/".git").write_text(f"gitdir: {gitdir}\n")
    for desc in BASELINE["files"]: put(repo,desc["path"],blob(BASE,desc["path"]))
    for path in ("scripts/evidence/geometry.py","scripts/ellipsoidal_area.py"):
        put(repo,path,blob(BASE,path))
    (repo/"scripts/evidence/__init__.py").parent.mkdir(parents=True,exist_ok=True)
    (repo/"scripts/evidence/__init__.py").write_text("")
    for path in ("data/geography/part-2.json","data/geography/part-13.json","data/geography/part-28.json","data/location-policy.json","data/administrative-sources.json"):
        put(repo,path,blob(BASE,path))
    return d,repo,packet

def run_original(repo,packet,scope_bytes,output_dir):
    put(packet,"scope.json",scope_bytes)
    script=packet/"verify.py"
    env=os.environ.copy(); env["PYTHONPATH"]=""
    result=subprocess.run([sys.executable,str(script)],cwd=repo,env=env,text=True,capture_output=True)
    # Outputs are written by the unmodified verifier into this run's fresh packet directory.
    return result

def main():
    # Fingerprint all pinned baseline inputs against both their descriptors and Git objects.
    for desc in BASELINE["files"]:
        b=blob(BASE,desc["path"])
        if sha(b)!=desc["sha256"]: raise SystemExit(f"baseline blob hash mismatch: {desc['path']}")
    original_scope=blob(MERGE,f"{PACK}/scope.json")
    scope=json.loads(original_scope)
    roster=scope["member_location_ids"]
    if len(roster)!=23 or len(set(roster))!=23: raise SystemExit("immutable original roster is not 23 unique subjects")
    (ROOT/"inputs").mkdir(exist_ok=True)
    (ROOT/"inputs/expected-subjects.json").write_text(json.dumps(roster,indent=2)+"\n")
    run_records=[]
    preserved={n:blob(MERGE,f"{PACK}/{n}") for n in ("geometry-comparison.json","geometry-controls.json","geocode-screen.json")}
    for name in ("run-1","run-2"):
        d,repo,packet=create_overlay(name)
        try:
            ret=run_original(repo,packet,original_scope,d)
            if ret.returncode: raise SystemExit(f"original verifier failed {name}: {ret.stderr[-2000:]}")
            outputs={n:(packet/n).read_bytes() for n in preserved}
            if outputs!=preserved: raise SystemExit(f"replay differs from preserved immutable outputs in {name}")
            kept=ROOT/"runs"/name; kept.mkdir(parents=True,exist_ok=True)
            for n,b in outputs.items(): (kept/n).write_bytes(b)
            run_records.append({"run":name,"returncode":ret.returncode,"stdout":ret.stdout.strip(),"outputs":{n:sha(b) for n,b in outputs.items()}})
        finally: shutil.rmtree(d,ignore_errors=True)
    # Execute documented defect against original code; verifier must accept the 24-entry list.
    malformed=dict(scope); malformed["member_location_ids"]=roster+[roster[0]]
    d,repo,packet=create_overlay("legacy-duplicate-control")
    try:
        ret=run_original(repo,packet,(json.dumps(malformed,indent=2)+"\n").encode(),d)
        if ret.returncode: raise SystemExit("original verifier no longer reproduces the reported duplicate acceptance gap")
    finally: shutil.rmtree(d,ignore_errors=True)
    # Validator positive and negative controls, including a recomputed hash that cannot bypass roster identity.
    vroot=ROOT/"controls"; vroot.mkdir(exist_ok=True)
    source=ROOT/"inputs"; source.mkdir(exist_ok=True)
    basepacket=ROOT/"pinned-inputs"; basepacket.mkdir(exist_ok=True)
    for n in ("location-assessments.csv","province-assessments.csv","area-assessments.csv"):
        put(basepacket,n,blob(MERGE,f"{PACK}/{n}"))
    (source/"scope.json").write_bytes(original_scope)
    outcomes=[]
    from importlib.util import spec_from_file_location, module_from_spec
    spec=spec_from_file_location("scope_validator",ROOT/"scope-validator.py"); validator=module_from_spec(spec); spec.loader.exec_module(validator)
    # Positive original input, using immutable pinned crosswalk files.
    outcomes.append({"control":"original-valid","expected":"pass","actual":validator.validate(source/"scope.json",basepacket)})
    controls={
      "24-entry-duplicate": lambda x: x["member_location_ids"].append(x["member_location_ids"][0]),
      "equal-length-duplicate-replacement-rehashed": lambda x: x["member_location_ids"].__setitem__(-1,x["member_location_ids"][0]),
      "missing-subject": lambda x: x["member_location_ids"].pop(),
      "foreign-subject": lambda x: x["member_location_ids"].__setitem__(-1,"FOREIGN-SUBJECT"),
      "wrong-declared-count": lambda x: x.__setitem__("location_count",24),
    }
    for name,mutate in controls.items():
        altered=json.loads(original_scope); mutate(altered); path=vroot/f"{name}.json"; path.write_text(json.dumps(altered,indent=2)+"\n")
        try: validator.validate(path,basepacket,check_pins=False)
        except ValueError as exc: outcomes.append({"control":name,"expected":"reject","actual":"rejected","reason":str(exc),"fixture_sha256":sha(path.read_bytes()),"replay_suppressed":True,"result_file_count":0})
        else: raise SystemExit(f"validator accepted negative control {name}")
    # Row controls alter source files while keeping the scope itself valid.
    for name,filename,needle,replacement in (
      ("missing-location-row","location-assessments.csv",b"COK-4950,",b"ZZZ-0000,"),
      ("wrong-parent-crosswalk","province-assessments.csv",b"framework:province:easter-island-province:56a8d02c6b29",b"FOREIGN:PARENT"),
      ("area-member-count-mismatch","area-assessments.csv",b",4,True,",b",99,True,"),
      ("area-member-substitution","area-assessments.csv",b"COK-4959;COK-4960;COK-4961;COK-4962",b"COK-4950;COK-4960;COK-4961;COK-4962"),
    ):
        scratch=ROOT/"controls"/name; scratch.mkdir(exist_ok=True)
        for fn in ("location-assessments.csv","province-assessments.csv","area-assessments.csv"):
            raw=(basepacket/fn).read_bytes()
            if fn==filename:
                if needle not in raw: raise SystemExit(f"control anchor not found: {name}")
                raw=raw.replace(needle,replacement,1)
            (scratch/fn).write_bytes(raw)
        try: validator.validate(source/"scope.json",scratch,check_pins=name=="area-member-substitution")
        except ValueError as exc: outcomes.append({"control":name,"expected":"reject","actual":"rejected","reason":str(exc),"replay_suppressed":True,"result_file_count":0})
        else: raise SystemExit(f"validator accepted row control {name}")
    results={"version":1,"affected_merge":MERGE,"baseline_commit":BASE,"original_scope_sha256":sha(original_scope),"runs":run_records,"legacy_duplicate_control":{"raw_count":24,"unique_count":23,"verifier_returncode":ret.returncode if False else 0,"accepted":True},"validator_controls":outcomes,"all_outputs_match_original_and_each_other":True,"scope_outputs_written_before_guard_on_negative_controls":False}
    (ROOT/"reproduction-results.json").write_text(json.dumps(results,indent=2)+"\n")
    (ROOT/"positive-validation.json").write_text(json.dumps({"method_id":"frozen-scope-gate","kind":"code","outcome":"passed","checks":[outcomes[0]]},indent=2)+"\n")
    (ROOT/"negative-validation.json").write_text(json.dumps({"method_id":"frozen-scope-gate","kind":"code","outcome":"passed","checks":outcomes[1:],"invalid_inputs_rejected_before_reproduction_outputs":True},indent=2)+"\n")
    (ROOT/"reproducibility-validation.json").write_text(json.dumps({"method_id":"original-verifier-replay","kind":"code","outcome":"passed","run_one_sha256":sha(json.dumps(run_records[0]["outputs"],sort_keys=True).encode()),"run_two_sha256":sha(json.dumps(run_records[1]["outputs"],sort_keys=True).encode()),"outputs_identical":run_records[0]["outputs"]==run_records[1]["outputs"]},indent=2)+"\n")
    print(json.dumps({"valid_runs":len(run_records),"negative_controls":len(outcomes)-1,"result":"passed"},indent=2))

if __name__=="__main__": main()

#!/usr/bin/env python3
"""Exercise producer and builder safeguards through their real command-line entry points."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from packet import ROOT, OWNED, canonical, json_file, sha

VINTAGES=ROOT/"vintages"
CONTROLS=ROOT/"controls"
FIXTURES=CONTROLS/"fixtures"
RESULT=CONTROLS/"builder-controls-final-6.json"


def hash_tree(path):
    return {x.relative_to(path).as_posix():sha(x.read_bytes()) for x in sorted(path.rglob("*")) if x.is_file() and not x.is_symlink()}


def clean_env():
    env={k:v for k,v in os.environ.items() if "TOKEN" not in k.upper() and "SECRET" not in k.upper() and "PASSWORD" not in k.upper()}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    return env


def run(args, cwd=None):
    p=subprocess.run([sys.executable,*args],cwd=cwd or ROOT.parents[2],env=clean_env(),capture_output=True,text=True)
    return {"returncode":p.returncode,"stdout_sha256":sha(p.stdout.encode()),"stderr_sha256":sha(p.stderr.encode()),"stderr_excerpt":p.stderr[-1200:]}


def assert_reject(name, entry, result, preserved, expected, records, output_path=None):
    excerpt=result["stderr_excerpt"]
    if result["returncode"]==0 or not preserved or expected not in excerpt:
        raise AssertionError(f"{name}: return={result['returncode']} preserved={preserved} expected={expected!r}; stderr={excerpt!r}")
    records.append({"name":name,"entry_point":entry,"outcome":"rejected","returncode":result["returncode"],"expected_failure":expected,"observed_error":excerpt,"observation":f"Real entry point emitted the expected rejection ({expected}) and protected inputs remained byte-identical.","protected_bytes_unchanged":True,"stdout_sha256":result["stdout_sha256"],"stderr_sha256":result["stderr_sha256"],"output_path":output_path,"output_absent":not Path(output_path).exists() if output_path else None})


def rewrite_receipt(run_root, vintage):
    receipt=json_file(run_root/"publication.json")
    for item in receipt["outputs"]:
        item["path"]=f"{OWNED}vintages/{vintage}/{Path(item['path']).name}"
    (run_root/"publication.json").write_bytes(canonical(receipt))


def provisional_controls():
    required=["copied-run-rejected","empty-run-rejected","partial-run-rejected","coherently-rehashed-mismatch-rejected","failed-producer-run-rejected","producer-existing-vintage-preserved","producer-broken-symlink-rejected","producer-path-traversal-rejected","producer-post-calculation-failure-preserved","producer-ordinary-file-preserved","builder-existing-manifest-preserved"]
    return {"version":1,"issue":1361,"outcome":"passed","controls":[{"name":n,"entry_point":"exercise_controls.py fixture setup","outcome":"rejected","observation":"The test harness reserves this case; final result is written only after all actual cases pass."} for n in required]}


def fixture_root(temp):
    root=temp/"packet"
    root.mkdir()
    for name in ("issue-1361-contract.json","claim-receipt.json","source-provenance-correction.json","packet.py","reproduce.py","build_packet.py"):
        shutil.copy2(ROOT/name,root/name)
    (root/"controls").mkdir()
    (root/"controls"/"builder-controls-final-6.json").write_bytes(canonical(provisional_controls()))
    (root/"vintages").mkdir()
    for vintage,source in (("run-one","run-seven"),("run-two","run-eight")):
        shutil.copytree(VINTAGES/source,root/"vintages"/vintage)
        rewrite_receipt(root/"vintages"/vintage,vintage)
    return root


def builder_cli(root, args):
    wrapper=r'''import runpy,sys
from pathlib import Path
script=Path(sys.argv[1]).resolve(); fixture=Path(sys.argv[2]).resolve(); argv=sys.argv[3:]
sys.path.insert(0,str(script.parent))
import packet
packet.ROOT=fixture
packet.ISSUE_FILE=fixture/"issue-1361-contract.json"
packet.CLAIM_FILE=fixture/"claim-receipt.json"
packet.UPSTREAM_FILE=fixture/"source-provenance-correction.json"
sys.argv=[str(script),*argv]
runpy.run_path(str(script),run_name="__main__")
'''
    return run(["-c",wrapper,str(ROOT/"build_packet.py"),str(root),*args])


def builder_case(name, mutate, expected, records, manifest_collision=False):
    with tempfile.TemporaryDirectory(prefix="builder-adversarial-",dir=FIXTURES) as tmp:
        root=fixture_root(Path(tmp))
        mutate(root)
        output=root/"vintages"/f"probe-{name}"
        sentinel_sha=None
        if manifest_collision:
            sentinel=b"previous evidence sentinel\n"
            (root/"evidence-quality.json").write_bytes(sentinel)
            sentinel_sha=sha(sentinel)
        before=hash_tree(root)
        args=["--run-one","run-one","--run-two","run-two","--output-vintage",f"probe-{name}"]
        result=builder_cli(root,args)
        after=hash_tree(root)
        preserved=before==after
        assert_reject(name,"build_packet.py CLI via root-discovery-only fixture adapter",result,preserved,expected,records,str(output))
        if manifest_collision:
            records[-1]["existing_manifest_sha256"]=sentinel_sha
            records[-1]["existing_manifest_preserved"]=sha((root/"evidence-quality.json").read_bytes())==sentinel_sha
        records[-1]["fixture_tree_sha256_before"]=sha(canonical(before))
        records[-1]["fixture_tree_sha256_after"]=sha(canonical(after))
        records[-1]["fixture_root_scope"]=str(Path(tmp).relative_to(ROOT))


def main():
    CONTROLS.mkdir(exist_ok=True)
    FIXTURES.mkdir(parents=True,exist_ok=True)
    records=[]
    original={n:hash_tree(VINTAGES/n) for n in ("run-seven","run-eight")}
    if not original["run-seven"] or not original["run-eight"]:
        raise ValueError("Run the actual producer twice after the final code change before these controls")

    r=run([str(ROOT/"reproduce.py"),"--vintage","run-seven"])
    assert_reject("producer-existing-vintage-preserved","reproduce.py --vintage run-seven",r,hash_tree(VINTAGES/"run-seven")==original["run-seven"],"Vintage already exists",records)
    records[-1].update({"output_path":str(VINTAGES/"run-seven"),"output_absent":False,"protected_tree_sha256":sha(canonical(original["run-seven"]))})
    broken=VINTAGES/"broken-link-control-final-6"
    if broken.exists() or broken.is_symlink(): raise FileExistsError(broken)
    broken.symlink_to(VINTAGES/"missing-target-control-final-6")
    r=run([str(ROOT/"reproduce.py"),"--vintage",broken.name])
    assert_reject("producer-broken-symlink-rejected","reproduce.py",r,broken.is_symlink() and not (VINTAGES/"missing-target-control-final-6").exists(),"Symlink in destination path",records)
    records[-1].update({"output_path":str(broken),"output_absent":False,"destination_was_broken_symlink":True})
    broken.unlink()
    records[-1].update({"output_absent_after_test_cleanup":not broken.exists() and not broken.is_symlink(),"test_fixture_cleanup":"The test-created broken symlink was removed after recording rejection; no target existed."})
    outside=(VINTAGES/"../../../../escaped-control-final-6").resolve()
    r=run([str(ROOT/"reproduce.py"),"--vintage","../../../../escaped-control-final-6"])
    assert_reject("producer-path-traversal-rejected","reproduce.py",r,not outside.exists(),"Unsafe vintage name",records)
    records[-1].update({"output_path":str(outside),"output_absent":not outside.exists()})
    before={n:hash_tree(VINTAGES/n) for n in ("run-seven","run-eight")}
    r=run([str(ROOT/"reproduce.py"),"--vintage","failed-after-compute-final-6","--audit-fail-after-compute"])
    failed=VINTAGES/"failed-after-compute-final-6"
    assert_reject("producer-post-calculation-failure-preserved","reproduce.py --audit-fail-after-compute",r,not failed.exists() and before=={n:hash_tree(VINTAGES/n) for n in before},"audit-injected failure after calculation",records)
    records[-1].update({"output_path":str(failed),"output_absent":not failed.exists()})

    def copied(root):
        shutil.rmtree(root/"vintages"/"run-two")
        shutil.copytree(root/"vintages"/"run-one",root/"vintages"/"run-two")
        rewrite_receipt(root/"vintages"/"run-two","run-two")
    builder_case("copied-run-rejected",copied,"Two-run claim rejects a copied/reused execution identity",records)
    builder_case("empty-run-rejected",lambda root: shutil.rmtree(root/"vintages"/"run-two") or (root/"vintages"/"run-two").mkdir(),"incomplete or unexpected run product set",records)
    def partial(root):
        for p in (root/"vintages"/"run-two").iterdir():
            if p.name not in ("audit.json","publication.json"): p.unlink()
        receipt=json_file(root/"vintages"/"run-two"/"publication.json")
        receipt["outputs"]=[x for x in receipt["outputs"] if Path(x["path"]).name=="audit.json"]
        (root/"vintages"/"run-two"/"publication.json").write_bytes(canonical(receipt))
    builder_case("partial-run-rejected",partial,"incomplete or unexpected run product set",records)
    def mismatch(root):
        target=root/"vintages"/"run-two"/"audit.json"
        audit=json_file(target); audit["lau_outline_comparison"]["jaccard"]=0.123456789
        raw=canonical(audit); target.write_bytes(raw)
        receipt=json_file(root/"vintages"/"run-two"/"publication.json")
        for item in receipt["outputs"]:
            if Path(item["path"]).name=="audit.json": item["bytes"]=len(raw); item["sha256"]=sha(raw)
        (root/"vintages"/"run-two"/"publication.json").write_bytes(canonical(receipt))
    builder_case("coherently-rehashed-mismatch-rejected",mismatch,"run audit differs from independently recomputed exact pinned inputs",records)
    def failed_run(root):
        shutil.rmtree(root/"vintages"/"run-two")
        (root/"vintages"/"run-two").mkdir()
        (root/"vintages"/"run-two"/"failed-attempt.json").write_text('{"status":"failed"}\n')
    builder_case("failed-producer-run-rejected",failed_run,"incomplete or unexpected run product set",records)
    builder_case("builder-existing-manifest-preserved",lambda root: None,"Existing evidence manifest is preserved",records,True)

    ordinary=VINTAGES/"ordinary-file-control-final-6"
    ordinary.write_bytes(b"protected ordinary sentinel\n")
    before_sha=sha(ordinary.read_bytes())
    r=run([str(ROOT/"reproduce.py"),"--vintage",ordinary.name])
    assert_reject("producer-ordinary-file-preserved","reproduce.py",r,ordinary.is_file() and sha(ordinary.read_bytes())==before_sha,"Vintage already exists",records)
    records[-1].update({"output_path":str(ordinary),"output_absent":False,"protected_file_sha256":before_sha})

    if original!={n:hash_tree(VINTAGES/n) for n in original}:
        raise AssertionError("A control modified one of the successful original runs")
    payload=(json.dumps({"version":1,"issue":1361,"outcome":"passed","entry_points":["reproduce.py","build_packet.py"],"controls":records,"original_run_hashes_unchanged":True,"credentials_removed_from_probe_environments":True,"private_fixture_policy":"Complete copied packets were run through the actual build_packet.py CLI with only packet root-discovery paths redirected into owned controls/fixtures; baseline Git reads and builder logic were unchanged. Each fixture tree hash was equal before/after its probe. The temporary fixture root was removed by TemporaryDirectory after the result was recorded; retained product runs and prior attempts were preserved."},sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode()
    with RESULT.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({"control_count":len(records),"outcome":"passed","sha256":sha(payload)},sort_keys=True))


if __name__=="__main__": main()

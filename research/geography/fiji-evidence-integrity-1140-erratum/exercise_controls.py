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

from packet import ROOT, OWNED, canonical, json_file, sha, shared_new_vintage

VINTAGES=ROOT/"vintages"
CONTROLS=ROOT/"controls"
RUN_ID="final-13"
RUN_NAMESPACE=CONTROLS/f"control-exercise-{RUN_ID}"
FIXTURES=RUN_NAMESPACE/"fixtures"
RESULT=RUN_NAMESPACE/"builder-controls.json"
ORDINARY_SENTINEL=VINTAGES/f"ordinary-file-control-{RUN_ID}"
BROKEN_LINK=VINTAGES/f"broken-link-control-{RUN_ID}"
BROKEN_TARGET=VINTAGES/f"missing-target-control-{RUN_ID}"
FAILED_AFTER=VINTAGES/f"failed-after-compute-{RUN_ID}"
ESCAPED_CONTROL=(VINTAGES/f"../../../../escaped-control-{RUN_ID}").resolve()


def reserve_control_namespace():
    """Reject every known destination before mutation, then exclusively reserve this run."""
    parents=(CONTROLS,VINTAGES)
    for parent in parents:
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise FileExistsError(f"Unsafe control parent: {parent}")
    destinations=(RUN_NAMESPACE,RESULT,ORDINARY_SENTINEL,BROKEN_LINK,BROKEN_TARGET,
                  FAILED_AFTER,ESCAPED_CONTROL)
    occupied=[str(path) for path in destinations if os.path.lexists(path)]
    if occupied:
        raise FileExistsError("Control namespace has existing result/sentinel/symlink destinations: "+", ".join(occupied))
    CONTROLS.mkdir(exist_ok=True)
    VINTAGES.mkdir(exist_ok=True)
    RUN_NAMESPACE.mkdir()  # atomic exclusive reservation after the complete preflight
    receipt={"version":1,"run_id":RUN_ID,"namespace":str(RUN_NAMESPACE.relative_to(ROOT)),
      "reserved_before_fixture_writes":True,"preflight_destinations":[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else os.path.relpath(p,ROOT) for p in destinations],
      "exclusive_reservation":"mkdir without exist_ok; an existing namespace is rejected"}
    (RUN_NAMESPACE/"reservation.json").write_bytes(canonical(receipt))
    FIXTURES.mkdir()
    return receipt


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
    required=["copied-run-rejected","empty-run-rejected","partial-run-rejected","coherently-rehashed-mismatch-rejected","failed-producer-run-rejected","producer-existing-vintage-preserved","producer-broken-symlink-rejected","producer-path-traversal-rejected","producer-post-calculation-failure-preserved","producer-ordinary-file-preserved","shared-writer-path-escape-rejected","shared-writer-aggregate-budget-rejected","builder-existing-manifest-preserved","control-harness-rerun-preserved"]
    return {"version":1,"issue":1361,"outcome":"passed","controls":[{"name":n,"entry_point":"exercise_controls.py fixture setup","outcome":"rejected","observation":"The test harness reserves this case; final result is written only after all actual cases pass."} for n in required]}


def fixture_root(temp):
    root=temp/"packet"
    root.mkdir()
    for name in ("issue-1361-contract.json","claim-receipt.json","source-provenance-correction.json","packet.py","reproduce.py","build_packet.py"):
        shutil.copy2(ROOT/name,root/name)
    (root/"controls").mkdir()
    (root/"controls"/"builder-controls-final-10.json").write_bytes(canonical(provisional_controls()))
    (root/"vintages").mkdir()
    for vintage,source in (("run-one","run-nine"),("run-two","run-ten")):
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


def shared_writer_cases(records):
    writer_type, writer_pin = shared_new_vintage(type("Repo", (), {"repo": str(ROOT.parents[2])})())
    for name in ("shared-writer-path-escape-rejected", "shared-writer-aggregate-budget-rejected"):
        with tempfile.TemporaryDirectory(prefix="shared-writer-",dir=FIXTURES) as tmp:
            repo=Path(tmp)/"repo"
            repo.mkdir()
            class Baseline:
                def __init__(self):
                    self.repo=str(repo)
                    self.pins={}
                    self.consumed={"pinned-input":1}
                    self.max_phase_bytes=32
                def pinned_bytes(self, path):
                    raise AssertionError("No pin reads are required for this isolated writer fixture")
            baseline=Baseline()
            before=hash_tree(repo)
            vintage="path-escape-control" if name.endswith("path-escape-rejected") else "aggregate-budget-control"
            escaped=repo/"escaped.json"
            intended=repo/OWNED/"vintages"/vintage
            publish_reached=False
            if name.endswith("path-escape-rejected"):
                unsafe="../../../../../escaped.json"
                try:
                    writer=writer_type(baseline,OWNED,vintage,[unsafe])
                    publish_reached=True
                    writer.publish({unsafe:{"probe":"must not escape"}})
                except ValueError as error:
                    expected="complete unique plain output filename inventory"
                    observed=str(error)
                else:
                    raise AssertionError("Shared writer accepted a traversal filename")
            else:
                writer=writer_type(baseline,OWNED,vintage,["payload.json"])
                try:
                    publish_reached=True
                    writer.publish({"payload.json":{"probe":"x"*256}})
                except ValueError as error:
                    expected="Complete phase including output exceeds byte budget"
                    observed=str(error)
                else:
                    raise AssertionError("Shared writer published beyond aggregate phase budget")
            after=hash_tree(repo)
            if before!=after or escaped.exists() or intended.exists():
                raise AssertionError(f"{name}: fixture changed or escaped output appeared")
            records.append({"name":name,"entry_point":"packet.shared_new_vintage -> pinned NewVintage constructor/publish","outcome":"rejected","expected_failure":expected,"observed_error":observed,"observation":("Constructor rejected the traversal filename before publication was entered; the escaped destination and intended run stayed absent." if not publish_reached else "The actual pinned publish method rejected the complete phase budget before reserving a run directory; original fixture bytes were unchanged."),"shared_writer":writer_pin,"fixture_tree_sha256_before":sha(canonical(before)),"fixture_tree_sha256_after":sha(canonical(after)),"fixture_tree_unchanged":True,"escaped_output_absent":not escaped.exists(),"intended_run_absent":not intended.exists(),"publish_reached":publish_reached,"fixture_scope":str(Path(tmp).relative_to(ROOT))})


def main():
    reservation=reserve_control_namespace()
    records=[]
    original={n:hash_tree(VINTAGES/n) for n in ("run-nine","run-ten")}
    if not original["run-nine"] or not original["run-ten"]:
        raise ValueError("Run the actual producer twice after the final code change before these controls")

    r=run([str(ROOT/"reproduce.py"),"--vintage","run-nine"])
    assert_reject("producer-existing-vintage-preserved","reproduce.py --vintage run-nine",r,hash_tree(VINTAGES/"run-nine")==original["run-nine"],"Evidence already exists; choose a new vintage",records)
    records[-1].update({"output_path":str(VINTAGES/"run-nine"),"output_absent":False,"protected_tree_sha256":sha(canonical(original["run-nine"]))})
    broken=BROKEN_LINK
    broken.symlink_to(BROKEN_TARGET)
    r=run([str(ROOT/"reproduce.py"),"--vintage",broken.name])
    assert_reject("producer-broken-symlink-rejected","reproduce.py",r,broken.is_symlink() and not BROKEN_TARGET.exists(),"Symlink in output path",records)
    records[-1].update({"output_path":str(broken),"output_absent":False,"destination_was_broken_symlink":True})
    broken.unlink()
    records[-1].update({"output_absent_after_test_cleanup":not broken.exists() and not broken.is_symlink(),"test_fixture_cleanup":"The test-created broken symlink was removed after recording rejection; no target existed."})
    outside=ESCAPED_CONTROL
    r=run([str(ROOT/"reproduce.py"),"--vintage",f"../../../../escaped-control-{RUN_ID}"])
    assert_reject("producer-path-traversal-rejected","reproduce.py",r,not outside.exists(),"Unsafe vintage name",records)
    records[-1].update({"output_path":str(outside),"output_absent":not outside.exists()})
    before={n:hash_tree(VINTAGES/n) for n in ("run-nine","run-ten")}
    r=run([str(ROOT/"reproduce.py"),"--vintage",FAILED_AFTER.name,"--audit-fail-after-compute"])
    failed=FAILED_AFTER
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

    ordinary=ORDINARY_SENTINEL
    ordinary.write_bytes(b"protected ordinary sentinel\n")
    before_sha=sha(ordinary.read_bytes())
    r=run([str(ROOT/"reproduce.py"),"--vintage",ordinary.name])
    assert_reject("producer-ordinary-file-preserved","reproduce.py",r,ordinary.is_file() and sha(ordinary.read_bytes())==before_sha,"Fresh run directory already exists",records)
    records[-1].update({"output_path":str(ordinary),"output_absent":False,"protected_file_sha256":before_sha})

    shared_writer_cases(records)

    if original!={n:hash_tree(VINTAGES/n) for n in original}:
        raise AssertionError("A control modified one of the successful original runs")
    control_tree_before=hash_tree(RUN_NAMESPACE)
    sentinel_before=sha(ordinary.read_bytes())
    rerun=run([str(ROOT/"exercise_controls.py")])
    control_tree_after=hash_tree(RUN_NAMESPACE)
    sentinel_after=sha(ordinary.read_bytes())
    expected="Control namespace has existing result/sentinel/symlink destinations"
    preserved=(rerun["returncode"]!=0 and expected in rerun["stderr_excerpt"]
      and control_tree_before==control_tree_after and sentinel_before==sentinel_after and not RESULT.exists())
    if not preserved:
        raise AssertionError(f"control-harness-rerun-preserved: rerun changed reserved outputs or missed rejection: {rerun}")
    records.append({"name":"control-harness-rerun-preserved","entry_point":"exercise_controls.py","outcome":"rejected","returncode":rerun["returncode"],"expected_failure":expected,"observed_error":rerun["stderr_excerpt"],"protected_bytes_unchanged":True,"control_namespace_sha256_before":sha(canonical(control_tree_before)),"control_namespace_sha256_after":sha(canonical(control_tree_after)),"ordinary_sentinel_sha256":sentinel_after,"result_absent":not RESULT.exists(),"observation":"A second real entry-point invocation rejected the already reserved namespace and existing sentinel before writing; the complete existing namespace and sentinel hashes stayed byte-identical."})
    payload=(json.dumps({"version":1,"issue":1361,"outcome":"passed","entry_points":["reproduce.py","build_packet.py"],"controls":records,"original_run_hashes_unchanged":True,"credentials_removed_from_probe_environments":True,"namespace_reservation":reservation,"private_fixture_policy":"Complete copied packets were run through the actual build_packet.py CLI with only packet root-discovery paths redirected into the exclusively reserved control namespace; baseline Git reads and builder logic were unchanged. Each fixture tree hash was equal before/after its probe. The temporary fixture root was removed by TemporaryDirectory after the result was recorded; retained product runs and prior attempts were preserved."},sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode()
    with RESULT.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({"control_count":len(records),"outcome":"passed","sha256":sha(payload)},sort_keys=True))


if __name__=="__main__": main()

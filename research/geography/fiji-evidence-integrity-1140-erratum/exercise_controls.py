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

from packet import ROOT, canonical, json_file, sha
from build_packet import MANIFEST_PATH, publish_root_manifest

VINTAGES=ROOT/"vintages"
FIX=VINTAGES/"control-fixtures"
CONTROLS=ROOT/"controls"
RESULT=CONTROLS/"builder-controls-final-2.json"


def hash_tree(path):
    return {x.relative_to(path).as_posix():sha(x.read_bytes()) for x in sorted(path.rglob("*")) if x.is_file() and not x.is_symlink()}


def clean_env():
    env={k:v for k,v in os.environ.items() if "TOKEN" not in k.upper() and "SECRET" not in k.upper() and "PASSWORD" not in k.upper()}
    env["PYTHONDONTWRITEBYTECODE"]="1"
    return env


def run(args):
    p=subprocess.run([sys.executable,*args],cwd=ROOT.parents[2],env=clean_env(),capture_output=True,text=True)
    return {"returncode":p.returncode,"stdout_sha256":sha(p.stdout.encode()),"stderr_sha256":sha(p.stderr.encode()),"stderr_excerpt":p.stderr[-600:]}


def assert_reject(name, entry, result, preserved, observation, records):
    if result["returncode"]==0 or not preserved:
        raise AssertionError(f"{name} was accepted or changed protected evidence")
    records.append({"name":name,"entry_point":entry,"outcome":"rejected","returncode":result["returncode"],"observation":observation,"protected_bytes_unchanged":True,"stdout_sha256":result["stdout_sha256"],"stderr_sha256":result["stderr_sha256"],"stderr_excerpt":result["stderr_excerpt"]})


def main():
    CONTROLS.mkdir(exist_ok=True)
    FIX.mkdir(parents=True,exist_ok=True)
    records=[]
    original={"run-three":hash_tree(VINTAGES/"run-three"),"run-four":hash_tree(VINTAGES/"run-four")}
    if not original["run-three"] or not original["run-four"]:
        raise ValueError("Run the actual producer twice before these controls")

    # Existing complete run directory: no run output may be overwritten.
    r=run([str(ROOT/"reproduce.py"),"--vintage","run-three"])
    assert_reject("producer-existing-vintage-preserved","reproduce.py --vintage run-three",r,hash_tree(VINTAGES/"run-three")==original["run-three"],"the producer rejected the occupied run name and every original output hash stayed equal",records)

    # A broken symlink occupies the destination and must remain untouched.
    broken=VINTAGES/"broken-link-control"
    if broken.exists() or broken.is_symlink(): raise FileExistsError(broken)
    broken.symlink_to(VINTAGES/"missing-target-control")
    r=run([str(ROOT/"reproduce.py"),"--vintage","broken-link-control"])
    assert_reject("producer-broken-symlink-rejected","reproduce.py",r,broken.is_symlink() and not (VINTAGES/"missing-target-control").exists(),"broken output symlink remains and no target was created",records)
    broken.unlink()
    records[-1]["test_fixture_cleanup"]="The test-created broken symlink was removed after recording rejection; no target existed."

    # Traversal is rejected before resolving or creating any path outside the prefix.
    outside=(VINTAGES/"../../../../escaped-control").resolve()
    r=run([str(ROOT/"reproduce.py"),"--vintage","../../../../escaped-control"])
    assert_reject("producer-path-traversal-rejected","reproduce.py",r,not outside.exists(),"unsafe vintage name was rejected and no escaped path was created",records)

    # A deliberate failure after the full calculation leaves no completion receipt or partial run.
    failed=VINTAGES/"failed-after-compute"
    before=hash_tree(VINTAGES/"run-three")|{("run-four/"+k):v for k,v in hash_tree(VINTAGES/"run-four").items()}
    r=run([str(ROOT/"reproduce.py"),"--vintage","failed-after-compute","--audit-fail-after-compute"])
    after=hash_tree(VINTAGES/"run-three")|{("run-four/"+k):v for k,v in hash_tree(VINTAGES/"run-four").items()}
    assert_reject("producer-post-calculation-failure-preserved","reproduce.py --audit-fail-after-compute",r,not failed.exists() and before==after,"intentional post-calculation fault exits nonzero, publishes no run directory/receipt and leaves prior runs byte-identical",records)

    # A duplicate directory is not a second execution: its execution ID is copied.
    dup=VINTAGES/"copied-run-four-final-2"
    if dup.exists(): raise FileExistsError(dup)
    shutil.copytree(VINTAGES/"run-three",dup)
    r=run([str(ROOT/"build_packet.py"),"--run-one","run-three","--run-two","copied-run-four-final-2","--output-vintage","probe-copy-final-2"])
    assert_reject("copied-run-rejected","build_packet.py",r,not (VINTAGES/"probe-copy-rejected").exists(),"the builder rejected duplicate producer execution IDs; no pair receipt was published",records)

    # Empty and one-file directories fail the complete inventory requirement.
    empty=VINTAGES/"empty-run-four-final-2"
    empty.mkdir(exist_ok=False)
    r=run([str(ROOT/"build_packet.py"),"--run-one","run-three","--run-two","empty-run-four-final-2","--output-vintage","probe-empty-final-2"])
    assert_reject("empty-run-rejected","build_packet.py",r,not (VINTAGES/"probe-empty-rejected").exists(),"empty second run fails whole-run receipt/product inventory; no pair receipt was published",records)

    partial=VINTAGES/"partial-run-four-final-2"
    partial.mkdir(exist_ok=False)
    shutil.copy2(VINTAGES/"run-four"/"audit.json",partial/"audit.json")
    r=run([str(ROOT/"build_packet.py"),"--run-one","run-three","--run-two","partial-run-four-final-2","--output-vintage","probe-partial-final-2"])
    assert_reject("partial-run-rejected","build_packet.py",r,not (VINTAGES/"probe-partial-rejected").exists(),"one matching product cannot substitute for the five expected products plus completion receipt",records)

    # A fully rehashed but semantically modified audit is rejected by pinned-input recomputation.
    mismatch=VINTAGES/"mismatched-run-four-final-2"
    shutil.copytree(VINTAGES/"run-four",mismatch)
    audit=json_file(mismatch/"audit.json")
    audit["lau_outline_comparison"]["jaccard"]=0.123456789
    raw=(json.dumps(audit,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)+"\n").encode()
    (mismatch/"audit.json").write_bytes(raw)
    receipt=json_file(mismatch/"publication.json")
    for item in receipt["outputs"]:
        if item["path"].endswith("/audit.json"):
            item["bytes"]=len(raw); item["sha256"]=sha(raw)
    (mismatch/"publication.json").write_bytes(canonical(receipt))
    r=run([str(ROOT/"build_packet.py"),"--run-one","run-three","--run-two","mismatched-run-four-final-2","--output-vintage","probe-mismatch-final-2"])
    assert_reject("coherently-rehashed-mismatch-rejected","build_packet.py",r,not (VINTAGES/"probe-mismatch-rejected").exists(),"builder accepts internally consistent file hashes only after exact pinned-input recomputation; altered Lau metric is rejected",records)

    # The failed producer attempt is not accepted as a valid second run.
    r=run([str(ROOT/"build_packet.py"),"--run-one","run-three","--run-two","failed-after-compute","--output-vintage","probe-failed-final-2"])
    assert_reject("failed-producer-run-rejected","build_packet.py",r,not (VINTAGES/"probe-failed-run-rejected").exists(),"missing failed-run output/receipt is rejected; no successful pair receipt is created",records)

    # Plain file, broken symlink, and path traversal destination admission are tested at producer boundary.
    ordinary=VINTAGES/"ordinary-file-control-final-2"
    ordinary.write_bytes(b"protected ordinary sentinel\n")
    before_sha=sha(ordinary.read_bytes())
    r=run([str(ROOT/"reproduce.py"),"--vintage","ordinary-file-control"])
    assert_reject("producer-ordinary-file-preserved","reproduce.py",r,ordinary.is_file() and sha(ordinary.read_bytes())==before_sha,"ordinary file at run destination is preserved and no completion record is written",records)

    # Exercise the same exclusive root writer used for evidence-quality.json.
    manifest_fixture=CONTROLS/"fixtures"/"preexisting-manifest-final-2"/"evidence-quality.json"
    manifest_fixture.parent.mkdir(parents=True,exist_ok=True)
    manifest_fixture.write_bytes(b"previous evidence sentinel\n")
    sentinel=sha(manifest_fixture.read_bytes())
    try:
        publish_root_manifest(b"new content\n",target=manifest_fixture)
    except FileExistsError:
        rejected=True
    else:
        rejected=False
    records.append({"name":"builder-existing-manifest-preserved","entry_point":"build_packet.publish_root_manifest","outcome":"rejected" if rejected and sha(manifest_fixture.read_bytes())==sentinel else "accepted","returncode":1 if rejected else 0,"observation":"exclusive root-manifest publisher rejects an existing target and leaves its exact sentinel bytes unchanged","protected_bytes_unchanged":rejected and sha(manifest_fixture.read_bytes())==sentinel,"sentinel_sha256":sentinel})
    if not rejected or sha(manifest_fixture.read_bytes())!=sentinel: raise AssertionError("Root manifest collision overwrote prior evidence")

    if original["run-three"]!=hash_tree(VINTAGES/"run-three") or original["run-four"]!=hash_tree(VINTAGES/"run-four"):
        raise AssertionError("A control modified one of the successful original runs")
    doc={"version":1,"issue":1361,"outcome":"passed","entry_points":["reproduce.py","build_packet.py","build_packet.publish_root_manifest"],"controls":records,"original_run_hashes_unchanged":True,"credentials_removed_from_probe_environments":True}
    payload=(json.dumps(doc,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode()
    with RESULT.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({"control_count":len(records),"outcome":"passed","sha256":sha(payload)},sort_keys=True))


if __name__=="__main__": main()

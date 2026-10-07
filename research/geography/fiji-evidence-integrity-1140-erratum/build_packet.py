#!/usr/bin/env python3
"""Validate a complete independent run pair and publish a truthful final manifest."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys

from packet import (
    ROOT, REPO, OWNED, BASELINE_COMMIT, OUTPUTS as RUN_OUTPUTS,
    canonical, code_bindings, descriptor, git_blob, json_file, load_context,
    calculate, make_controls, validate_run, sha,
)

PAIR_OUTPUTS = ["two-run-reproducibility.json", "builder-controls.json", "run-bindings.json", "run-metadata.json"]
PAIR_CONTROLS_PATH = ROOT / "controls" / "builder-controls-final-13.json"
MANIFEST_PATH = ROOT / "evidence-quality.json"


def ensure_fresh_manifest_path(target=MANIFEST_PATH):
    for path in [target, *target.parents]:
        if path == REPO.parent:
            break
        if path.is_symlink():
            raise ValueError("Manifest path has a symlink ancestor")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Existing evidence manifest is preserved; build into a fresh owned namespace")


def publish_root_manifest(payload: bytes, target=MANIFEST_PATH):
    """Exclusive, fsynced root-manifest write; never replace an earlier result."""
    if len(payload) > 32 * 1024 * 1024:
        raise ValueError("Evidence manifest exceeds file budget")
    ensure_fresh_manifest_path(target)
    temp = target.parent / ("." + target.name + ".incomplete-" + secrets.token_hex(8))
    try:
        with temp.open("xb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, target)
        dfd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if temp.exists():
            temp.unlink()


def file_record(path: Path):
    raw = path.read_bytes()
    return descriptor(str(path.relative_to(REPO)), raw)


def inventory_outputs():
    rows=[]
    for path in sorted(ROOT.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ValueError("Evidence namespace contains an untrusted symlink: "+str(path))
        if path.is_file() and path != MANIFEST_PATH:
            rows.append(file_record(path))
    if not rows:
        raise ValueError("No candidate outputs to inventory")
    return rows


def verify_controls(controls):
    if controls.get("version") != 1 or controls.get("issue") != 1361 or controls.get("outcome") != "passed":
        raise ValueError("Actual adverse-control execution record is missing or invalid")
    required={"copied-run-rejected","empty-run-rejected","partial-run-rejected","coherently-rehashed-mismatch-rejected","failed-producer-run-rejected","producer-existing-vintage-preserved","producer-broken-symlink-rejected","producer-path-traversal-rejected","producer-post-calculation-failure-preserved","producer-ordinary-file-preserved","shared-writer-path-escape-rejected","shared-writer-aggregate-budget-rejected","builder-existing-manifest-preserved","control-harness-rerun-preserved"}
    rows=controls.get("controls",[])
    names={x.get("name") for x in rows}
    if names != required or any(x.get("outcome") != "rejected" for x in rows):
        raise ValueError("Adverse controls do not cover every required real entry-point case")
    if any(not x.get("entry_point") or not x.get("observation") for x in rows):
        raise ValueError("Control record lacks actual entry point or observation")
    return rows


def build_manifest(ctx, audit, pair, controls_path, run_one, run_two, output_vintage):
    base=ctx["baseline"]
    pins=ctx["work"]["evidence_quality"]["pins"]
    baseline_files=[descriptor(path,base.pinned_bytes(path)) for path in sorted(pins)]
    baseline={
        "commit":BASELINE_COMMIT,
        "files":baseline_files,
        "pins":pins,
        "pin_commits":ctx["pin_commits"],
        "pin_files":{k:k for k in pins},
        "subject_files":{x:"data/geography/part-8.json" for x in ctx["ids"]},
    }
    outputs=inventory_outputs()
    subject_hash=hashlib.sha256(json.dumps(ctx["ids"],separators=(",",":")).encode()).hexdigest()
    audit_path=OWNED+f"vintages/{run_one}/audit.json"
    pair_path=OWNED+f"vintages/{output_vintage}/two-run-reproducibility.json"
    source_files=[
        {"path":"data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-FJI-ADM2.geojson","bytes":1357011,"sha256":"a9cd94789cb5eb66cfbcbaf32a21bcbceba16b9a76adacba9ac675b950ca1ccd","hash_kind":"file-bytes"},
        {"path":"data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-FJI-ADM2-metaData.json","bytes":970,"sha256":"2a518d79ff779e3dddd3cfabd0357885c078e7226fdeceb0ddc3e10d47d31925","hash_kind":"file-bytes"},
        {"path":"data/regional-review/fiji-admin-source-reconciliation-20261005/sources/CITATION-AND-USE-geoBoundaries.txt","bytes":4316,"sha256":"f6ea7572bea6036c4cdcacf8c0ca7bf09098d4e600d19546d7432533e9a290d5","hash_kind":"file-bytes"},
        {"path":"data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-api-current-FJI-ADM2.json","bytes":1867,"sha256":"35e5eff798967d740490f28420d48a11ce7f764acc8470c4354b11a4e6272564","hash_kind":"file-bytes"},
    ]
    correction=json_file(ROOT/"source-provenance-correction.json")
    sources=[
        {"id":"geoBoundaries-FJI-ADM2-pinned","url":"https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/FJI/ADM2/geoBoundaries-FJI-ADM2.geojson","role":"Full retained 15-feature layer for exact native identity/name matching and diagnostic Lau comparison; not an authoritative current boundary determination.","vintage":"Source catalog calls the underlying dataset 2007 Fiji PHC administrative boundaries; pinned geoBoundaries release says boundaryYear=2020 and is built 2023-12-12. Meaning unresolved.","retrieved_at":"2026-10-06 retained; source GitHub API identities rechecked 2026-10-07","license":{"status":"redistributable","terms":"geoBoundaries release and citation identify CC BY 4.0; attribution required."},"retention":"retained","verification":"verified","temporal_status":"reference","limit":"Issue/source roster agreement and shape identity do not prove current legal boundaries or complete islands.","files":[source_files[0]]},
        {"id":"geoBoundaries-release-metadata","url":"https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/FJI/ADM2/geoBoundaries-FJI-ADM2-metaData.json","role":"Pinned source year, level, count, license, update/build timestamps and upstream source link.","vintage":"Source update 2023-01-19; build 2023-12-12; boundaryYear key is 2020.","retrieved_at":"2026-10-06 retained; exact GitHub blob/LFS pointer rechecked 2026-10-07","license":{"status":"redistributable","terms":"Associated release identifies CC BY 4.0."},"retention":"retained","verification":"verified","temporal_status":"reference","limit":"boundaryYearRepresented and sha256 keys are absent in this pinned release record; do not report either as JSON null.","files":[source_files[1]]},
        {"id":"geoBoundaries-citation-use","url":"https://github.com/wmgeolab/geoBoundaries/blob/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/FJI/ADM2/CITATION-AND-USE-geoBoundaries.txt","role":"Pinned attribution, license and field-definition instructions.","vintage":"Repository state at exact upstream commit 9469f09592ced973a3448cf66b6100b741b64c0d.","retrieved_at":"2026-10-06 retained; exact citation path/blob rechecked 2026-10-07","license":{"status":"redistributable","terms":"CC BY 4.0 attribution instructions for geoBoundaries product."},"retention":"retained","verification":"verified","temporal_status":"reference","limit":"A product license statement does not certify original authority, current territorial status or source completeness.","files":[source_files[2]]},
        {"id":"geoBoundaries-current-api-record","url":"https://www.geoboundaries.org/api/current/gbOpen/FJI/ADM2/","role":"Retained comparison record for current catalog metadata; records boundaryYearRepresented 2020 and omits sha256.","vintage":"Retrieved 2026-10-06; update/build fields report 2023 dates.","retrieved_at":"2026-10-06 retained; bytes rechecked 2026-10-07","license":{"status":"redistributable","terms":"Metadata record describes linked source as CC BY 4.0."},"retention":"retained","verification":"verified","temporal_status":"reference","limit":"A current catalog record is not a new boundary layer or authority adjudication.","files":[source_files[3]]},
        *[{"id":x["id"],"url":x["url"],"role":"Primary context source cited for territorial meaning, administrative scale or source vintage.","vintage":"See source-provenance-correction.json; original publication date is not asserted where absent.","retrieved_at":x["retrieved_at"],"license":{"status":"unknown","terms":x.get("reuse","Reuse terms not established; no source page body copied.")},"retention":"restoration-only","verification":"unverified","temporal_status":"reference","restoration":x["restoration"],"limit":"Institutional statement supports only the stated reporting context; it does not supply complete current boundary geometries or prove small-island coverage."} for x in correction["official_context"]],
    ]
    method_id="fiji-15-subject-source-identity-and-lau-diagnostic-v1"
    values={
        "exact_subjects":(15,"locations"),
        "source_features":(15,"features"),
        "exact_identity_matches":(15,"matches"),
        "positive_controls":(4,"controls"),
        "negative_controls":(5,"adverse cases"),
        "lau_jaccard":(audit["lau_outline_comparison"]["jaccard"],"fraction"),
        "lau_symmetric_difference":(audit["lau_outline_comparison"]["symmetric_difference_km2"],"km2"),
        "lau_intersection":(audit["lau_outline_comparison"]["intersection_m2"],"m2"),
        "lau_union":(audit["lau_outline_comparison"]["union_m2"],"m2"),
        "independent_successful_runs":(2,"executions"),
        "stable_run_products_byte_identical":(1,"boolean"),
    }
    input_digest=sha((ROOT/"source-provenance-correction.json").read_bytes())
    metrics=[{"id":k,"value":v[0],"unit":v[1],"vintage":"retained source + pinned Atlas baseline","evaluation_commit":BASELINE_COMMIT,"input_sha256":input_digest} for k,v in values.items()]
    manifest={
        "version":1,"issue":1361,"lane":"geography","worker_id":"01a10947-7d6e-7ba2-98a1-a9f91dedabfc",
        "subject_ids":ctx["ids"],"subject_ids_sha256":subject_hash,"baseline":baseline,
        "sources":sources,"outputs":outputs,
        "methods":[{"id":method_id,"kind":"geography","description":"Correct the exact source-vintage/blob/citation record and independently bind the 15 Fiji source identities to the pinned Atlas subjects; retain a Lau outline diagnostic without legal boundary adjudication.","software":"Python 3.12+; Shapely; PyProj; NumPy; exact pinned WorldAtlas evidence geometry and immutable helpers","units":"counts, fraction, square metres and square kilometres","helper_version":"worldatlas-evidence-geometry-v1","axis_order":"longitude-latitude","crs":"EPSG:4326","area_method":audit["lau_outline_comparison"]["method"]["area_method"],"distance_method":audit["lau_outline_comparison"]["method"]["distance_method"]}],
        "metrics":[{**x,"vintage":"baseline"} for x in metrics],
        "summaries":[{"metric_id":x["id"],"value":x["value"],"unit":x["unit"]} for x in metrics],
        "conclusions":[
            {"text":"All 15 issue subject IDs map one-to-one by native geoBoundaries shapeID suffix and exact name to the complete retained 15-feature source layer and to existing Atlas records.","status":"supported","source_ids":["geoBoundaries-FJI-ADM2-pinned"]},
            {"text":"The source provenance record now states the actual pinned metadata keys, 2020 value, absent boundaryYearRepresented/sha256 keys, correct upstream Git blobs, LFS OIDs and citation path.","status":"supported","source_ids":["geoBoundaries-release-metadata","geoBoundaries-citation-use","geoBoundaries-current-api-record"]},
            {"text":"The linked boundary vintage, current legal edge authority, exact Rotuma hierarchy meaning, small-island completeness and neighboring coverage remain unresolved; no geography approval is claimed.","status":"unresolved","source_ids":["pacific-data-hub-2007-fiji-phc-boundaries","fiji-government-2025-cedaw-statement","itaukei-affairs-board-province-list","fiji-bureau-statistics-census-page","fiji-rotuma-act-1927"]},
        ],
        "stages":{"research":"partial","implementation":"not-proposed","geographic_approval":"unapproved"},
        "commands":[f"python reproduce.py --vintage {run_one}",f"python reproduce.py --vintage {run_two}",f"python exercise_controls.py",f"python build_packet.py --run-one {run_one} --run-two {run_two} --output-vintage {output_vintage}",f"node scripts/evidence-quality.mjs {OWNED}evidence-quality.json"],
        "metric_bindings":[
            {"metric_id":"exact_subjects","path":audit_path,"json_pointer":"/scope/issue_subject_count"},
            {"metric_id":"source_features","path":audit_path,"json_pointer":"/scope/source_feature_count"},
            {"metric_id":"exact_identity_matches","path":audit_path,"json_pointer":"/scope/crosswalk_count"},
            {"metric_id":"positive_controls","path":OWNED+f"vintages/{run_one}/positive-control.json","json_pointer":"/passed_controls"},
            {"metric_id":"negative_controls","path":OWNED+f"vintages/{run_one}/negative-controls.json","json_pointer":"/passed_controls"},
            {"metric_id":"lau_jaccard","path":audit_path,"json_pointer":"/lau_outline_comparison/jaccard"},
            {"metric_id":"lau_symmetric_difference","path":audit_path,"json_pointer":"/lau_outline_comparison/symmetric_difference_km2"},
            {"metric_id":"lau_intersection","path":audit_path,"json_pointer":"/lau_outline_comparison/intersection_m2"},
            {"metric_id":"lau_union","path":audit_path,"json_pointer":"/lau_outline_comparison/union_m2"},
            {"metric_id":"independent_successful_runs","path":pair_path,"json_pointer":"/independent_execution_count"},
            {"metric_id":"stable_run_products_byte_identical","path":pair_path,"json_pointer":"/stable_run_products_byte_identical"},
        ],
        "validation":[
            {"method_id":method_id,"kind":"positive-control","outcome":"passed","evidence_path":OWNED+f"vintages/{run_one}/positive-control.json"},
            {"method_id":method_id,"kind":"negative-control","outcome":"passed","evidence_path":OWNED+f"vintages/{run_one}/negative-controls.json"},
            {"method_id":method_id,"kind":"reproducibility","outcome":"passed","evidence_path":pair_path},
        ],
        "change_receipts":[{"path":x["path"],"status":"added"} for x in outputs]+[{"path":OWNED+"evidence-quality.json","status":"added"}],
    }
    return manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--run-one",default="run-one")
    parser.add_argument("--run-two",default="run-two")
    parser.add_argument("--output-vintage",default="final-pair")
    args=parser.parse_args()
    ensure_fresh_manifest_path()
    ctx=load_context()
    writer=ctx["NewVintage"](ctx["baseline"],OWNED,args.output_vintage,PAIR_OUTPUTS)
    audit,rows,atlas,source,hierarchy=calculate(ctx)
    positive,negative=make_controls(ctx,atlas,source,hierarchy,rows)
    one=validate_run(args.run_one,ctx,audit,positive,negative)
    two=validate_run(args.run_two,ctx,audit,positive,negative)
    if one["metadata"]["execution_id"]==two["metadata"]["execution_id"]:
        raise ValueError("Two-run claim rejects a copied/reused execution identity")
    if one["metadata"]["process_id"]==two["metadata"]["process_id"]:
        raise ValueError("Two-run claim requires separately executed producer processes")
    stable=["audit.json","positive-control.json","negative-controls.json","execution-bindings.json"]
    if any(one["output_hashes"][x]!=two["output_hashes"][x] for x in stable):
        raise ValueError("Two independent complete runs differ in a calculated product")
    controls=json_file(PAIR_CONTROLS_PATH)
    control_rows=verify_controls(controls)
    cpath=str(PAIR_CONTROLS_PATH.relative_to(REPO))
    controls_hash=sha(PAIR_CONTROLS_PATH.read_bytes())
    pair={
        "version":1,"issue":1361,"method_id":"fiji-15-subject-source-identity-and-lau-diagnostic-v1",
        "kind":"reproducibility","outcome":"passed","independent_execution_count":2,
        "runs":[
            {"vintage":"run-one","execution_id":one["metadata"]["execution_id"],"process_id":one["metadata"]["process_id"],"started_at":one["metadata"]["started_at"],"publication_sha256":sha((one["root"]/"publication.json").read_bytes()),"whole_product_sha256":one["output_hashes"]},
            {"vintage":"run-two","execution_id":two["metadata"]["execution_id"],"process_id":two["metadata"]["process_id"],"started_at":two["metadata"]["started_at"],"publication_sha256":sha((two["root"]/"publication.json").read_bytes()),"whole_product_sha256":two["output_hashes"]},
        ],
        "compared_products":stable,
        "run_one_sha256":one["output_hashes"]["audit.json"],
        "run_two_sha256":two["output_hashes"]["audit.json"],
        "byte_identical":True,
        "stable_run_products_byte_identical":1,
        "metadata_is_expected_to_differ":["execution_id","process_id","started_at","command"],
        "adverse_control_record":{"path":cpath,"sha256":controls_hash,"rejected_cases":len(control_rows)},
        "interpretation":"Only the complete deterministic calculation/control/binding products are compared byte-for-byte. Each run has a distinct execution identity and its own complete publication receipt. No source/legal or boundary approval follows from repeatability.",
    }
    pair["runs"][0]["vintage"]=args.run_one
    pair["runs"][1]["vintage"]=args.run_two
    run_bindings={"version":1,"issue":1361,"baseline_commit":BASELINE_COMMIT,"executed_code":code_bindings(),"run_receipts":[pair["runs"][0],pair["runs"][1]],"builder_script_sha256":sha(Path(__file__).read_bytes()),"controls_sha256":controls_hash}
    import datetime
    run_meta={"version":1,"issue":1361,"vintage":args.output_vintage,"execution_id":secrets.token_hex(16),"process_id":os.getpid(),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"command":sys.argv,"status":"complete"}
    pair_records=writer.publish({"two-run-reproducibility.json":pair,"builder-controls.json":controls,"run-bindings.json":run_bindings,"run-metadata.json":run_meta})
    # Manifest publication follows two fully validated independent runs and the complete pair receipt.
    manifest=build_manifest(ctx,audit,pair,cpath,args.run_one,args.run_two,args.output_vintage)
    payload=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    publish_root_manifest(payload)
    print(json.dumps({"status":"complete","manifest":str(MANIFEST_PATH.relative_to(REPO)),"manifest_sha256":sha(payload),"pair_outputs":pair_records,"byte_identical":pair["byte_identical"]},sort_keys=True))


if __name__=="__main__":
    main()

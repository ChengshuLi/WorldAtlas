#!/usr/bin/env python3
"""Build the bounded issue #1510 evidence manifest from immutable pins."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
OWNED=ROOT.relative_to(REPO).as_posix()+"/"
OUTPUT=ROOT/"evidence-quality.json"
BASE_ISSUE=1510
PREDECESSOR_COMMIT="515c6e66cea72f0f2357826950692b719d0c89ce"
DATA_COMMIT="088ab05aeb16ddfa8f0c43e596533f3f11d5fcec"
RUN_EVALUATION_BASE="689fa0618ce61827adc8862c3e065bcfcf97417b"
BASE_MANIFEST_PATH="research/geography/norway-adm2-source-fit-1492/evidence-quality.json"
METHOD="norway-physical-applicability-measurement"

def git(*args: str) -> bytes:
    return subprocess.check_output(["git","-C",str(REPO),*args])
def sha(raw: bytes) -> str: return hashlib.sha256(raw).hexdigest()
def subjects_hash(ids: list[str]) -> str: return sha(json.dumps(sorted(ids),separators=(",",":")).encode())
def current_descriptor(path: str) -> dict:
    raw=(REPO/path).read_bytes()
    return {"path":path,"bytes":len(raw),"sha256":sha(raw),"hash_kind":"file-bytes"}
def baseline_descriptor(path: str, commit: str, known: dict[str,dict]) -> dict:
    raw=git("show",f"{commit}:{path}")
    desc=dict(known.get(path,{}))
    desc.update({"path":path,"bytes":len(raw),"sha256":sha(raw),"hash_kind":"file-bytes","commit":commit})
    return desc
def changed_files(base: str) -> list[dict]:
    text=git("diff","--name-status","--no-renames",f"{base}...HEAD","--").decode()
    rows={}
    for line in text.splitlines():
        status,path=line.split("\t",1)
        norm={"A":"added","M":"modified","D":"removed"}.get(status)
        if norm is None: raise SystemExit(f"Unsupported PR diff status {status}")
        row={"path":path,"status":norm}
        if norm!="added": row["original_sha256"]=sha(git("show",f"{base}:{path}"))
        if norm=="removed": row["reason"]="Removed only when superseded by a retained source/output in this evidence packet."
        rows[path]=row
    for path in git("ls-files","--others","--exclude-standard",OWNED).decode().splitlines():
        rows.setdefault(path,{"path":path,"status":"added"})
    return [rows[path] for path in sorted(rows)]

def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--refresh",action="store_true")
    args=parser.parse_args()
    if OUTPUT.exists() and not args.refresh: raise SystemExit("evidence-quality.json already exists; pass --refresh after committing the manifest to refresh exact PR change receipts")
    plan=json.loads((ROOT/"bounded-measurement-plan.json").read_text())
    result_path=OWNED+"physical-applicability-v1.json"
    result=json.loads((REPO/result_path).read_text())
    result_raw=(REPO/result_path).read_bytes(); result_sha=sha(result_raw)
    subject_ids=[row["component_id"] for row in result["cases"]]
    predecessor=json.loads(git("show",f"{PREDECESSOR_COMMIT}:{BASE_MANIFEST_PATH}"))
    known={}
    for descriptor in predecessor["baseline"]["files"]+predecessor["outputs"]+sum((x.get("files",[]) for x in predecessor["sources"]),[]):
        known.setdefault(descriptor["path"],descriptor)
    try:
        base=git("rev-parse","origin/main").decode().strip()
    except subprocess.CalledProcessError:
        base=git("rev-parse","HEAD^" if git("rev-parse","HEAD").decode().strip()!=PREDECESSOR_COMMIT else "HEAD").decode().strip()

    # Authenticate only the exact measurement inputs, required issue pins, and
    # the seven original delivery feature records. Each file is pinned to the
    # merged predecessor vintage that owns those bytes.
    paths={
      "research/geography/norway-adm2-source-fit-1492/vintages/component-geometries-20261008/selected-components.json",
      "research/geography/norway-adm2-source-fit-1492/vintages/exact-overlay-acceptance-20261008/overlay-v1.json",
      "research/geography/norway-adm2-source-fit-1492/vintages/family-scope-corrected-20261008/family-scope.json",
      "research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm2-simplified.geojson",
      "research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm1-simplified.geojson",
      "research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/selected-source-rows.json",
      "data/geography/part-17.json","data/administrative-sources.json","data/hierarchy.json",
      "coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-000.json.gz",
      "coordination/engineering/global-actionability-routing-20261007/results/families-000.bin.gz",
      BASE_MANIFEST_PATH,
    }
    for identity in result["scope"]["candidate_ids"]:
        paths.add(predecessor["baseline"]["subject_files"][identity])
    baseline_files=[]
    for path in sorted(paths):
        descriptor=baseline_descriptor(path,PREDECESSOR_COMMIT,known)
        # Measurement inputs are checked against their issue plan byte pins.
        for item in plan["measurement_inputs"]["pins"].values():
            if isinstance(item,dict) and item.get("path")==path:
                raw=(REPO/path).read_bytes()
                if len(raw)!=item["bytes"] or sha(raw)!=item["sha256"] or descriptor["sha256"]!=item["sha256"]:
                    raise SystemExit(f"Input drift from plan or predecessor: {path}")
        baseline_files.append(descriptor)
    path_set={item["path"] for item in baseline_files}
    source_subjects={identity:{"path":predecessor["baseline"]["subject_files"][identity],"commit":PREDECESSOR_COMMIT}
                     for identity in subject_ids}
    if any(binding["path"] not in path_set for binding in source_subjects.values()):
        raise SystemExit("One or more subject delivery records are unpinned")

    pins={}
    pin_paths={}
    issue_pins={
      "predecessor-evidence-quality":sha(git("show",f"{PREDECESSOR_COMMIT}:{BASE_MANIFEST_PATH}")),
      "atlas-hierarchy":"568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
      "atlas-administrative-sources":"ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
      "atlas-norway-geography-part":"1ae1a9ef25c1f71b66084aadf57933132383d4271b888ab38866905da5678af3",
      "norway-source-component-ledger":"ba0fd40372e35b4d266bc3d19fd51efeec4f990c7459ed3dc1ebaa40a3d3cf1e",
      "norway-400-family-ledger":"60e770171089510b8f97ebd74a93e1c913953716a4281699e4ecca75aaefffd5",
    }
    issue_pin_paths={
      "predecessor-evidence-quality":BASE_MANIFEST_PATH,
      "atlas-hierarchy":"data/hierarchy.json",
      "atlas-administrative-sources":"data/administrative-sources.json",
      "atlas-norway-geography-part":"data/geography/part-17.json",
      "norway-source-component-ledger":"coordination/engineering/global-source-comparisons-a-001-20261006/scientific/components-000.json.gz",
      "norway-400-family-ledger":"coordination/engineering/global-actionability-routing-20261007/results/families-000.bin.gz",
    }
    for key,value in issue_pins.items():
        pins[key]=value; pin_paths[key]={"path":issue_pin_paths[key],"commit":PREDECESSOR_COMMIT}
        if not any(x["path"]==issue_pin_paths[key] and x["sha256"]==value for x in baseline_files): raise SystemExit(f"Issue pin does not match baseline: {key}")
    for key,item in plan["measurement_inputs"]["pins"].items():
        if not isinstance(item,dict) or "path" not in item: continue
        pins["measurement-"+key]=item["sha256"]
        pin_paths["measurement-"+key]={"path":item["path"],"commit":PREDECESSOR_COMMIT}

    source_dir=ROOT/"sources/sjoekart-dybdedata-wfs-20261008"
    source_index=json.loads((source_dir/"source-snapshot-index.json").read_text())
    raw_paths=sorted((p.relative_to(REPO).as_posix() for p in source_dir.glob("*.gml")))
    wfs_files=[current_descriptor(path) for path in raw_paths+[OWNED+"sources/sjoekart-dybdedata-wfs-20261008/source-snapshot-index.json"]]
    # Capture metadata documents and scripts are outputs; the geographic source
    # inventory is limited to the 14 retained raw service responses and index.
    non_output={x["path"] for x in wfs_files}
    output_files=[]
    for path in sorted(p.relative_to(REPO).as_posix() for p in ROOT.rglob("*") if p.is_file()):
        if path==OWNED+"evidence-quality.json" or path in non_output: continue
        output_files.append(current_descriptor(path))
    if len(wfs_files)+len(output_files)+len(baseline_files)>512: raise SystemExit("Evidence inventory exceeds 512-file bound")

    vals={
      "case_rows":len(result["cases"]),"candidate_context_count":result["scope"]["candidate_context_count"],
      "family_member_count":result["scope"]["complete_family_member_count"],"neighbor_id_count":result["scope"]["positive_length_neighbor_count"],
      "neighbor_relation_rows":result["controls"]["relation_rows"],"evaluated_neighbor_relations":result["controls"]["evaluated_neighbor_relations"],
      "own_target_rows":result["controls"]["own_target_rows"],
      "added_area_receipt_matches":sum(bool(x["added_area_matches_pinned_1492_receipt"]) for x in result["cases"]),
      "strict_no_loss_passes":sum(bool(x["strict_no_loss_pass"]) for x in result["cases"]),
      "strict_no_loss_nonempty_residuals":sum(not bool(x["strict_no_loss_pass"]) for x in result["cases"]),
      "full_union_parent_coverage_passes":sum(bool(x["parent_coverage_pass"]) for x in result["cases"]),
      "invalid_landareal_features":result["source_products"]["kartverket"]["invalid_landareal_count"],
      "cases_flagged_by_invalid_source_bbox":sum(bool(x["invalid_landareal_source_bbox_overlaps"] or x["invalid_kystkontur_source_bbox_overlaps"]) for x in result["cases"]),
      "physical_applicability_resolved_cases":0,"correction_proposals":0,
    }
    metric_path=OWNED+"metric-values.json"
    metric_obj={"method_id":METHOD,"values":vals,"result_sha256":result_sha}
    metric_file=REPO/metric_path
    if not metric_file.exists(): metric_file.write_text(json.dumps(metric_obj,indent=2)+"\n")
    elif json.loads(metric_file.read_text())!=metric_obj: raise SystemExit("metric-values.json already exists with different contents")
    metric_desc=current_descriptor(metric_path)
    # The metric ledger is itself an output and is rebuilt before this inventory.
    if not any(x["path"]==metric_path for x in output_files): output_files.append(metric_desc)
    metrics=[];bindings=[];summaries=[]
    texts={
      "case_rows":"Assigned physical-applicability case rows","candidate_context_count":"Preserved selected candidate context","family_member_count":"Preserved full source-family members","neighbor_id_count":"Preserved positive-length neighbor IDs","neighbor_relation_rows":"Own-target plus neighbor relation rows","evaluated_neighbor_relations":"Measured non-target neighbor relations","own_target_rows":"Preserved own-target relation rows","added_area_receipt_matches":"Added-area geometries matching pinned #1492 receipts","strict_no_loss_passes":"Projected strict no-loss predicates returning empty","strict_no_loss_nonempty_residuals":"Projected strict no-loss predicates with nonempty residuals","full_union_parent_coverage_passes":"Full proposed T union C parent-coverage predicates passing","invalid_landareal_features":"Invalid Landareal source polygons excluded unrepaired","cases_flagged_by_invalid_source_bbox":"Cases flagged by invalid-source bounding-box overlap","physical_applicability_resolved_cases":"Cases with physical applicability resolved","correction_proposals":"Correction geometries proposed",
    }
    units={k:"cases" if k in ("case_rows","physical_applicability_resolved_cases","cases_flagged_by_invalid_source_bbox","correction_proposals") else "rows" if "rows" in k or "relations" in k else "members" if k=="family_member_count" else "IDs" if k=="neighbor_id_count" else "features" if k=="invalid_landareal_features" else "components" for k in vals}
    for key,value in vals.items():
        # Run 004 was evaluated before the PR base advanced. Preserve that
        # original evaluation commit as archived evidence instead of labeling
        # unchanged historical measurements as current on a later PR base.
        metrics.append({"id":key,"value":value,"unit":units[key],"input_sha256":result_sha,"input_file":{"path":result_path,"commit":"candidate"},"vintage":"archived","evaluation_commit":RUN_EVALUATION_BASE})
        bindings.append({"metric_id":key,"path":metric_path,"json_pointer":"/values/"+key})
        summaries.append({"metric_id":key,"text":texts[key],"value":value,"unit":units[key]})

    retrieval=max(x["retrieved_at"] for x in source_index["captures"])
    sources=[
      {"id":"kartverket-sjoekart-dybdedata","url":source_index["endpoint"],"role":"Mean-high-water coastline and saltwater-only chart-derived land context for local physical-applicability diagnostics","vintage":"Dynamic WFS; exact 2026-10-08 bounded responses with per-feature dates retained in source-snapshot-index.json","retrieved_at":retrieval,"license":{"status":"redistributable","terms":"CC BY 4.0; attribute Kartverket"},"retention":"retained","verification":"verified","temporal_status":"reference","files":wfs_files},
      {"id":"nor-adm2-simplified-2013","url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NOR/ADM2/geoBoundaries-NOR-ADM2_simplified.geojson","role":"Same-ID 2013 ADM2 source comparison; not physical-land proof","vintage":"Represented year 2013","retrieved_at":"2026-10-08T17:45:19Z","license":{"status":"redistributable","terms":"Creative Commons Attribution 4.0 International (CC BY 4.0)"},"retention":"restoration-only","restoration":f"Read immutable bytes at {PREDECESSOR_COMMIT}:research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm2-simplified.geojson","verification":"verified","temporal_status":"reference","limit":"Simplified administrative source comparison only; not evidence of physical land, water, or shoreline."},
      {"id":"nor-adm1-simplified-2022","url":"https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NOR/ADM1/geoBoundaries-NOR-ADM1_simplified.geojson","role":"Parent-coverage diagnostics","vintage":"Represented year 2022","retrieved_at":"2026-10-08T17:45:19Z","license":{"status":"redistributable","terms":"Creative Commons Attribution 4.0 (CC BY 4.0)"},"retention":"restoration-only","restoration":f"Read immutable bytes at {PREDECESSOR_COMMIT}:research/geography/norway-adm2-source-fit-1492/vintages/official-source-capture-20261008/adm1-simplified.geojson","verification":"verified","temporal_status":"reference","limit":"The 2022 ADM1 and 2013 ADM2 products have different editions; parent diagnostics do not certify new administrative authority."},
      {"id":"norway-n50-reference","url":"https://kartkatalog.geonorge.no/metadata/uuid/ea192681-d039-42ec-b1bc-f3ce04c189ac","role":"Generalized topographic reference reviewed for applicability","vintage":"Product sheet 2026-09-01","retrieved_at":"2026-10-08T19:02:00Z","license":{"status":"redistributable","terms":"N50 Kartdata CC BY 4.0; attribution as stated in product metadata"},"retention":"restoration-only","restoration":"Use the exact Geonorge metadata and product-sheet URLs recorded in source-scout.json; local product-sheet bytes are retained as packet outputs.","verification":"verified","temporal_status":"reference","limit":"N50 is generalized 1:50,000 and explicitly contains no sea information; it cannot classify these shoreline-sensitive added areas."},
      {"id":"norway-fkb-vann-reference","url":"https://dokument.geonorge.no/produktspesifikasjoner/fkb-vann/Versjon%205.1/index.html","role":"Potential topographic coast/sea reference; dataset not acquired","vintage":"Product specification 5.1 published 2024-07-01; product sheet 2025-01-07","retrieved_at":"2026-10-08T19:02:00Z","license":{"status":"restricted","terms":"Norway Digital license; product sheet restricts download to agreement parties"},"retention":"restoration-only","restoration":"Use Geonorge FKB-Vann specification and product-sheet URLs recorded in source-scout.json; exact spatial data requires authorized Norway Digital access.","verification":"verified","temporal_status":"reference","limit":"No FKB-Vann spatial geometry was acquired; metadata cannot establish exact candidate land/water applicability."},
    ]
    # Check required raw source bytes and results fit ordinary evidence limits.
    descriptors=baseline_files+wfs_files+output_files
    if any(x["bytes"]>32*1024*1024 for x in descriptors) or sum(x["bytes"] for x in descriptors)>256*1024*1024:
        raise SystemExit("Evidence file or total byte budget exceeded")
    manifest={
      "version":1,"issue":BASE_ISSUE,"lane":"geography","worker_id":"01a112b9-e2b7-7d03-8000-eb2890649612",
      "subject_ids":subject_ids,"subject_ids_sha256":subjects_hash(subject_ids),
      "component_ids":subject_ids,"component_ids_sha256":subjects_hash(subject_ids),
      "baseline":{"version":2,"commit":base,"files":baseline_files,"subject_files":source_subjects,"pins":pins,"pin_files":pin_paths},
      "sources":sources,"outputs":sorted(output_files,key=lambda x:x["path"]),
      "methods":[{"id":METHOD,"kind":"measurement","description":"Bounded seven-case exact source/topology and mean-high-water shoreline diagnostics with exact 15/400/36 context. No source repair, snap, buffer, or tolerance.","software":result["method"]["software"]["python"].splitlines()[0]+"; Shapely "+result["method"]["software"]["shapely"]+"; GEOS "+result["method"]["software"]["geos"]+"; pyproj "+result["method"]["software"]["pyproj"],"units":"Per-metric units in the ledger; projected area and distance diagnostics use EPSG:25833 metres.","axis_order":"longitude-latitude for GeoJSON; EPSG:4258 GML axes reordered from latitude-longitude","crs":"WGS84 GeoJSON and EPSG:4258 GML, projected to EPSG:25833 for area/distance diagnostics","area_method":"Shapely/GEOS planar overlays in EPSG:25833; exact reported residuals, no epsilon or geometry repair","distance_method":"Shapely/GEOS planar distance in EPSG:25833; diagnostic only"}],
      "metrics":metrics,"metric_bindings":bindings,"summaries":summaries,
      "validation":[{"method_id":METHOD,"kind":"positive-control","outcome":"passed","evidence_path":OWNED+"control-positive.json"},{"method_id":METHOD,"kind":"negative-control","outcome":"passed","evidence_path":OWNED+"control-negative.json"}],
      "conclusions":[
        {"status":"supported","text":"All seven exact candidate-minus-target geometries reproduce the pinned #1492 receipts; the full 15/400/36 context remains intact with 252 neighbor relation rows.","source_ids":["nor-adm2-simplified-2013","nor-adm1-simplified-2022"]},
        {"status":"unresolved","text":"No independent evidence establishes physical applicability for any of the seven additions. Kartverket mean-high-water and saltwater-only chart products have variable feature dates and no exposed positional-quality attributes; N50 contains no sea information, and no authorized FKB-Vann geometry was acquired.","source_ids":["kartverket-sjoekart-dybdedata","norway-n50-reference","norway-fkb-vann-reference"]},
        {"status":"unresolved","text":"Three invalid Landareal source polygons are excluded unrepaired. Conservative invalid-source bounding-box overlap flags Dønna and Sortland; both remain unresolved. All component class, water/ice status, territorial authority, history, cause, rights, and ownership remain unknown.","source_ids":["kartverket-sjoekart-dybdedata"]},
        {"status":"unresolved","text":"The projected full-union parent predicate is false for all seven; projected strict no-loss is nonempty for Lurøy and Vefsn with the exact residuals retained. Raw-domain additive parent and set-preservation predicates were not measured in this run; no correction proposal is made.","source_ids":["nor-adm1-simplified-2022","nor-adm2-simplified-2013"]},
      ],
      "stages":{"research":"complete","implementation":"not-proposed","geographic_approval":"unapproved"},
      "commands":["python3.12 research/geography/norway-seven-physical-applicability-20261008/verify_sjoekart_capture.py","python3.12 research/geography/norway-seven-physical-applicability-20261008/validate_result_controls.py","python3.12 research/geography/norway-seven-physical-applicability-20261008/capture_geometry_admission.py (fresh admission only; refuses replacement)","python3.12 research/geography/norway-seven-physical-applicability-20261008/run_geometry_phase.py (only after the serialized admission passes)","node scripts/evidence-quality.mjs research/geography/norway-seven-physical-applicability-20261008/evidence-quality.json"],
      "change_receipts":changed_files(base),
      "limits":["Physical applicability remains unresolved for all seven candidates; source overlap is not a land/water determination.","Kartverket Sjøkart Dybdedata is dynamically served, saltwater-only, not for navigation; mean-high-water Kystkontur records expose no positional-quality/coastline-category field and feature ages vary.","Three invalid Landareal polygons were excluded without repair; their bounding boxes flag Dønna and Sortland, not exact invalid-polygon intersections.","Parent result measures full projected T∪C coverage by lower-dated simplified 2022 ADM1; it is not the #1492 candidate-only predicate.","Projected strict no-loss residuals of 3.0329804438897386e-9 m² (Lurøy) and 1.1650589381911533e-7 m² (Vefsn) remain literal failures; no tolerance was applied.","Original-coordinate no-loss and additive parent-exclusion predicates from the issue's exact additive-repair clarification were not measured; no proposed correction is supported.","No independent water/ice source, territorial authority, history, cause, rights, or ownership is established."],
      "retained_artifacts":[{"path":result_path,"sha256":result_sha,"status":"bounded exact diagnostic; no cases accepted for correction"}]
    }
    # Every source/output byte descriptor is unique in its role; canonical JSON
    # is written atomically with an exclusive create to preserve prior receipts.
    raw=(json.dumps(manifest,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
    tmp=OUTPUT.with_suffix(".json.tmp")
    with tmp.open("wb") as f: f.write(raw);f.flush();os.fsync(f.fileno())
    if OUTPUT.exists(): tmp.replace(OUTPUT)
    else: tmp.rename(OUTPUT)
    print(json.dumps({"manifest":OWNED+"evidence-quality.json","sha256":sha(raw),"bytes":len(raw),"baseline_files":len(baseline_files),"sources":len(sources),"source_files":sum(len(s.get("files",[])) for s in sources),"outputs":len(output_files),"subjects":len(source_subjects),"change_receipts":len(manifest["change_receipts"]),"metric_count":len(metrics),"baseline_commit":base},indent=2))

if __name__=="__main__": main()

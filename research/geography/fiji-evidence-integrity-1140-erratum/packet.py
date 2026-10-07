"""Shared, bounded evidence logic for the Fiji PR #1140 erratum."""
from __future__ import annotations

import hashlib
import builtins
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
OWNED = "research/geography/fiji-evidence-integrity-1140-erratum/"
BASELINE_COMMIT = "09c2dcff4f5acd92936fdd49378dd563332a1187"
HELPER_COMMIT = BASELINE_COMMIT
SHARED_WRITER_COMMIT = "839883ae281af7bf012f694698624a7ec77275e1"
SHARED_WRITER_PATH = "scripts/evidence/immutable.py"
SHARED_WRITER_SHA256 = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
ISSUE_FILE = ROOT / "issue-1361-contract.json"
CLAIM_FILE = ROOT / "claim-receipt.json"
UPSTREAM_FILE = ROOT / "source-provenance-correction.json"
EXPECTED_WORKER = "01a10947-7d6e-7ba2-98a1-a9f91dedabfc"
EXPECTED_BRANCH = "geography/fiji-evidence-integrity-1361-20261007"
SOURCE_PATH = "data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-FJI-ADM2.geojson"
META_PATH = "data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-FJI-ADM2-metaData.json"
API_PATH = "data/regional-review/fiji-admin-source-reconciliation-20261005/sources/geoBoundaries-api-current-FJI-ADM2.json"
CITATION_PATH = "data/regional-review/fiji-admin-source-reconciliation-20261005/sources/CITATION-AND-USE-geoBoundaries.txt"
UPSTREAM_COMMIT = "9469f09592ced973a3448cf66b6100b741b64c0d"
UPSTREAM_BLOBS = {
    SOURCE_PATH: "a55fc77ef79cfc65ea2bbaf1036d9832d57c5beb",
    META_PATH: "8a798505b2cfd83546e8fcc9a59b5643be60987b",
    CITATION_PATH: "ff1d1d9a4ab9c714a5a60eca051696f41446a086",
}
EXPECTED_SOURCE_SHA = "a9cd94789cb5eb66cfbcbaf32a21bcbceba16b9a76adacba9ac675b950ca1ccd"
EXPECTED_SOURCE_BYTES = 1_357_011
OUTPUTS = ["audit.json", "positive-control.json", "negative-controls.json", "execution-bindings.json", "run-metadata.json"]


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode()


def descriptor(path: str, raw: bytes) -> dict:
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def git_blob(path: str, commit: str = BASELINE_COMMIT) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{commit}:{path}"])


class CompositeBaseline:
    """Read issue-pinned files from their recorded immutable Git snapshots."""
    def __init__(self, pins, raws):
        self.repo=str(REPO); self.commit=BASELINE_COMMIT; self.pins=pins
        self.raws=raws; self.consumed={}; self.max_phase_bytes=256*1024*1024
    def read(self, name):
        if name in self.raws:
            raw=self.raws[name]
        else:
            raw=git_blob(name, BASELINE_COMMIT)
        if name not in self.consumed:
            if sum(self.consumed.values())+len(raw)>self.max_phase_bytes: raise ValueError("Evidence phase exceeds byte budget")
            self.consumed[name]=len(raw)
        return raw
    def pinned_bytes(self, name):
        if name not in self.pins: raise ValueError("Consumed input lacks exact issue pin: "+name)
        raw=self.read(name)
        if sha(raw)!=self.pins[name]: raise ValueError("Pinned evidence hash mismatch: "+name)
        return raw
    def subjects(self, ids, index="data/world-index.json"):
        parts=json.loads(self.pinned_bytes(index))["parts"]
        found={}; containing={}; all_ids=set(); root=str(Path(index).parent)
        for part in parts:
            name=root+"/"+part; raw=self.read(name)
            if name.endswith(".gz"):
                import gzip,io
                with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: body=stream.read(32*1024*1024+1)
                if len(body)>32*1024*1024: raise ValueError("Indexed geography part exceeds limit")
            else: body=raw
            for feature in json.loads(body)["features"]:
                ident=feature.get("id") or (feature.get("properties") or {}).get("id")
                if not ident or ident in all_ids: raise ValueError("Missing or duplicate indexed identity")
                all_ids.add(ident)
                if ident in ids:
                    found[ident]=feature; containing[ident]=descriptor(name,raw)
        if set(found)!=set(ids): raise ValueError("Issue subjects absent from complete pinned world index")
        return found,containing


def shared_new_vintage(baseline):
    """Load the exact shared whole-run writer reviewed on the PR base commit."""
    raw = git_blob(SHARED_WRITER_PATH, SHARED_WRITER_COMMIT)
    if sha(raw) != SHARED_WRITER_SHA256:
        raise ValueError("Shared evidence writer differs from its reviewed immutable pin")
    module = types.ModuleType("worldatlas_shared_immutable_writer")
    module.__file__ = f"pinned:{SHARED_WRITER_COMMIT}:{SHARED_WRITER_PATH}"
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module.NewVintage, {**descriptor(SHARED_WRITER_PATH, raw), "commit": SHARED_WRITER_COMMIT}


def json_file(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_work(issue):
    body = issue.get("body") or ""
    start = body.index("<!-- worldatlas-work:v1")
    end = body.index("-->", start)
    return json.loads(body[body.index("{", start):end])


def load_context():
    issue = json_file(ISSUE_FILE)
    claim = json_file(CLAIM_FILE)
    if issue.get("number") != 1361 or issue.get("state") != "open":
        raise ValueError("Issue snapshot must be the open exact issue #1361")
    work = parse_work(issue)
    if work.get("mode") != "geography" or work.get("max_prs") != 1 or work.get("owned_paths") != [OWNED]:
        raise ValueError("Issue contract scope/mode/ownership mismatch")
    ids = work["evidence_quality"]["subject_ids"]
    if len(ids) != 15 or len(ids) != len(set(ids)):
        raise ValueError("Issue scope must contain exactly 15 unique subjects")
    c = claim.get("claim", {})
    if not claim.get("accepted") or claim.get("issue_number") != 1361 or c.get("active") is not True:
        raise ValueError("Claim receipt is not accepted and active")
    if c.get("worker_id") != EXPECTED_WORKER or c.get("branch") != EXPECTED_BRANCH or c.get("owned_paths") != [OWNED]:
        raise ValueError("Claim receipt identity, branch or ownership mismatch")
    pins = work["evidence_quality"]["pins"]
    if not isinstance(pins, dict) or not pins:
        raise ValueError("Issue has no exact source/baseline pin map")
    descriptors = []; raws={}; provenance={}
    for path, expected in sorted(pins.items()):
        commit=HELPER_COMMIT if path in ("scripts/evidence/geometry.py","scripts/evidence/immutable.py") else BASELINE_COMMIT
        raw = git_blob(path,commit)
        if sha(raw) != expected:
            raise ValueError(f"Declared issue pin is not present in its captured Git snapshot: {path}")
        raws[path]=raw; provenance[path]=commit
        descriptors.append(descriptor(path, raw))
    baseline = CompositeBaseline(pins,raws)
    writer_type, writer_descriptor = shared_new_vintage(baseline)
    baseline_raw = {d["path"]: baseline.pinned_bytes(d["path"]) for d in descriptors}
    area_module=types.ModuleType("worldatlas_pinned_area")
    area_raw=raws["scripts/ellipsoidal_area.py"]; exec(compile(area_raw,"pinned:scripts/ellipsoidal_area.py","exec"),area_module.__dict__)
    geometry_module=types.ModuleType("worldatlas_pinned_geometry")
    geometry_raw=raws["scripts/evidence/geometry.py"]
    geometry_module.__dict__["__builtins__"]=vars(builtins)
    sys.modules["ellipsoidal_area"]=area_module
    exec(compile(geometry_raw,"pinned:scripts/evidence/geometry.py","exec"),geometry_module.__dict__)
    METHOD,VERSION=geometry_module.METHOD,geometry_module.VERSION
    from shapely.geometry import shape
    issue_hash = sha(ISSUE_FILE.read_bytes())
    claim_hash = sha(CLAIM_FILE.read_bytes())
    upstream = json_file(UPSTREAM_FILE)
    return {
        "issue": issue, "work": work, "ids": sorted(ids), "claim": claim,
        "baseline": baseline, "baseline_raw": baseline_raw, "pins": pins, "NewVintage": writer_type,
        "shared_writer": writer_descriptor,
        "pin_commits":provenance,
        "geometry": (METHOD, VERSION, geometry_module.canonical_land, geometry_module.land_area_m2, geometry_module.transform_point, shape),
        "issue_sha256": issue_hash, "claim_sha256": claim_hash, "upstream": upstream,
    }


def reject(condition, reason):
    if condition:
        raise ValueError(reason)


def validate_crosswalk(ids, atlas_features, source_features, hierarchy):
    """Return an exact identity crosswalk or reject incomplete/substituted rows."""
    reject(not isinstance(ids, list) or not ids, "empty issue scope")
    reject(len(ids) != len(set(ids)), "duplicate issue subject")
    source_rows = []
    for feature in source_features:
        props = feature.get("properties") or {}
        source_id = props.get("shapeID")
        reject(not isinstance(source_id, str) or not source_id, "missing source shapeID")
        source_rows.append((source_id, feature))
    source_ids = [x[0] for x in source_rows]
    reject(len(source_ids) != len(set(source_ids)), "duplicate source shapeID")
    suffixes = [x.rsplit(":", 1)[-1] for x in ids]
    reject(set(source_ids) != set(suffixes) or len(source_ids) != len(ids), "source roster differs from exact issue subjects")
    source_by_id = dict(source_rows)
    rows = []
    for ident in sorted(ids):
        atlas = atlas_features.get(ident)
        reject(atlas is None, "issue subject absent from indexed Atlas baseline: " + ident)
        props = atlas.get("properties") or {}
        source = source_by_id.get(ident.rsplit(":", 1)[-1])
        reject(source is None, "issue subject has no native source shapeID: " + ident)
        source_props = source.get("properties") or {}
        reject(source_props.get("shapeGroup") != "FJI", "source shapeGroup is not Fiji: " + ident)
        reject(source_props.get("shapeName") != props.get("name"), "source name disagrees with Atlas name: " + ident)
        parent_id = props.get("parent_id")
        parent = hierarchy.get(parent_id)
        reject(parent is None, "Atlas parent ID absent from pinned hierarchy: " + ident)
        geometry = source.get("geometry")
        reject(not geometry, "source geometry is missing: " + ident)
        geom = __import__("shapely.geometry", fromlist=["shape"]).shape(geometry)
        rows.append({
            "subject_id": ident,
            "source_shape_id": source_props["shapeID"],
            "source_name": source_props["shapeName"],
            "source_shape_type": source_props.get("shapeType"),
            "source_shape_group": source_props.get("shapeGroup"),
            "source_geometry_type": geom.geom_type,
            "source_geometry_valid": bool(geom.is_valid),
            "source_polygon_components": len(geometry.get("coordinates", [])),
            "atlas_name": props.get("name"),
            "atlas_parent_id": parent_id,
            "atlas_parent_name": parent.get("name"),
            "baseline_containing_file": "data/geography/part-8.json",
            "identity_result": "exact native shapeID suffix and exact name match",
            "territorial_role": "source labels the row Province/ADM2; Fiji official sources distinguish 14 provinces from Rotuma inconsistently across statistical and government contexts",
            "legal_parent_and_current_boundary": "unresolved; this evidence confirms identity against pinned records, not statutory parentage or current boundaries",
        })
    return rows


def calculate(ctx):
    baseline, ids = ctx["baseline"], ctx["ids"]
    world = baseline.pinned_bytes("data/world-index.json")
    atlas_features, containing = baseline.subjects(ids)
    if set(containing) != set(ids):
        raise ValueError("Complete immutable world-index lookup did not return all issue subjects")
    hierarchy = {x["id"]: x for x in json.loads(baseline.pinned_bytes("data/hierarchy.json"))}
    source_raw = baseline.pinned_bytes(SOURCE_PATH)
    if len(source_raw) != EXPECTED_SOURCE_BYTES or sha(source_raw) != EXPECTED_SOURCE_SHA:
        raise ValueError("Retained original source bytes disagree with pinned LFS content identity")
    source_doc = json.loads(source_raw)
    source_features = source_doc.get("features", [])
    rows = validate_crosswalk(ids, atlas_features, source_features, hierarchy)
    meta = json.loads(baseline.pinned_bytes(META_PATH))
    current_api = json.loads(baseline.pinned_bytes(API_PATH))
    registry = json.loads(baseline.pinned_bytes("data/administrative-sources.json"))
    if meta.get("boundaryYear") != "2020" or "boundaryYearRepresented" in meta:
        raise ValueError("Pinned release metadata year field/value changed from the audited record")
    if current_api.get("boundaryYearRepresented") != "2020":
        raise ValueError("Retained current API represented-year field changed")
    if "sha256" in meta or "sha256" in current_api:
        raise ValueError("Expected source metadata sha256 field absence must be explicitly reconciled")
    lau_id = "gb:FJI:ADM2:14151628B80423492752803"
    source_by_id = {f["properties"]["shapeID"]: f for f in source_features}
    native_lau = source_by_id[lau_id.rsplit(":", 1)[-1]]
    atlas_lau = atlas_features[lau_id]
    METHOD, VERSION, canonical_land, land_area_m2, transform_point, shape = ctx["geometry"]
    left = canonical_land(shape(native_lau["geometry"]))
    right = canonical_land(shape(atlas_lau["geometry"]))
    intersection = land_area_m2(left.intersection(right))
    union = land_area_m2(left.union(right))
    difference = land_area_m2(left.symmetric_difference(right))
    jaccard = intersection / union
    source_ids = [x["properties"]["shapeID"] for x in source_features]
    parent_ids = sorted({x["atlas_parent_id"] for x in rows})
    x, y = transform_point(10, 45, "EPSG:3857")
    if abs(x - 1_113_194.9079) >= 1 or abs(y - 5_621_521.486) >= 1:
        raise ValueError("Longitude-first EPSG:4326 axis control failed")
    audit = {
        "version": 1,
        "issue": 1361,
        "evaluation_commit": BASELINE_COMMIT,
        "scope": {
            "issue_subject_count": len(ids),
            "unique_atlas_subject_count": len(atlas_features),
            "source_feature_count": len(source_features),
            "crosswalk_count": len(rows),
            "all_subjects_in_part_8": set(containing) == set(ids) and {v["path"] for v in containing.values()} == {"data/geography/part-8.json"},
            "source_roster_exactly_matches_15_issue_suffixes": set(source_ids) == {x.rsplit(":", 1)[-1] for x in ids} and len(source_ids) == len(ids),
            "atlas_parent_ids_present_in_pinned_hierarchy": all(x["atlas_parent_id"] in hierarchy for x in rows),
            "atlas_parent_ids": parent_ids,
        },
        "source": {
            "upstream_commit": UPSTREAM_COMMIT,
            "upstream_geojson_git_blob": UPSTREAM_BLOBS[SOURCE_PATH],
            "geojson_lfs_oid_sha256": EXPECTED_SOURCE_SHA,
            "whole_source_bytes": EXPECTED_SOURCE_BYTES,
            "boundary_id": meta.get("boundaryID"),
            "boundary_type": meta.get("boundaryType"),
            "boundary_canonical": meta.get("boundaryCanonical"),
            "source_update_date": meta.get("sourceDataUpdateDate"),
            "build_date": meta.get("buildDate"),
            "boundary_year_actual_key": meta.get("boundaryYear"),
            "boundary_year_represented_key_absent": "boundaryYearRepresented" not in meta,
            "api_boundary_year_represented": current_api.get("boundaryYearRepresented"),
            "sha256_key_absent_in_release_metadata": "sha256" not in meta,
            "sha256_key_absent_in_current_api": "sha256" not in current_api,
            "source_license": meta.get("boundaryLicense"),
            "source_count_declared": meta.get("admUnitCount"),
            "atlas_source_registry_bytes_sha256": sha(baseline.pinned_bytes("data/administrative-sources.json")),
            "source_registry_record_observed": "Original Fiji record is pinned in the administrative source registry; its historical digest recipe is not asserted as recovered.",
            "source_feature_count": len(source_features),
            "source_feature_roster": [x["properties"]["shapeName"] for x in source_features],
        },
        "subjects": rows,
        "lau_outline_comparison": {
            "subject_id": lau_id,
            "source_vertices": sum(len(ring) for poly in native_lau["geometry"]["coordinates"] for ring in poly),
            "source_polygon_components": len(native_lau["geometry"]["coordinates"]),
            "source_geometry_valid": bool(shape(native_lau["geometry"]).is_valid),
            "intersection_m2": intersection,
            "union_m2": union,
            "jaccard": jaccard,
            "symmetric_difference_m2": difference,
            "symmetric_difference_km2": difference / 1_000_000,
            "method": METHOD,
            "interpretation": "Reproducible shape divergence only; neither outline is thereby selected as current or legally authoritative.",
        },
        "source_and_territorial_limits": [
            "SPC Pacific Data Hub describes the linked 2007 layer as boundaries used for the 2007 Fiji Population and Housing Census and warns upper-level units may differ from official boundaries and do not imply SPC endorsement; exact page bytes were not retrievable by direct HTTP on 2026-10-07.",
            "geoBoundaries release metadata says boundaryYear=2020; its own citation defines boundaryYear as representative year(s). boundaryYearRepresented is absent in the pinned file, not null. The current API separately reports boundaryYearRepresented=2020. Source-data update/build dates are 2023; these statements do not establish which legal boundaries the geometry represents.",
            "Fiji Government's 2025 statement says four divisions and fourteen provinces, then later in the same statement refers to fifteen provinces including Rotuma. The iTaukei Affairs Board page lists fourteen named provinces; the Fiji census treats Rotuma as a separate statistical roster column. This is a real terminology/context conflict; Rotuma classification and Atlas parent/category remain unresolved.",
            "The 15-row source and issue rosters agree for this exact scope only. Current legal edge authority, small-island completeness, neighboring administrative boundary coverage, and source-to-Atlas boundary correctness remain unestablished.",
            "CC BY 4.0 is the geoBoundaries product license with attribution. The cited Pacific Data Hub record states Creative Commons Attribution without specifying a version; upstream rights/authority beyond those catalog statements are not independently established.",
            "The prior issue #910 packet's unretained 2017 census PDF and 2024 Hansard bodies are not reauthenticated here; they remain restoration-only prior findings, not newly inspected primary text.",
        ],
        "runtime": {"python": sys.version.split()[0], "shapely": __import__("shapely").__version__, "pyproj": __import__("pyproj").__version__, "numpy": __import__("numpy").__version__, "geometry_helper": VERSION, "geometry_method": METHOD},
    }
    return audit, rows, atlas_features, source_features, hierarchy


def make_controls(ctx, atlas_features, source_features, hierarchy, rows):
    ids = ctx["ids"]
    positive = {
        "version": 1, "issue": 1361, "method_id": "fiji-15-subject-source-identity-and-lau-diagnostic-v1",
        "kind": "positive-control", "outcome": "passed", "passed_controls": 4,
        "controls": [
            {"name": "exact scoped roster", "outcome": "passed", "observed": f"{len(rows)} unique issue subjects joined to {len(source_features)} unique source features"},
            {"name": "native identity and exact display name", "outcome": "passed", "observed": "all 15 suffix IDs and names match the pinned source layer and Atlas rows"},
            {"name": "hierarchy reference integrity", "outcome": "passed", "observed": "each retained Atlas parent ID resolves in the pinned hierarchy"},
            {"name": "longitude-first axis", "outcome": "passed", "observed": "10E,45N transforms through the pinned helper to EPSG:3857 within 1 m"},
        ],
    }
    cases=[]
    def rejected(name, changed_ids, changed_atlas, changed_source, why):
        fixture={"ids":changed_ids,"source_shape_ids":[(x.get("properties") or {}).get("shapeID") for x in changed_source],"reason":why}
        try:
            validate_crosswalk(changed_ids,changed_atlas,changed_source,hierarchy)
        except (ValueError, TypeError, KeyError) as error:
            cases.append({"name":name,"outcome":"rejected","entry_point":"packet.validate_crosswalk","expected_failure":why,"observed_error":str(error),"fixture_sha256":sha(canonical(fixture))})
        else:
            raise AssertionError("Adverse identity fixture was accepted: "+name)
    rejected("duplicate issue identity", ids+[ids[0]], atlas_features, source_features, "duplicate issue subject")
    rejected("missing source feature", ids, atlas_features, source_features[:-1], "source roster differs")
    rejected("fabricated issue ID", ids+["gb:FJI:ADM2:14151628B99999999999999"], atlas_features, source_features, "source roster differs")
    wrong=[json.loads(json.dumps(x)) for x in source_features]
    wrong[0]["properties"]["shapeName"]="AUDITOR-FABRICATED-WRONG-NAME"
    rejected("substituted source name", ids, atlas_features, wrong, "source name disagrees")
    wrong_parent={k:json.loads(json.dumps(v)) for k,v in atlas_features.items()}
    first=ids[0]; wrong_parent[first]["properties"]["parent_id"]="framework:province:NONEXISTENT"
    rejected("unknown parent identity", ids, wrong_parent, source_features, "Atlas parent ID absent")
    negative={"version":1,"issue":1361,"method_id":"fiji-15-subject-source-identity-and-lau-diagnostic-v1","kind":"negative-control","outcome":"passed","passed_controls":len(cases),"controls":cases}
    return positive, negative


def code_bindings():
    rows=[]
    for name in ("packet.py","reproduce.py"):
        path=ROOT/name
        if path.is_file():
            raw=path.read_bytes()
            rows.append(descriptor(str(path.relative_to(REPO)),raw))
    raw=git_blob(SHARED_WRITER_PATH,SHARED_WRITER_COMMIT)
    if sha(raw)!=SHARED_WRITER_SHA256:
        raise ValueError("Shared evidence writer differs from its reviewed immutable pin")
    rows.append({**descriptor(f"git:{SHARED_WRITER_COMMIT}:{SHARED_WRITER_PATH}",raw),"commit":SHARED_WRITER_COMMIT})
    return rows


def run_products(vintage: str, fail_after_compute: bool = False):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        raise ValueError("Unsafe vintage name")
    ctx=load_context()
    baseline=ctx["baseline"]
    writer=ctx["NewVintage"](baseline,OWNED,vintage,OUTPUTS)
    audit,rows,atlas_features,source_features,hierarchy=calculate(ctx)
    positive,negative=make_controls(ctx,atlas_features,source_features,hierarchy,rows)
    code=code_bindings()
    bindings={
        "version":1,"issue":1361,"baseline_commit":BASELINE_COMMIT,"pin_commits":ctx["pin_commits"],
        "issue_snapshot":descriptor("research/geography/fiji-evidence-integrity-1140-erratum/issue-1361-contract.json",ISSUE_FILE.read_bytes()),
        "claim_receipt":descriptor("research/geography/fiji-evidence-integrity-1140-erratum/claim-receipt.json",CLAIM_FILE.read_bytes()),
        "source_correction_record":descriptor("research/geography/fiji-evidence-integrity-1140-erratum/source-provenance-correction.json",UPSTREAM_FILE.read_bytes()),
        "executed_code":code,
        "shared_writer":ctx["shared_writer"],
        "pinned_inputs":[descriptor(name,baseline.pinned_bytes(name) if name in baseline.pins else git_blob(name)) for name in sorted(baseline.consumed)],
        "source_lfs_content":descriptor(SOURCE_PATH,baseline.pinned_bytes(SOURCE_PATH)),
        "output_inventory":OUTPUTS,
        "immutable_reader":"CompositeBaseline reads exact issue-pinned and baseline Git objects directly; complete output admission and publication use the exact shared writer pinned above",
    }
    import datetime, secrets
    runtime={"version":1,"issue":1361,"vintage":vintage,"execution_id":secrets.token_hex(16),"process_id":os.getpid(),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"command":sys.argv,"status":"complete"}
    products={"audit.json":audit,"positive-control.json":positive,"negative-controls.json":negative,"execution-bindings.json":bindings,"run-metadata.json":runtime}
    if fail_after_compute:
        raise RuntimeError("audit-injected failure after calculation; no output was published")
    return writer.publish(products)


def validate_run(vintage: str, ctx, expected_audit, expected_positive, expected_negative):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", vintage):
        raise ValueError("Unsafe vintage name")
    root=ROOT/"vintages"/vintage
    if root.is_symlink() or not root.is_dir(): raise ValueError(f"missing whole run: {vintage}")
    expected=set(OUTPUTS)|{"publication.json"}
    actual={x.name for x in root.iterdir()}
    if actual!=expected or any(x.is_symlink() or not x.is_file() for x in root.iterdir()):
        raise ValueError(f"incomplete or unexpected run product set: {vintage}")
    receipt=json_file(root/"publication.json")
    if receipt.get("version")!=1 or receipt.get("status")!="complete": raise ValueError("invalid whole-run completion receipt")
    records=receipt.get("outputs")
    if not isinstance(records,list) or {x.get("path") for x in records}!={f"{OWNED}vintages/{vintage}/{name}" for name in OUTPUTS}:
        raise ValueError("whole-run receipt inventory mismatch")
    for rec in records:
        path=root/Path(rec["path"]).name
        raw=path.read_bytes()
        if rec.get("bytes")!=len(raw) or rec.get("sha256")!=sha(raw): raise ValueError("output receipt digest mismatch: "+str(rec.get("path")))
    audit=json_file(root/"audit.json")
    pos=json_file(root/"positive-control.json")
    neg=json_file(root/"negative-controls.json")
    bindings=json_file(root/"execution-bindings.json")
    meta=json_file(root/"run-metadata.json")
    if canonical(audit)!=canonical(expected_audit): raise ValueError("run audit differs from independently recomputed exact pinned inputs")
    if canonical(pos)!=canonical(expected_positive) or canonical(neg)!=canonical(expected_negative): raise ValueError("run controls differ from independently executed controls")
    if bindings.get("issue_snapshot",{}).get("sha256")!=ctx["issue_sha256"] or bindings.get("claim_receipt",{}).get("sha256")!=ctx["claim_sha256"]:
        raise ValueError("run issue/claim bindings mismatch")
    if meta.get("status")!="complete" or not re.fullmatch(r"[0-9a-f]{32}",meta.get("execution_id","")):
        raise ValueError("run lacks a unique genuine execution receipt")
    return {"root":root,"receipt":receipt,"audit":audit,"positive":pos,"negative":neg,"bindings":bindings,"metadata":meta,"output_hashes":{n:sha((root/n).read_bytes()) for n in OUTPUTS}}

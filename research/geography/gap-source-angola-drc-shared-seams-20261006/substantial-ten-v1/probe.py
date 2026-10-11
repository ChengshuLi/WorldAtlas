"""Bounded strict predicates for the complete substantial AGO/COD family, not approval."""
import gzip, hashlib, io, json, os, pathlib, re, resource, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[4]
OWN = "research/geography/gap-source-angola-drc-shared-seams-20261006"
CONTROL = OWN + "/substantial-ten-v1"
HEAD, VINTAGE = sys.argv[1:3]
GIT = "/usr/local/bin/git"
CAP = 256 * 1024 * 1024
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def git(*args):
    return subprocess.check_output([GIT, "-C", str(ROOT), *args], stderr=subprocess.PIPE)
def frozen(name):
    raw = (ROOT / name).read_bytes()
    if len(raw) > 1024 * 1024 or raw != git("show", HEAD + ":" + name):
        raise ValueError("Unfrozen/oversized execution control: " + name)
    return raw
if len(HEAD) != 40 or git("rev-parse", HEAD + "^{commit}").decode().strip() != HEAD:
    raise ValueError("Exact committed execution head required")
controls = {name: frozen(CONTROL + "/" + name) for name in
            ["probe.py", "probe-inputs.json", "runtime-lock.json", "original-issue-snapshot.json"]}
plan, runtime = json.loads(controls["probe-inputs.json"]), json.loads(controls["runtime-lock.json"])
charge = sum(p["bytes"] + p.get("uncompressed_bytes", 0) for p in plan["files"])
charge += runtime["logical_bytes"] + sum(map(len, controls.values())) + plan["output_reserve_bytes"] + 4096
if charge > CAP or any(max(p["bytes"], p.get("uncompressed_bytes", 0)) > 32 * 1024**2 for p in plan["files"]):
    raise ValueError("Complete logical input/code/runtime/output admission failed")
if str(pathlib.Path(runtime["python_executable"]).resolve()) != str(pathlib.Path(sys.executable).resolve()):
    raise ValueError("Wrong interpreter")
if pathlib.Path(runtime["git_executable"]).resolve() != pathlib.Path(GIT).resolve():
    raise ValueError("Wrong Git executable")
if not os.environ.get("PYTHONDONTWRITEBYTECODE") or not os.environ.get("PYTHONPYCACHEPREFIX"):
    raise ValueError("Read-only runtime and fresh cache prefix required")
for f in runtime["files"]:
    p = pathlib.Path(f["path"])
    if p.stat().st_size != f["bytes"] or sha(p.read_bytes()) != f["sha256"]:
        raise ValueError("Runtime drift: " + f["path"])
helper = next(p for p in plan["files"] if p["path"] == "scripts/evidence/immutable.py")
raw = git("show", plan["baseline_commit"] + ":" + helper["path"])
if len(raw) != helper["bytes"] or sha(raw) != helper["sha256"]: raise ValueError("Helper drift")
ns = {"__name__": "bounded_immutable", "__file__": str(ROOT / helper["path"])}
exec(compile(raw, ns["__file__"], "exec"), ns)
class PinnedBaseline(ns["Baseline"]):
    def _git(self, *args): return git(*args)
base = PinnedBaseline(ROOT, plan["baseline_commit"], plan["files"])
for f in runtime["files"]: base.admit("runtime:" + f["path"], f["bytes"])
for name, raw in controls.items(): base.admit("control:" + name, len(raw))
base.admit("output-reservation", plan["output_reserve_bytes"])
dest = ns["NewVintage"](base, OWN + "/", VINTAGE, ["strict-predicates.json"])
canon = ns["canonical_json"]
# Derive the complete roster from the original issue independently of the plan rows.
body = json.loads(controls["original-issue-snapshot.json"])["body"]
blocks = [json.loads(x) for x in re.findall(r"```json\s*(.*?)\s*```", body, re.S)]
reference = next(x for x in blocks if isinstance(x, dict) and x.get("id") == plan["family_id"])
expected = reference["component_ids"]
if len(expected) != 10 or len(set(expected)) != 10 or reference["contact_ids"] != plan["contacts"]:
    raise ValueError("Independent original roster malformed")
subjects = plan["original_component_bindings"]
if len(subjects) != 10 or sorted(x["component"] for x in subjects) != sorted(expected):
    raise ValueError("Missing, duplicated or foreign original component")

def read(pin):
    raw = base.pinned_bytes(pin["path"])
    if "uncompressed_bytes" in pin:
        base.admit("decoded:" + pin["path"], pin["uncompressed_bytes"])
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: raw = stream.read(pin["uncompressed_bytes"] + 1)
        if len(raw) != pin["uncompressed_bytes"] or sha(raw) != pin["uncompressed_sha256"]:
            raise ValueError("Decoded original drift")
    return json.loads(raw)
originals = {}
for pin in plan["files"]:
    if "/custody-v1/payloads/" not in pin["path"]: continue
    features = read(pin)["features"]
    for row in subjects:
        binding = row["baseline_component"]
        if binding["containing_file"]["actual_retained_path"] != pin["path"]: continue
        f = features[binding["feature_index"]]
        if f["id"] != row["component"] or f["id"] in originals:
            raise ValueError("Original ordinal/identity mismatch")
        if sha(canon(f)) != binding["full_feature_sha256"] or sha(canon(f["geometry"])) != binding["geometry_sha256"]:
            raise ValueError("Original whole-feature/geometry mismatch")
        originals[f["id"]] = f
if set(originals) != set(expected): raise ValueError("Incomplete original custody")
from shapely.geometry import shape, mapping
from shapely.validation import explain_validity
import shapely, numpy
if (shapely.__version__, shapely.geos_version_string, numpy.__version__) != (runtime["shapely"], runtime["geos"], runtime["numpy"]):
    raise ValueError("Wrong scientific runtime versions")
exact = base.load_modules({"exact_predicates": "scripts/evidence/exact_predicates.py"})["exact_predicates"]
current = {}
for pin in plan["files"]:
    if not pin["path"].startswith("data/geography/"): continue
    data = read(pin)
    for f in data["features"] if isinstance(data, dict) else data:
        if f["id"] in current: raise ValueError("Duplicate current Atlas identity")
        current[f["id"]] = f
if any(i not in current for i in plan["contacts"]): raise ValueError("Missing recorded current neighbor")
sources = {}
for pin in plan["files"]:
    if "consumed-simplified.geojson" not in pin["path"]: continue
    data = read(pin)
    if data.get("crs", {}).get("properties", {}).get("name") != "urn:ogc:def:crs:OGC:1.3:CRS84":
        raise ValueError("Unaccepted native CRS/axis")
    for f in data["features"]:
        p = f["properties"]
        identity = "gb:" + p["shapeGroup"] + ":" + p["shapeType"] + ":" + p["shapeID"]
        if identity in sources: raise ValueError("Duplicate source identity")
        sources[identity] = f
if len(sources) != 350: raise ValueError("Missing whole consumed products")
provisional = plan["provisional_comparisons"]
if len(provisional) != 2 or len({r["component"] for r in provisional}) != 2:
    raise ValueError("Invalid provisional candidate roster")
source_geoms = {i: shape(f["geometry"]) for i, f in sources.items()}
current_geoms = {i: shape(f["geometry"]) for i, f in current.items()}
start = time.monotonic()
results = []
for row in provisional:
    cid = row["component"]
    prior = row["original_admin_observations"][0]
    target = prior["uniquely_covering_compatible_recorded_subject"]["id"]
    cf, tf, sf = originals[cid], current[target], sources[target]
    if tf["properties"]["parent_id"] != prior["uniquely_covering_compatible_recorded_subject"]["original_parent_id"]:
        raise ValueError("Target parent drift")
    cg, tg, sg = shape(cf["geometry"]), current_geoms[target], source_geoms[target]
    predicates = {"candidate_valid": cg.is_valid, "candidate_nonempty": not cg.is_empty,
                  "current_target_valid": tg.is_valid, "consumed_target_source_valid": sg.is_valid}
    exact_status = "valid"
    try: exact.prepare_geometry(cf["geometry"])
    except exact.DiagnosticError as exc: exact_status = exc.status + ":" + exc.reason
    predicates["exact_binary64_candidate_topology"] = exact_status
    residuals, source_hits, neighbor_hits = {}, [], []
    if cg.is_valid and not cg.is_empty and tg.is_valid and sg.is_valid:
        predicates["consumed_target_source_covers_candidate"] = sg.covers(cg)
        predicates["current_target_covers_candidate"] = tg.covers(cg)
        overlap = cg.intersection(tg)
        predicates["candidate_current_target_no_positive_area_overlap"] = overlap.area == 0
        proposal = tg.union(cg)
        gain, loss = proposal.difference(tg), tg.difference(proposal)
        residuals = {"source_uncovered_candidate": mapping(cg.difference(sg)),
                     "candidate_current_target_intersection": mapping(overlap),
                     "dissolved_gain": mapping(gain), "dissolved_loss": mapping(loss),
                     "candidate_dissolved_gain_symmetric_difference": mapping(cg.symmetric_difference(gain))}
        predicates["diagnostic_dissolved_zero_loss"] = loss.is_empty
        predicates["diagnostic_dissolved_full_gain"] = cg.symmetric_difference(gain).is_empty
        predicates["diagnostic_gain_positive_area"] = gain.area > 0
        for identity, g in source_geoms.items():
            if not cg.envelope.intersects(g.envelope): continue
            if not g.is_valid:
                source_hits.append({"id": identity, "status": "invalid-bbox-neighbor", "reason": explain_validity(g)})
                continue
            if not cg.intersects(g): continue
            hit = cg.intersection(g)
            source_hits.append({"id": identity, "whole_source_feature_sha256": sha(canon(sources[identity])),
                                "covers_candidate": g.covers(cg), "positive_area": hit.area > 0, "intersection": mapping(hit)})
        for identity, g in current_geoms.items():
            if not cg.envelope.intersects(g.envelope): continue
            if not g.is_valid:
                neighbor_hits.append({"id": identity, "status": "invalid-bbox-neighbor", "reason": explain_validity(g)})
                continue
            if not cg.intersects(g): continue
            hit = cg.intersection(g)
            neighbor_hits.append({"id": identity, "whole_current_feature_sha256": sha(canon(current[identity])),
                                  "positive_area": hit.area > 0, "intersection": mapping(hit)})
        predicates["unique_full_cover_consumed_source"] = [h["id"] for h in source_hits if h.get("covers_candidate")] == [target]
        predicates["no_positive_area_other_current_neighbor_in_two_parts"] = not any(h.get("positive_area") for h in neighbor_hits if h["id"] != target)
    decisive = [k for k in ["candidate_valid", "candidate_nonempty", "current_target_valid", "consumed_target_source_valid",
                 "consumed_target_source_covers_candidate", "candidate_current_target_no_positive_area_overlap",
                 "unique_full_cover_consumed_source", "no_positive_area_other_current_neighbor_in_two_parts"] if predicates.get(k) is False]
    if exact_status.startswith("invalid:"): decisive.append("exact_binary64_candidate_topology")
    status = "strict-premise-failed" if decisive else "bounded-premises-only-not-approved"
    results.append({"component": cid, "target_id": target, "status": status, "failed_predicates": decisive,
        "predicates": predicates, "residuals": residuals, "source_hits": source_hits, "current_neighbor_hits": neighbor_hits,
        "candidate_feature_sha256": sha(canon(cf)), "current_target_feature_sha256": sha(canon(tf)),
        "consumed_target_source_feature_sha256": sha(canon(sf)), "candidate_geometry": cf["geometry"],
        "retained_detector_area_m2": cf["properties"]["measured_fragment_area_sum_m2"]})
by_id = {r["component"]: r for r in results}
dispositions = [{"component": cid, "disposition": by_id[cid]["status"] if cid in by_id else "awaiting-original-mixed-source-evidence",
                 "resolved": False, "original_feature_sha256": sha(canon(originals[cid]))} for cid in expected]
result = {"issue": 1243, "family_id": plan["family_id"], "original_family_denominator": 10,
    "original_batch_id": plan["original_batch_id"], "original_batch_denominator": 130,
    "baseline_commit": plan["baseline_commit"], "execution_head": HEAD, "prospective_logical_bytes": charge,
    "runtime_lock_sha256": sha(controls["runtime-lock.json"]), "producer_sha256": sha(controls["probe.py"]),
    "input_plan_sha256": sha(controls["probe-inputs.json"]), "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    "elapsed_seconds": time.monotonic() - start, "all_ten_dispositions": dispositions, "results": results,
    "resolved": 0, "scientific_or_publication_approval": False, "limits": plan["limits"]}
if result["peak_rss_bytes"] > 1024**3: raise ValueError("Process reservation exceeded")
print(json.dumps(dest.publish({"strict-predicates.json": result})))
print(json.dumps({"peak_rss_bytes": result["peak_rss_bytes"], "results": [{"component": r["component"], "status": r["status"], "predicates": r["predicates"]} for r in results]}))

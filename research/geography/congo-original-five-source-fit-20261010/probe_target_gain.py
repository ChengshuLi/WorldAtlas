"""Bounded exact current-target rejection probe; never source-fit approval."""
import gzip, hashlib, io, json, os, pathlib, resource, subprocess, sys, time
ROOT = pathlib.Path(__file__).resolve().parents[3]
OWN = "research/geography/congo-original-five-source-fit-20261010"
HEAD = sys.argv[1]
VINTAGE = sys.argv[2]
GIT = '/usr/local/bin/git'
CAP = 256 * 1024 * 1024
OUTPUT_RESERVE = 4 * 1024 * 1024
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def git(*args):
    return subprocess.check_output([GIT, "-C", str(ROOT), *args], stderr=subprocess.PIPE)
def frozen(name):
    raw = (ROOT / name).read_bytes()
    if len(raw) > 1024 * 1024 or raw != git("show", HEAD + ":" + name):
        raise ValueError("Unfrozen or oversized execution control: " + name)
    return raw
if len(HEAD) != 40 or git("rev-parse", HEAD + "^{commit}").decode().strip() != HEAD:
    raise ValueError("Exact committed execution head required")
code = frozen(OWN + "/probe_target_gain.py")
plan_raw = frozen(OWN + "/probe-inputs.json")
runtime_raw = frozen(OWN + "/runtime-lock.json")
plan, runtime = json.loads(plan_raw), json.loads(runtime_raw)
if pathlib.Path(runtime["git_executable"]).resolve() != pathlib.Path(GIT).resolve():
    raise ValueError("Git executable drift")
charge = sum(f["bytes"] + f.get("uncompressed_bytes", 0) for f in plan["files"])
charge += runtime["logical_bytes"] + len(code) + len(plan_raw) + len(runtime_raw) + OUTPUT_RESERVE
if charge > CAP or any(f["bytes"] > 32 * 1024 * 1024 or f.get("uncompressed_bytes", 0) > 32 * 1024 * 1024 for f in plan["files"]):
    raise ValueError("Prospective full-union logical admission failed")
for f in runtime["files"]:
    path = pathlib.Path(f["path"])
    if path.stat().st_size != f["bytes"] or sha(path.read_bytes()) != f["sha256"]:
        raise ValueError("Runtime drift: " + f["path"])
if not os.environ.get("PYTHONDONTWRITEBYTECODE") or not os.environ.get("PYTHONPYCACHEPREFIX"):
    raise ValueError("Fresh bytecode-cache prefix and no bytecode writes required")
# Preserve the repository's immutable reader and exclusive new-vintage writer.
helper_path = "scripts/evidence/immutable.py"
helper_pin = next(f for f in plan["files"] if f["path"] == helper_path)
helper_raw = git("show", plan["baseline_commit"] + ":" + helper_path)
if sha(helper_raw) != helper_pin["sha256"] or len(helper_raw) != helper_pin["bytes"]:
    raise ValueError("Immutable helper mismatch")
namespace = {"__name__": "bounded_immutable", "__file__": str(ROOT / helper_path)}
exec(compile(helper_raw, namespace["__file__"], "exec"), namespace)
class PinnedBaseline(namespace["Baseline"]):
    def _git(self, *args):
        return git(*args)
base = PinnedBaseline(ROOT, plan["baseline_commit"], plan["files"])
for runtime_file in runtime["files"]:
    base.admit("runtime:" + runtime_file["path"], runtime_file["bytes"])
for name, raw in [("producer", code), ("plan", plan_raw), ("runtime-lock", runtime_raw)]:
    base.admit("execution-control:" + name, len(raw))
base.admit("output-reservation", OUTPUT_RESERVE)
dest = namespace["NewVintage"](base, OWN + "/", VINTAGE, ["result.json"])
canon = namespace["canonical_json"]
from shapely.geometry import shape, mapping
import shapely, numpy
if (shapely.__version__, shapely.geos_version_string, numpy.__version__) != (runtime["shapely"], runtime["geos"], runtime["numpy"]):
    raise ValueError("Scientific runtime version drift")
exact = base.load_modules({"exact_predicates": "scripts/evidence/exact_predicates.py"})["exact_predicates"]
def read(pin):
    raw = base.pinned_bytes(pin["path"])
    if "uncompressed_bytes" in pin:
        base.admit("decoded:" + pin["path"], pin["uncompressed_bytes"])
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            raw = stream.read(pin["uncompressed_bytes"] + 1)
        if len(raw) != pin["uncompressed_bytes"] or sha(raw) != pin["uncompressed_sha256"]:
            raise ValueError("Complete decoded original mismatch")
    return json.loads(raw)
start = time.monotonic()
wanted = {s["id"] for s in plan["subjects"]}
originals = {}
for pin in plan["files"]:
    if "/custody-v1/payloads/" in pin["path"]:
        features = read(pin)["features"]
        for feature in features:
            if feature["id"] in wanted:
                if feature["id"] in originals: raise ValueError("Duplicate original candidate")
                originals[feature["id"]] = feature
if set(originals) != wanted: raise ValueError("Incomplete original five-ID roster")
target_data = read(next(p for p in plan["files"] if p["path"] == "data/geography/part-5.json"))
features = target_data["features"] if isinstance(target_data, dict) else target_data
results = []
for subject in plan["subjects"]:
    cf = originals[subject["id"]]
    if sha(canon(cf)) != subject["feature_sha256"] or sha(canon(cf["geometry"])) != subject["geometry_sha256"]:
        raise ValueError("Original candidate drift")
    matches = [f for f in features if f["id"] == subject["target"]["id"]]
    if len(matches) != 1: raise ValueError("Missing/duplicate current target")
    tf = matches[0]
    if sha(canon(tf)) != subject["target"]["original_feature_sha256"] or tf["properties"]["parent_id"] != subject["target"]["original_parent_id"]:
        raise ValueError("Current target full-feature/parent drift")
    cg, tg = shape(cf["geometry"]), shape(tf["geometry"])
    predicates = {"candidate_valid": cg.is_valid, "target_valid": tg.is_valid}
    try:
        exact.prepare_geometry(cf["geometry"])
        predicates["exact_binary64_candidate_valid"] = True
    except Exception as exc:
        predicates["exact_binary64_candidate_valid"] = False
        predicates["exact_binary64_candidate_failure"] = str(exc)
    residuals = {}
    if cg.is_valid and tg.is_valid and not cg.is_empty and not tg.is_empty:
        proposal = tg.union(cg)
        gain, loss = proposal.difference(tg), tg.difference(proposal)
        mismatch, already = cg.symmetric_difference(gain), cg.intersection(tg)
        predicates.update({"target_covers_candidate": tg.covers(cg), "candidate_target_positive_area_overlap": already.area > 0,
            "zero_target_loss": loss.is_empty, "full_candidate_gain": mismatch.is_empty,
            "gain_nonempty": not gain.is_empty, "gain_positive_area": gain.area > 0})
        residuals = {"gain": mapping(gain), "loss": mapping(loss), "candidate_gain_symmetric_difference": mapping(mismatch), "candidate_target_intersection": mapping(already)}
    results.append({"component": subject["id"], "target_id": tf["id"], "current_target_feature_sha256": sha(canon(tf)),
        "current_parent_id": tf["properties"]["parent_id"], "original_geometry_sha256": sha(canon(cf["geometry"])),
        "predicates": predicates, "residuals": residuals,
        "retained_detector_area_m2": cf["properties"]["measured_fragment_area_sum_m2"],
        "status": "strict-target-premise-failed" if not predicates.get("zero_target_loss") or not predicates.get("full_candidate_gain") or not predicates.get("exact_binary64_candidate_valid") or predicates.get("candidate_target_positive_area_overlap") else "target-premises-only-not-approved"})
result = {"issue": 1694, "original_batch": plan["original_batch"], "execution_head": HEAD,
    "baseline_commit": plan["baseline_commit"], "input_plan_sha256": sha(plan_raw), "runtime_lock_sha256": sha(runtime_raw),
    "producer_sha256": sha(code), "prospective_logical_bytes": charge, "logical_cap_bytes": CAP,
    "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, "elapsed_seconds": time.monotonic() - start,
    "results": results, "resolved": 0, "scientific_or_publication_approval": False,
    "limits": plan["limits"] + ["No full affected-neighbor scan, source physical qualification, native operation or selected-map change was performed."]}
if result["peak_rss_bytes"] > 1024**3: raise ValueError("Process peak reservation exceeded")
print(json.dumps(dest.publish({"result.json": result})))
print(json.dumps({"peak_rss_bytes": result["peak_rss_bytes"], "elapsed_seconds": result["elapsed_seconds"], "results": [{"component": r["component"], "status": r["status"], "predicates": r["predicates"]} for r in results]}))

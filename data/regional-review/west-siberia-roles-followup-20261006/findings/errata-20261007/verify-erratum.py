#!/usr/bin/env python3
"""Run real controls and two complete fresh erratum generations exactly once."""
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OWNED = ROOT / "data/regional-review/west-siberia-roles-followup-20261006"
ERRATUM = OWNED / "findings/errata-20261007"
GENERATOR = ERRATUM / "reproduce-erratum.py"
ASSESSMENT = OWNED / "findings/followup-assessments.json"
CONTRACT = OWNED / "baseline/issue-contract.json"
ORIGINALS = {
    "assessment": (OWNED / "findings/followup-assessments.json", "7fa0d983d07534ffe068cdf056a102eb033d1c268466c4a1605d405b2c0630b0"),
    "issue_contract": (OWNED / "baseline/issue-contract.json", "13a9d0c8bbf6fbc80f98a8842c82f315211d9183e066a246e319a90dc46f9acf"),
    "positive_control": (OWNED / "findings/positive-control.json", "a0ab32cee3adc7c1dbd81fa7acec0bb4076a3e8a556a4aa06410593f8bc79dd8"),
    "negative_control": (OWNED / "findings/negative-control.json", "cc31d1ed56eb47310413b8f870aba8c07d5e037b86a740ec9300c7c5a17ef913"),
    "reproduction_result": (OWNED / "findings/reproduction-result.json", "82a3375b9b9d20ec4ae1a2dfae1d6d230f48acaa7c2daa8831e14ba7cd08f85c"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def path_components_have_no_symlinks(path):
    path = Path(os.path.abspath(path))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            return False
    return True


def verify_originals():
    result = {}
    for label, (path, expected) in ORIGINALS.items():
        observed = sha(path.read_bytes())
        if observed != expected:
            raise RuntimeError("original evidence changed: %s (%s)" % (label, observed))
        result[label] = {"path": str(path.relative_to(OWNED)), "sha256": observed}
    return result


def call_generator(*args):
    return subprocess.run([sys.executable, str(GENERATOR), *map(str, args)],
                          cwd=ROOT, text=True, capture_output=True, check=False)


def record_attempt(proc, expected_fragment):
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "expected_error_observed": proc.returncode != 0 and expected_fragment in proc.stderr,
    }


def run_controls(tempdir, original_before):
    controls = ERRATUM / "control-fixtures"
    if controls.exists() or controls.is_symlink():
        raise RuntimeError("control fixture path already exists; inspect and do not overwrite")
    controls.mkdir(mode=0o700)
    observations = {}
    try:
        original = json.loads(ASSESSMENT.read_bytes())
        roster = [row["subject_id"] for row in original["assessments"]]
        positive = Path(tempdir) / "roster-positive.json"
        positive.write_bytes(canonical(roster))
        proc = call_generator("--roster-probe", positive)
        observations["positive_exact_roster"] = record_attempt(proc, "")
        if proc.returncode != 0:
            raise RuntimeError("positive exact-roster control failed")

        missing = Path(tempdir) / "roster-missing.json"
        missing.write_bytes(canonical(roster[:-1]))
        proc = call_generator("--roster-probe", missing)
        observations["negative_missing_subject"] = record_attempt(proc, "exactly 45")
        if not observations["negative_missing_subject"]["expected_error_observed"]:
            raise RuntimeError("missing-subject negative control did not reject")

        duplicate = Path(tempdir) / "roster-duplicate.json"
        duplicate.write_bytes(canonical(sorted(roster + [roster[0]])))
        proc = call_generator("--roster-probe", duplicate)
        observations["negative_duplicate_subject"] = record_attempt(proc, "exactly 45")
        if not observations["negative_duplicate_subject"]["expected_error_observed"]:
            raise RuntimeError("duplicate-subject negative control did not reject")

        tampered = Path(tempdir) / "assessment-tampered.json"
        tampered.write_bytes(ASSESSMENT.read_bytes() + b" ")
        target = ERRATUM / "run-one"
        proc = call_generator("--assessment", tampered, "--output-dir", target, "--run-id", "run-one")
        observations["input_tamper"] = record_attempt(proc, "pinned original assessment input hash mismatch")
        observations["input_tamper"].update({"tampered_input_sha256": sha(tampered.read_bytes()), "output_untouched": not target.exists()})
        if not observations["input_tamper"]["expected_error_observed"] or not observations["input_tamper"]["output_untouched"]:
            raise RuntimeError("input-tamper control failed or wrote output")

        target.mkdir()
        sentinel = target / "preserve-me.txt"
        sentinel.write_text("occupied destination sentinel\n")
        before = sha(sentinel.read_bytes())
        proc = call_generator("--output-dir", target, "--run-id", "run-one")
        observations["occupied_output"] = record_attempt(proc, "occupied output destination refused")
        observations["occupied_output"].update({"sentinel_sha256_before": before, "sentinel_sha256_after": sha(sentinel.read_bytes())})
        if not observations["occupied_output"]["expected_error_observed"] or before != observations["occupied_output"]["sentinel_sha256_after"]:
            raise RuntimeError("occupied-destination control failed")
        sentinel.unlink()
        target.rmdir()

        target.symlink_to(ERRATUM / "run-two", target_is_directory=True)
        proc = call_generator("--output-dir", target, "--run-id", "run-one")
        observations["symlink_output"] = record_attempt(proc, "symlinked output path refused")
        observations["symlink_output"].update({"symlink_preserved": target.is_symlink(), "target_untouched": not (ERRATUM / "run-two").exists()})
        if not observations["symlink_output"]["expected_error_observed"] or not observations["symlink_output"]["symlink_preserved"]:
            raise RuntimeError("symlink-destination control failed")
        target.unlink()

        proc = call_generator("--output-dir", OWNED / "findings", "--run-id", "run-one")
        observations["original_destination"] = record_attempt(proc, "output must be a direct dated erratum run directory")
        observations["original_destination"]["originals_unchanged"] = verify_originals() == original_before
        if not observations["original_destination"]["expected_error_observed"] or not observations["original_destination"]["originals_unchanged"]:
            raise RuntimeError("original-destination control failed")

        escaped = Path(tempdir) / "escaped-output"
        proc = call_generator("--output-dir", escaped, "--run-id", "run-one")
        observations["escaped_destination"] = record_attempt(proc, "output must be a direct dated erratum run directory")
        observations["escaped_destination"]["escaped_path_untouched"] = not escaped.exists()
        if not observations["escaped_destination"]["expected_error_observed"] or not observations["escaped_destination"]["escaped_path_untouched"]:
            raise RuntimeError("escaped-destination control failed")
    finally:
        if controls.exists() and not controls.is_symlink():
            shutil.rmtree(controls)
    if verify_originals() != original_before:
        raise RuntimeError("original evidence changed during controls")
    return observations


def product_hashes(run_dir):
    rows = []
    for name in ("assessment.json", "issue-contract.json", "positive-control.json", "negative-control.json"):
        raw = (run_dir / name).read_bytes()
        rows.append({"name": name, "bytes": len(raw), "sha256": sha(raw)})
    return rows


def main():
    if Path(__file__).resolve().parent.name != "errata-20261007":
        raise RuntimeError("expected dated 2026-10-07 erratum directory")
    if not path_components_have_no_symlinks(ERRATUM):
        raise RuntimeError("symlinked erratum path refused")
    original_before = verify_originals()
    reserved = [ERRATUM / name for name in ("run-one", "run-two", "control-results.json", "reproduction-result.json", "control-fixtures")]
    if any(path.exists() or path.is_symlink() for path in reserved):
        raise RuntimeError("dated output vintage is occupied; inspect it and do not overwrite")

    with tempfile.TemporaryDirectory(prefix="worldatlas-1092-erratum-") as tempdir:
        controls = run_controls(tempdir, original_before)

    generator_hash = sha(GENERATOR.read_bytes())
    verifier_hash = sha(Path(__file__).read_bytes())
    start = datetime.now(timezone.utc).isoformat()
    runs = []
    for run_id in ("run-one", "run-two"):
        destination = ERRATUM / run_id
        proc = call_generator("--output-dir", destination, "--run-id", run_id)
        if proc.returncode != 0:
            raise RuntimeError("%s failed: %s %s" % (run_id, proc.stdout, proc.stderr))
        manifest_raw = (destination / "run-manifest.json").read_bytes()
        manifest = json.loads(manifest_raw)
        if manifest["execution"][0]["sha256"] != generator_hash or manifest["execution"][1]["sha256"] != verifier_hash:
            raise RuntimeError("run execution code hash mismatch")
        products = product_hashes(destination)
        manifest_products = [
            {"name": Path(item["path"]).name, "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in manifest["products"]
        ]
        if products != manifest_products:
            raise RuntimeError("run product hashes do not match its execution manifest")
        runs.append({
            "run_id": run_id,
            "process_id": manifest["process_id"],
            "started_at_utc": manifest["started_at_utc"],
            "run_manifest_sha256": sha(manifest_raw),
            "products": products,
            "content_sha256": sha(canonical(products)),
            "generator_stdout": proc.stdout.strip(),
        })
    if runs[0]["process_id"] == runs[1]["process_id"] or runs[0]["content_sha256"] != runs[1]["content_sha256"]:
        raise RuntimeError("two independent output-vintage runs did not match")
    original_after = verify_originals()
    if original_before != original_after:
        raise RuntimeError("original files changed during fresh reproduction")

    control_doc = {
        "version": 1,
        "evaluation_commit": "15025282de755d631024211687f036751fba963d",
        "generator_sha256": generator_hash,
        "verifier_sha256": verifier_hash,
        "controls": controls,
    }
    result_doc = {
        "version": 1,
        "method_id": "west-siberia-20261007-erratum",
        "kind": "reproducibility",
        "outcome": "passed",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_commit": "15025282de755d631024211687f036751fba963d",
        "runtime": {"python": sys.version, "implementation": __import__("platform").python_implementation(), "platform": __import__("platform").platform()},
        "execution": {"generator_sha256": generator_hash, "verifier_sha256": verifier_hash},
        "originals_before": original_before,
        "originals_after": original_after,
        "runs": runs,
        "independent_equal_product_hashes": runs[0]["products"] == runs[1]["products"],
        "control_results_path": str((ERRATUM / "control-results.json").relative_to(OWNED)),
        "limits": ["Source and role evidence only; no geometry, Atlas tier, current boundary, or publication certification."],
    }
    for name, document in (("control-results.json", control_doc), ("reproduction-result.json", result_doc)):
        with (ERRATUM / name).open("xb") as stream:
            stream.write(canonical(document))
            stream.flush()
            os.fsync(stream.fileno())
    print(json.dumps({"status": "passed", "runs": [r["content_sha256"] for r in runs], "originals_unchanged": original_before == original_after}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

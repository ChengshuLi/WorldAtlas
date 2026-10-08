"""Bounded controls for the admission entrypoint and pinned output guard."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import types

HERE = Path(__file__).resolve().parent
import admission


def desc(identity: str, size: int, digest: str = "a" * 64, category: str = "input") -> dict:
    return {"identity": identity, "category": category, "bytes": size,
            "sha256": digest, "authenticated": True}


def check(condition: bool, label: str) -> dict:
    if not condition:
        raise AssertionError(label)
    return {"control": label, "passed": True}


def output_preservation_control() -> dict:
    # Execute the exact retained immutable helper bytes in a disposable repo.
    helper_commit = "950eb2188e5b66d88ea47a679936a02fe3eb1c40"
    helper_bytes = subprocess.check_output([
        "git", "show", f"{helper_commit}:scripts/evidence/immutable.py"
    ])
    helper = types.ModuleType("pinned_immutable")
    exec(compile(helper_bytes, "pinned:scripts/evidence/immutable.py", "exec"), helper.__dict__)
    with tempfile.TemporaryDirectory(prefix="wa-admission-control-") as temp:
        repo = Path(temp)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "Control"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "control@example.invalid"], check=True)
        (repo / "baseline.json").write_bytes(b'{"pinned":true}\n')
        subprocess.run(["git", "-C", str(repo), "add", "baseline.json"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
        commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        raw = (repo / "baseline.json").read_bytes()
        baseline = helper.Baseline(repo, commit, [helper.descriptor("baseline.json", raw)])
        root = repo / "research/geography/admission-control/vintages/collision"
        root.mkdir(parents=True)
        sentinel = root / "sentinel.txt"
        sentinel.write_bytes(b"keep these exact bytes\n")
        before = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        try:
            helper.NewVintage(baseline, "research/geography/admission-control/", "collision", ["result.json"])
        except FileExistsError:
            pass
        else:
            raise AssertionError("existing vintage collision was accepted")
        after = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        if before != after or sentinel.read_bytes() != b"keep these exact bytes\n":
            raise AssertionError("existing collision sentinel changed")
        return {
            "control": "pinned-NewVintage-existing-vintage-collision",
            "passed": True,
            "helper_commit": helper_commit,
            "helper_sha256": hashlib.sha256(helper_bytes).hexdigest(),
            "sentinel_sha256_before_after": before,
            "sentinel_preserved": True,
        }


def run() -> dict:
    limit = admission.MAX_FILE_BYTES
    phase = admission.MAX_PHASE_BYTES
    rows: list[dict] = []

    for size, expected in ((limit - 1, "admitted"), (limit, "admitted"), (limit + 1, "refused")):
        plan = admission.evaluate_phase(raw_inputs=[desc(f"body-{size}", size)], decoded_inputs=[], output_reservations=[])
        rows.append(check(plan["status"] == expected, f"whole-body-{expected}-at-{size}"))

    # A tiny encoded fixture whose complete decoded body exceeds the whole-body cap.
    encoded = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=encoded, mtime=0) as stream:
        stream.write(b"x" * (limit + 1))
    compressed = encoded.getvalue()
    try:
        admission.decode_gzip_bounded(compressed, limit)
    except admission.DecodedBodyTooLarge as error:
        rows.append(check(error.observed_bytes == limit + 1, "compressed-small-decoded-large-stops-at-limit-plus-one"))
    else:
        raise AssertionError("oversized decoded fixture was accepted")
    rows.append(check(len(compressed) < limit and admission.gzip_footer_isize(compressed) == (limit + 1) % (2**32),
                      "compressed-small-decoded-large-fixture-properties"))
    try:
        admission.decode_gzip_bounded(b"x" * (limit + 1), limit)
    except admission.AdmissionError:
        rows.append(check(True, "encoded-body-over-file-limit-rejected-before-decode"))
    else:
        raise AssertionError("oversized encoded fixture was accepted")

    # Separate category/source and geography identities both contribute to one cap.
    plan = admission.evaluate_phase(
        raw_inputs=[desc(f"source:bundle:{i}", limit, category="source") for i in range(4)] +
                   [desc(f"geography:bundle:{i}", limit, category="geography") for i in range(4)],
        decoded_inputs=[], output_reservations=[], receipt_bytes=1)
    rows.append(check(plan["status"] == "refused" and plan["input_bytes"] == phase and
                      any(r["code"] == "complete-phase-exceeds-limit" for r in plan["reasons"]),
                      "source-plus-geography-single-phase-cap"))

    same = desc("logical:item", 20, "b" * 64)
    duplicate = admission.evaluate_phase(raw_inputs=[same], decoded_inputs=[dict(same)], output_reservations=[], receipt_bytes=0)
    rows.append(check(duplicate["input_count"] == 1 and duplicate["input_bytes"] == 20, "same-logical-identity-counted-once"))
    distinct = admission.evaluate_phase(raw_inputs=[desc("logical:a", 20, "b" * 64), desc("logical:b", 20, "b" * 64)],
                                        decoded_inputs=[], output_reservations=[], receipt_bytes=0)
    rows.append(check(distinct["input_count"] == 2 and distinct["input_bytes"] == 40, "distinct-identities-count-same-bytes-separately"))

    output_over = admission.evaluate_phase(raw_inputs=[desc("input", phase - 10)], decoded_inputs=[],
                                           output_reservations=[{"name": "report.json", "max_bytes": 11}], receipt_bytes=0)
    rows.append(check(output_over["status"] == "refused" and
                      any(r["code"] == "complete-phase-exceeds-limit" for r in output_over["reasons"]),
                      "outputs-included-in-complete-phase"))

    missing = admission.evaluate_phase(raw_inputs=[desc("present", 1)], decoded_inputs=[], output_reservations=[],
                                       expected_input_identities=["present", "missing"], receipt_bytes=0)
    rows.append(check(missing["status"] == "refused" and
                      any(r["code"] == "missing-input-descriptors" for r in missing["reasons"]),
                      "missing-complete-input-descriptor-refused"))
    products: list[str] = []
    try:
        admission.run_if_admitted(missing, lambda: products.append("must-not-exist"))
    except admission.AdmissionError:
        pass
    else:
        raise AssertionError("refused plan invoked its producer")
    rows.append(check(products == [], "refusal-stops-producer-before-product-creation"))

    runtime = admission.evaluate_phase(raw_inputs=[desc("input", 1)], decoded_inputs=[], output_reservations=[],
                                       runtime_complete=False, receipt_bytes=0)
    rows.append(check(runtime["status"] == "refused" and
                      any(r["code"] == "runtime-closure-incomplete" for r in runtime["reasons"]),
                      "unclosed-runtime-refused"))

    try:
        admission.evaluate_phase(raw_inputs=[desc("same", 1), desc("same", 2)], decoded_inputs=[], output_reservations=[])
    except admission.AdmissionError:
        rows.append(check(True, "conflicting-logical-input-descriptors-rejected"))
    else:
        raise AssertionError("conflicting logical identity descriptors were accepted")

    rows.append(output_preservation_control())
    return {"version": 1, "status": "passed", "controls": rows,
            "limits": {"file_bytes": limit, "phase_bytes": phase,
                       "receipt_bytes": admission.MAX_RECEIPT_BYTES},
            "scope": "bounded synthetic admission fixtures only; no source decode or geography reproduction"}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))

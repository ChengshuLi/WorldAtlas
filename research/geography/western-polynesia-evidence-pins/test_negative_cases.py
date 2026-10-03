#!/usr/bin/env python3
"""Prove changed baseline bytes, paths, and issue/release pins are rejected."""
import copy, json, re
from pathlib import Path
from source_pins import (OUT, EXPECTED_BASELINE_COMMIT, PARENT_EVIDENCE_COMMIT,
    PARENT_PACKET, PinError, git_blob, load_json, verify_packet, write_packet)

packet = json.loads((OUT/"baseline-source-crosswalk.json").read_text(encoding="utf-8"))
results = []

def expect_rejected(label, operation, expected_text):
    try:
        operation()
    except PinError as exc:
        if expected_text not in str(exc):
            raise AssertionError(f"{label}: rejected for unexpected reason: {exc}") from exc
        results.append({"case": label, "result": "REJECTED_AS_EXPECTED", "reason": str(exc)})
    else:
        raise AssertionError(f"{label}: invalid input returned PASS")

def changed_bytes_reader(commit, path):
    raw = git_blob(commit, path)
    if commit == EXPECTED_BASELINE_COMMIT and path == "data/geography/part-23.json":
        return raw + b" "
    return raw

# Existing packet validation rejects changed source bytes.
expect_rejected("changed_baseline_input_bytes",
    lambda: verify_packet(packet, read_blob=changed_bytes_reader), "input bytes do not match immutable Git blob")
# The builder also refuses changed source bytes before creating its output file.
no_output = OUT/"negative-test-must-not-exist.json"
try:
    expect_rejected("builder_rejects_changed_bytes_before_write",
        lambda: write_packet(no_output, read_blob=changed_bytes_reader), "input bytes do not match immutable Git blob")
    if no_output.exists() or no_output.with_suffix(no_output.suffix+".tmp").exists():
        raise AssertionError("builder wrote an output before rejecting changed bytes")
finally:
    no_output.unlink(missing_ok=True)
    no_output.with_suffix(no_output.suffix+".tmp").unlink(missing_ok=True)

# Redirect a real subject to a valid but non-containing file in the world index.
wrong_paths = copy.deepcopy(packet["location_source_crosswalk"])
wrong_paths[0]["containing_path"] = "data/geography/part-0.json"
expect_rejected("incorrect_containing_path",
    lambda: verify_packet(packet, crosswalk_override=wrong_paths), "feature identity/content check")

# Mutate the exact preserved #134 machine-scope release ID; certificate
# comparison must fail before the new output file is written.
issue_path = f"{PARENT_PACKET}/issue-metadata.json"
issue_doc = load_json(git_blob(PARENT_EVIDENCE_COMMIT, issue_path), issue_path)
pattern = re.compile(r"(```json\s*)(\{.*?\})(\s*```)", re.S)
match = pattern.search(issue_doc["body"])
if not match:
    raise AssertionError("could not locate #134 scoped issue pin block")
spec = json.loads(match.group(2))
spec["release"]["id"] = "geography:review:deliberately-mismatched"
issue_doc["body"] = issue_doc["body"][:match.start()] + match.group(1) + json.dumps(spec) + match.group(3) + issue_doc["body"][match.end():]
expect_rejected("mismatched_issue_release_pin",
    lambda: verify_packet(packet, issue_override=issue_doc), "release pins mismatch certificate")
no_output = OUT/"negative-test-pin-mismatch-must-not-exist.json"
try:
    expect_rejected("builder_rejects_release_mismatch_before_write",
        lambda: write_packet(no_output, issue_override=issue_doc), "release pins mismatch certificate")
    if no_output.exists() or no_output.with_suffix(no_output.suffix+".tmp").exists():
        raise AssertionError("builder wrote an output before rejecting release mismatch")
finally:
    no_output.unlink(missing_ok=True)
    no_output.with_suffix(no_output.suffix+".tmp").unlink(missing_ok=True)

print(json.dumps({"negative_cases": results, "all_invalid_inputs_rejected": len(results) == 5}, indent=2))

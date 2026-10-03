#!/usr/bin/env python3
"""Verify the superseding #134 baseline path/release evidence packet."""
import json
from pathlib import Path
from source_pins import OUT, PinError, verify_packet

packet = json.loads((OUT/"baseline-source-crosswalk.json").read_text(encoding="utf-8"))
verify_packet(packet)
print(json.dumps({"baseline_commit": packet["baseline_commit"]["sha"],
    "scope_locations": len(packet["location_source_crosswalk"]),
    "actual_containing_files": [x["path"] for x in packet["containing_files"]],
    "issue_release_pins_match": packet["checks"]["hierarchy_release_certificate_publication_gate_region_envelope_and_membership_pins_match"],
    "result": "PASS"}, indent=2))

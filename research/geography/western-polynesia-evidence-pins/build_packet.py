#!/usr/bin/env python3
"""Validate all frozen inputs before writing the new explicit crosswalk output."""
import json
from source_pins import PinError, write_packet

try:
    packet = write_packet()
except PinError as exc:
    raise SystemExit(f"REFUSED: {exc}") from exc
print(json.dumps({"output": "baseline-source-crosswalk.json",
    "scope_locations": len(packet["location_source_crosswalk"]),
    "baseline_commit": packet["baseline_commit"]["sha"],
    "containing_files": [x["path"] for x in packet["containing_files"]],
    "result": "PASS"}, indent=2))

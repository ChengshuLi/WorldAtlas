#!/usr/bin/env python3
"""Inject an interrupted exclusive write and prove no completion is published."""
from pathlib import Path
import json
import os
from unittest.mock import patch

from reproduce import OUTPUTS, ROOT, OWNED, canonical, sha
from reproduce import write_complete


def main():
    path = ROOT / OWNED / "controls" / "partial-interruption"
    if os.path.lexists(path):
        raise FileExistsError("control fixture is retained; do not overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    original_open = Path.open
    opens = 0

    def interrupted(self, mode="r", *args, **kwargs):
        nonlocal opens
        if Path(self).parent == path and mode == "xb":
            opens += 1
            if opens == 2:
                raise OSError("injected interruption after first exclusive product write")
        return original_open(self, mode, *args, **kwargs)

    payloads = {name: ("sentinel-" + name).encode() for name in OUTPUTS}
    error = None
    try:
        with patch.object(Path, "open", interrupted):
            write_complete(path, payloads, {"control": "interruption"})
    except OSError as exc:
        error = str(exc)
    files = sorted(p.name for p in path.iterdir())
    passed = (opens == 2 and files == [OUTPUTS[0]] and not (path / "publication.json").exists() and
              (path / OUTPUTS[0]).read_bytes() == payloads[OUTPUTS[0]])
    report = {"version": 1, "kind": "interrupted-exclusive-write-control", "passed": passed,
              "injected_error": error, "files_after_interruption": files,
              "first_product_sha256": sha((path / OUTPUTS[0]).read_bytes()),
              "completion_receipt_absent": not (path / "publication.json").exists(),
              "outcome": "partial products remain explicitly unaccepted; no success receipt exists"}
    target = ROOT / OWNED / "interrupted-write-control.json"
    with target.open("xb") as stream:
        stream.write(canonical(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

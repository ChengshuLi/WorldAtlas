"""Adversarially exercise the same shared new-vintage writer used by both CLIs."""
import json
import os
from pathlib import Path
import shutil

from authenticated import OWNED, ROOT, load_trusted_helper
from authenticated import CapturedBaseline, output_writer

PACKET = ROOT / OWNED


def run():
    manifest = json.loads((PACKET / "evidence-quality.json").read_bytes())
    helper = load_trusted_helper(manifest)
    base = CapturedBaseline(helper, manifest)
    results = []
    vintages = PACKET / "vintages"
    vintages.mkdir(exist_ok=True)

    sentinel_root = vintages / "writer-sentinel"
    sentinel_root.mkdir()
    sentinel = sentinel_root / "result.json"
    sentinel.write_bytes(b"preserve-me\n")
    rejected = False
    try:
        output_writer(base, "writer-sentinel", ["result.json"])
    except FileExistsError:
        rejected = True
    if not rejected or sentinel.read_bytes() != b"preserve-me\n":
        raise ValueError("Preexisting ordinary sentinel was not safely rejected")
    results.append({"case": "preexisting ordinary sentinel", "outcome": "passed", "sentinel_sha256": helper.sha256(sentinel.read_bytes())})
    shutil.rmtree(sentinel_root)

    broken = vintages / "writer-broken-link"
    broken.symlink_to(PACKET / "missing-link-target")
    rejected = False
    try:
        output_writer(base, "writer-broken-link", ["result.json"])
    except ValueError:
        rejected = True
    if not rejected:
        raise ValueError("Broken output symlink was not rejected")
    broken.unlink()
    results.append({"case": "broken symlink in output path", "outcome": "passed"})

    # Check an ancestor symlink while preserving the complete existing vintages
    # directory in the same owned packet. Restore it in a finally block.
    saved = PACKET / ".writer-controls-vintages-saved"
    target = PACKET / ".writer-controls-ancestor-target"
    if saved.exists() or saved.is_symlink() or target.exists() or target.is_symlink():
        raise FileExistsError("Writer control scratch path already exists")
    os.replace(vintages, saved)
    target.mkdir()
    vintages.symlink_to(target, target_is_directory=True)
    try:
        rejected = False
        try:
            output_writer(base, "writer-ancestor-link", ["result.json"])
        except ValueError:
            rejected = True
        if not rejected:
            raise ValueError("Ancestor symlink in output path was not rejected")
    finally:
        vintages.unlink()
        target.rmdir()
        os.replace(saved, vintages)
    results.append({"case": "ancestor symlink in output path", "outcome": "passed"})

    escaped = False
    try:
        helper.NewVintage(type("WriterBaseline", (), {"repo":base.repo,"commit":base.commit,"pins":base.pins,
            "consumed":base.consumed,"max_phase_bytes":base.max_phase_bytes,
            "pinned_bytes":staticmethod(base.pinned_bytes)})(), "research/geography/../escaped/", "escape", ["result.json"])
    except ValueError:
        escaped = True
    if not escaped:
        raise ValueError("Escaped destination path was not rejected")
    results.append({"case": "traversal/escaped destination", "outcome": "passed"})

    partial = output_writer(base, "writer-partial-failure-ancestor-final", ["first.json", "second.json"])
    path_open = Path.open
    def fail_second(self, *args, **kwargs):
        if self.name == "second.json" and self.parent.name == "writer-partial-failure-ancestor-final":
            raise OSError("controlled partial-output failure")
        return path_open(self, *args, **kwargs)
    Path.open = fail_second
    failed = False
    try:
        partial.publish({"first.json": {"written": True}, "second.json": {"written": True}})
    except OSError:
        failed = True
    finally:
        Path.open = path_open
    if not failed or not (partial.root / "first.json").exists() or (partial.root / "publication.json").exists():
        raise ValueError("Partial write did not leave an unpublished incomplete vintage")
    shutil.rmtree(partial.root)
    results.append({"case": "failure during multi-file write", "outcome": "passed",
        "first_file_was_partial": True, "complete_receipt_absent": True, "scratch_removed_after_observation": True})

    return {"method_id": "exclusive-output-publication", "kind": "negative-control", "outcome": "passed",
        "entrypoints": ["compare.py", "shared_edge.py"], "writer": "captured shared immutable.NewVintage",
        "cases": results, "limit": "Failure fixture confirms no final receipt appears until every output has been flushed. The incomplete private test vintage was removed after its no-receipt state was recorded."}


if __name__ == "__main__":
    result = run()
    manifest = json.loads((PACKET / "evidence-quality.json").read_bytes())
    helper = load_trusted_helper(manifest)
    base = CapturedBaseline(helper, manifest)
    records = output_writer(base, "writer-safety-controls-verified", ["result.json"]).publish({"result.json": result})
    print(json.dumps({"records": records, "result": result}, ensure_ascii=False, indent=2))

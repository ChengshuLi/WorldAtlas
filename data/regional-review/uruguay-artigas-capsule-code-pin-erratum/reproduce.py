#!/usr/bin/env python3
"""Reproduce the retained Artigas representation report from pinned bytes.

The manifest is a descriptive inventory, never the trust root for executed code.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sys

HERE = Path(__file__).resolve().parent
ISSUE_BODY_SHA256 = "043bc67f66df53f60f2ac8b5d52b0a62fa71fb13556dd3bdf4f9e5d62cc91f71"
CAPSULE = "inputs/code/capsule-reproduce.py"
CAPSULE_SHA256 = "5b3787d9f07373751d2bbd5a94acec41eab79de43732cd4f6c45e2fd72c3d873"
ISSUE_CAPSULE_PIN = "data/regional-review/uruguay-artigas-contested-guard-erratum/inputs/code/capsule-reproduce.py"
MANIFEST = {
    "reproduce.py": "107c20e0cb35ad47d614d56d11bc97780178e769d885bfd66bf0a7f96eba3265",
    CAPSULE: CAPSULE_SHA256,
    "inputs/code/original-reproduce.py": "c6abb1d4b2ba662d2b7318db55d4fb9943945257a754ee8e42ff17d4ac0d79f8",
    "inputs/original-reproduction-results.json": "3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a",
    "inputs/original-source-inventory.json": "83c6a22703baedab022144d3284e4b6434043c91e04dccd1573c02473c576675",
    "inputs/baseline/data-administrative-sources.json": "ed0051d2956271c72f8917e7da0c6f53e5dfb595bee5920cac489a65a747d633",
    "inputs/baseline/data-geography-part-25.json": "dada55df1b7f0f2a2b307f4aea071d0e48791e3105875755fe74a292a6763394",
    "inputs/baseline/data-hierarchy.json": "568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b",
    "inputs/baseline/data-macro-publication-v5.json": "aae3967fde4f5bf92b3cb0b42c490c6c6a5921c7421dcdc9533f242afbd6a674",
    "inputs/baseline/data-world-index.json": "a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03",
    "inputs/sources/ury-gb-2017.geojson": "9f4887205e7b359af2ef1e4f484ad071d2dc0d12d068f1d7b6c1cc6c2624d1cf",
    "inputs/sources/ury-igm-current.geojson": "3cfa19c6be9d12bd159b236e15839f958656fdbe66ef19e38379cb54c141b3a7",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate():
    api = json.loads((HERE / "inputs/issue-1413-api.json").read_text())
    body = api.get("body", "").encode("utf-8")
    if sha(body) != ISSUE_BODY_SHA256:
        raise ValueError("issue contract snapshot differs from reviewed contract")
    contract = "<!-- worldatlas-work:v1\n"
    body_text = body.decode("utf-8")
    if contract not in body_text:
        raise ValueError("issue contract snapshot lacks issue 1413 work contract")
    start = body_text.index(contract) + len(contract)
    end = body_text.index("\n-->", start)
    spec = json.loads(body_text[start:end])
    if (api.get("number") != 1413 or spec.get("mode") != "geography" or
            spec.get("owned_paths") != ["data/regional-review/uruguay-artigas-capsule-code-pin-erratum/"] or
            spec.get("max_prs") != 1 or
            spec.get("evidence_quality", {}).get("pins", {}).get(ISSUE_CAPSULE_PIN) != CAPSULE_SHA256):
        raise ValueError("issue contract scope or immutable capsule pin differs")
    manifest = json.loads((HERE / "inputs/original-manifest.json").read_text())
    if manifest.get("capsule") != MANIFEST:
        raise ValueError("required executable and input pin inventory differs")
    if set(MANIFEST) != set(manifest["capsule"]):
        raise ValueError("required executable pin inventory is incomplete")
    captured = {}
    for rel, expected in MANIFEST.items():
        path = HERE / ("inputs/code/original-wrapper.py" if rel == "reproduce.py" else rel)
        if path.is_symlink() or not path.is_file():
            raise ValueError("immutable whole-file pin mismatch: " + rel)
        raw = path.read_bytes()
        if sha(raw) != expected:
            raise ValueError("immutable whole-file pin mismatch: " + rel)
        captured[rel] = raw
    if sha(captured[CAPSULE]) != CAPSULE_SHA256:
        raise ValueError("executed capsule identity mismatch")
    return captured


def execute_captured_capsule(captured, out):
    """Execute reviewed code and serve its pinned inputs from captured bytes."""
    script = HERE / CAPSULE
    pinned_paths = {str((HERE / rel).absolute()): raw for rel, raw in captured.items()
                    if rel != "reproduce.py"}
    read_bytes = Path.read_bytes
    write_bytes = Path.write_bytes
    output_path = str((out / "reproduction-results.json").absolute())
    outputs = {}

    def pinned_read_bytes(path):
        value = pinned_paths.get(str(path.absolute()))
        return value if value is not None else read_bytes(path)

    def capture_output_bytes(path, raw):
        if str(path.absolute()) != output_path or "reproduction-results.json" in outputs:
            raise ValueError("capsule attempted an unplanned or duplicate output")
        if not isinstance(raw, bytes):
            raise ValueError("capsule output must be exact bytes")
        outputs["reproduction-results.json"] = raw
        return len(raw)

    previous_argv = sys.argv
    stdout = io.StringIO()
    try:
        sys.argv = [str(script), str(out)]
        Path.read_bytes = pinned_read_bytes
        Path.write_bytes = capture_output_bytes
        with contextlib.redirect_stdout(stdout):
            exec(compile(captured[CAPSULE], str(script), "exec"),
                 {"__name__": "__main__", "__file__": str(script)})
    finally:
        Path.read_bytes = read_bytes
        Path.write_bytes = write_bytes
        sys.argv = previous_argv
    return stdout.getvalue(), outputs


def destination(name):
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError("output name must be one plain fresh directory name")
    root = HERE / "outputs"
    if root.is_symlink() or not root.is_dir() or root.resolve() != root:
        raise ValueError("unsafe outputs directory")
    target = root / name
    if target.exists() or target.is_symlink():
        raise FileExistsError("output already exists")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    root_fd = os.open(str(root), flags)
    try:
        os.mkdir(name, dir_fd=root_fd)
        out_fd = os.open(name, flags, dir_fd=root_fd)
    finally:
        os.close(root_fd)
    return target, out_fd


def write_exclusive(directory_fd, name, raw):
    if name not in ("reproduction-results.json", "failure.json"):
        raise ValueError("unplanned output file")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    file_fd = os.open(name, flags, 0o600, dir_fd=directory_fd)
    with os.fdopen(file_fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def publish_exclusive(directory_fd, raw):
    """Expose a success receipt only after its complete bytes are synced."""
    temporary = ".publication-" + secrets.token_hex(12)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    file_fd = os.open(temporary, flags, 0o600, dir_fd=directory_fd)
    try:
        with os.fdopen(file_fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, "publication.json", src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd, follow_symlinks=False)
    finally:
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="fresh plain name under outputs/")
    parser.add_argument("--fail-after-compute", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    captured = validate()  # The exact bytes used below are captured before destination creation.
    out, out_fd = destination(args.output)
    capsule_stdout = ""
    try:
        capsule_stdout, output_bytes = execute_captured_capsule(captured, out)
        actual = output_bytes.get("reproduction-results.json")
        if actual is None:
            raise ValueError("capsule did not create its report")
        retained = captured["inputs/original-reproduction-results.json"]
        write_exclusive(out_fd, "reproduction-results.json", actual)
        if actual != retained:
            raise ValueError("report differs from the exact retained result")
        if args.fail_after_compute:
            raise RuntimeError("directed failure after computation; preserve this attempt")
        receipt = {"status": "complete", "capsule_sha256": CAPSULE_SHA256,
                   "report_sha256": sha(actual)}
        publish_exclusive(out_fd, (json.dumps(receipt, sort_keys=True) + "\n").encode())
        print(json.dumps({"exit_code": 0, "report_sha256": sha(actual),
                          "capsule_sha256": CAPSULE_SHA256,
                          "output": str((out / "reproduction-results.json").relative_to(HERE)),
                          "stdout": capsule_stdout}, sort_keys=True))
    except Exception as exc:
        failure = {"status": "failed", "error": str(exc),
                   "report_sha256": sha(output_bytes["reproduction-results.json"])
                   if "output_bytes" in locals() and "reproduction-results.json" in output_bytes else None,
                   "capsule_stdout": capsule_stdout}
        if "output_bytes" in locals() and "reproduction-results.json" in output_bytes:
            try:
                write_exclusive(out_fd, "reproduction-results.json", output_bytes["reproduction-results.json"])
            except FileExistsError:
                pass
        write_exclusive(out_fd, "failure.json", (json.dumps(failure, sort_keys=True) + "\n").encode())
        raise
    finally:
        os.close(out_fd)


if __name__ == "__main__":
    main()

"""Authenticated readers and safe vintage publication for the bounded erratum."""
import hashlib
import json
import os
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OWNED = "research/geography/saravan-panjgur-source-execution-1121-erratum/"
MANIFEST_PATH = OWNED + "evidence-quality.json"
EXPECTED_HELPER = "a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46"
HELPER_COMMIT = "696d1eadd9afdff8267ef3166c4c6b8b849011f5"
LEGACY_COMMIT = "39eff6e40063a4a22bfc4e6655487404c35c54c4"
LEGACY_MODULES = {
    "native": "coordination/engineering/iran-pakistan-native-seam-971-20261005-local09/reproduce.py",
    "evidence.immutable": "scripts/evidence/immutable.py",
    "evidence.geometry": "scripts/evidence/geometry.py",
    "ellipsoidal_area": "scripts/ellipsoidal_area.py",
}
SUBJECTS = [
    "gb:IRN:ADM2:26516999B17111396986996",
    "gb:PAK:ADM2:60131773B78019453337506",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(commit, path):
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        stderr=subprocess.PIPE,
    )


def load_trusted_helper(manifest):
    row = next(
        f for f in manifest["baseline"]["files"]
        if f["path"] == "scripts/evidence/immutable.py"
        and f.get("commit") == HELPER_COMMIT and f["sha256"] == EXPECTED_HELPER
    )
    raw = git_blob(HELPER_COMMIT, row["path"])
    if len(raw) != row["bytes"] or sha(raw) != EXPECTED_HELPER:
        raise ValueError("Current shared byte helper differs from its immutable pin")
    module = types.ModuleType("worldatlas_trusted_immutable")
    module.__file__ = f"{ROOT}/{row['path']}"
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


class CapturedBaseline:
    """Composite version-2 reader; every (commit,path) is a whole-file pin."""
    def __init__(self, helper, manifest):
        self.helper = helper
        self.repo = str(ROOT)
        self.commit = manifest["baseline"]["commit"]
        self.max_phase_bytes = helper.MAX_PHASE_BYTES
        self.consumed = {}
        self.rows = {}
        self.pins = {}
        for item in manifest["baseline"]["files"]:
            commit = item.get("commit")
            if not commit:
                raise ValueError("Historical file lacks its explicit immutable commit")
            key = f"{item['path']}@{commit}"
            if key in self.rows:
                raise ValueError("Duplicate historical (commit,path) descriptor")
            self.rows[key] = item
            self.pins[key] = item
        # A candidate copy is not an input. Verify all versioned inputs before use.
        for key in self.rows:
            self.pinned_bytes(key)

    def admit(self, key, size):
        self.helper.safe_path(key)
        if size < 0 or size > self.helper.MAX_FILE_BYTES:
            raise ValueError("Input exceeds shared per-file byte limit")
        old = self.consumed.get(key)
        if old is not None and old != size:
            raise ValueError("Captured input size changed")
        if old is None:
            if sum(self.consumed.values()) + size > self.max_phase_bytes:
                raise ValueError("Complete source/code phase exceeds shared byte limit")
            self.consumed[key] = size

    def pinned_bytes(self, key):
        row = self.rows.get(key)
        if row is None:
            raise ValueError("Consumed source or code is not declared in the immutable manifest")
        raw = git_blob(row["commit"], row["path"])
        self.admit(key, len(raw))
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("Captured source/code bytes disagree with immutable whole-file pin: " + row["path"])
        return raw

    def bytes_for(self, path, commit):
        return self.pinned_bytes(f"{path}@{commit}")

    def json_for(self, path, commit):
        return json.loads(self.bytes_for(path, commit))


def descriptor(path, raw):
    return {"path": path, "bytes": len(raw), "sha256": sha(raw), "hash_kind": "file-bytes"}


def authenticated_modules(base):
    # The complete original execution closure is loaded from an immutable
    # ancestor commit with the issue-pinned whole-file hashes, not from the
    # mutable worktree. The older producer commit remains recorded in the
    # archived result and is not silently adopted as an evidence baseline.
    module_files = LEGACY_MODULES
    # The original producer commit is recorded in the prior result but is not
    # an ancestor of current main. This identical whole-file closure is also
    # present at the retained merge commit below, which the hosted gate can verify.
    commit = LEGACY_COMMIT
    # Baseline.load_modules verifies all captured module bytes against the
    # historical whole-file descriptors before executing their import closure.
    original = base.helper.Baseline(
        ROOT, commit,
        [next(f for f in base.rows.values() if f["path"] == path and f["commit"] == commit)
         for path in module_files.values()],
    )
    modules = original.load_modules(module_files)
    # Reconcile bytes consumed by the shared helper with our phase-wide ledger.
    for path, row in zip(module_files.values(), original.pins.values()):
        key = f"{path}@{commit}"
        raw = original.pinned_bytes(path)
        if sha(raw) != row["sha256"]:
            raise ValueError("Loaded module is not the manifest-pinned vintage")
        base.admit(key, len(raw))
    return modules


def output_writer(base, vintage, filenames):
    # Delegate path, symlink, exclusive-creation, complete-budget and final
    # receipt handling to the shared immutable NewVintage writer.
    class WriterBaseline:
        repo = base.repo
        commit = base.commit
        max_phase_bytes = base.max_phase_bytes
        consumed = base.consumed
        pins = base.pins

        @staticmethod
        def pinned_bytes(key):
            return base.pinned_bytes(key)

    return base.helper.NewVintage(WriterBaseline(), OWNED, vintage, filenames)


def code_receipt(paths):
    records = []
    for path in paths:
        raw = Path(path).read_bytes()
        records.append({"path": str(Path(path).relative_to(ROOT)), "bytes": len(raw), "sha256": sha(raw)})
    return records


def runtime_receipt():
    import numpy
    import pyproj
    import shapely
    return {"python": sys.version.split()[0], "numpy": numpy.__version__,
        "shapely": shapely.__version__, "geos": shapely.geos_version_string,
        "pyproj": pyproj.__version__, "proj": pyproj.proj_version_str}


def load_run(vintage, names):
    manifest = json.loads((ROOT / MANIFEST_PATH).read_bytes())
    helper = load_trusted_helper(manifest)
    base = CapturedBaseline(helper, manifest)
    modules = authenticated_modules(base)
    writer = output_writer(base, vintage, names)
    return manifest, base, modules, writer

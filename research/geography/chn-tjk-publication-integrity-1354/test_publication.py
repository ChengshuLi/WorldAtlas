"""Black-box custody controls for the real producer/comparison CLI."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
PACKET = Path(__file__).resolve().parent
RUNS = PACKET / "vintages"
SCRIPT = PACKET / "reproduce.py"
PYTHON = sys.executable
GOOD = "run-20261008-b2"
FIRST = "run-20261008-b1"
FILES = ["member-inventory.json", "positive-control.json", "negative-control.json", "execution.json"]


def cli(*args):
    return subprocess.run([PYTHON, "-I", "-B", str(SCRIPT), *args], cwd=ROOT,
                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class PublicationTests(unittest.TestCase):
    def fixture(self, name, mutate):
        source = RUNS / GOOD
        target = RUNS / name
        shutil.copytree(source, target)
        receipt_path = target / "publication.json"
        receipt = json.loads(receipt_path.read_text())
        for row in receipt["outputs"]:
            row["path"] = str(Path("research/geography/chn-tjk-publication-integrity-1354/vintages") / name / Path(row["path"]).name)
        mutate(target, receipt)
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        return target

    def reject_fixture(self, case, mutate):
        fixture = "fixture-" + case
        destination = "compare-reject-" + case
        try:
            self.fixture(fixture, mutate)
            result = cli("--compare", FIRST, fixture, "--vintage", destination)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertFalse((RUNS / destination / "publication.json").exists())
        finally:
            shutil.rmtree(RUNS / fixture, ignore_errors=True)
            shutil.rmtree(RUNS / destination, ignore_errors=True)

    def test_intact_runs_publish_complete_comparison(self):
        receipt = json.loads((RUNS / "compare-20261008-a1" / "publication.json").read_text())
        result = json.loads((RUNS / "compare-20261008-a1" / "reproducibility.json").read_text())
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual(result["outcome"], "passed")
        self.assertTrue(result["byte_identical_payloads"])

    def test_failed_status_rejected(self):
        def mutate(_root, receipt):
            receipt["status"] = "failed"
        self.reject_fixture("status", mutate)

    def test_unsupported_version_rejected(self):
        def mutate(_root, receipt):
            receipt["version"] = 999
        self.reject_fixture("version", mutate)

    def test_duplicate_descriptor_rejected(self):
        self.reject_fixture("duplicate", lambda _root, receipt: receipt["outputs"].append(dict(receipt["outputs"][0])))

    def test_foreign_run_paths_rejected(self):
        def mutate(_root, receipt):
            for row in receipt["outputs"]:
                row["path"] = "research/geography/foreign-owner/vintages/other/" + Path(row["path"]).name
        self.reject_fixture("foreign", mutate)

    def test_missing_and_altered_products_rejected(self):
        self.reject_fixture("missing", lambda root, _receipt: (root / FILES[0]).unlink())
        self.reject_fixture("altered", lambda root, _receipt: (root / FILES[0]).write_bytes((root / FILES[0]).read_bytes() + b"altered"))

    def test_both_writer_entrypoints_reject_bad_destinations(self):
        cases = ["ordinary-file", "directory", "symlink", "dangling-symlink"]
        for writer in ("producer", "comparison"):
            for case in cases:
                name = "control-" + writer + "-" + case
                target = RUNS / name
                if case == "ordinary-file":
                    target.write_text("occupied")
                elif case == "directory":
                    target.mkdir()
                elif case == "symlink":
                    target.symlink_to(RUNS / GOOD, target_is_directory=True)
                else:
                    target.symlink_to(RUNS / "not-present")
                args = (("--vintage", name) if writer == "producer" else ("--compare", FIRST, GOOD, "--vintage", name))
                result = cli(*args)
                self.assertNotEqual(result.returncode, 0, f"{writer} accepted {case}")
                self.assertTrue(target.exists() or target.is_symlink())
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    shutil.rmtree(target)
        for writer in ("producer", "comparison"):
            args = (("--vintage", "../escape") if writer == "producer" else ("--compare", FIRST, GOOD, "--vintage", "../escape"))
            result = cli(*args)
            self.assertNotEqual(result.returncode, 0, f"{writer} accepted traversal")

    def test_failed_exclusive_writer_leaves_no_completion_receipt(self):
        # Inject a late atomic-link failure in the exact shared NewVintage writer
        # used by both CLI entrypoints, after payload creation but before receipt.
        code = r'''import pathlib, sys
root=pathlib.Path(sys.argv[1]); sys.path.insert(0, str(root))
from scripts.evidence import immutable
owned="research/geography/chn-tjk-publication-integrity-1354/"
class B:
 repo=str(root); pins={}; consumed={}; max_phase_bytes=256*1024*1024
 def pinned_bytes(self,n): return b""
b=B(); vintage="failed-partial-test"
dest=immutable.NewVintage(b,owned,vintage,["one.json"])
original=immutable.os.link
def fail(source,target,*a,**k):
 if pathlib.Path(target).name=="publication.json": raise OSError("injected late receipt-link failure")
 return original(source,target,*a,**k)
immutable.os.link=fail
try: dest.publish_bytes({"one.json":b"{}\n"})
except OSError: pass
else: raise SystemExit("failure injection did not fire")
assert (root/owned/"vintages"/vintage/"one.json").is_file()
assert not (root/owned/"vintages"/vintage/"publication.json").exists()
'''
        # Run a temporary script from an isolated Python process; its argument
        # supplies the repository path used by the injected shared writer test.
        run = subprocess.run([PYTHON, "-I", "-B", "-c", code, str(ROOT)], cwd=ROOT,
                             text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if run.returncode:
            with tempfile.NamedTemporaryFile("w", suffix=".py", dir=ROOT, delete=False) as stream:
                stream.write(code)
                helper_test = Path(stream.name)
            try:
                run = subprocess.run([PYTHON, "-I", "-B", str(helper_test), str(ROOT)], cwd=ROOT,
                                     text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            finally:
                helper_test.unlink()
        self.assertEqual(run.returncode, 0, run.stderr)
        shutil.rmtree(RUNS / "failed-partial-test", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

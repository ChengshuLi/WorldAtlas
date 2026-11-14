"""Source capture preserves bytes and can restore an installable project without Git."""

import base64
from pathlib import Path, PurePosixPath
import tempfile
import unittest
from unittest.mock import Mock, patch

from worldatlas.map_build.execution.code_archive import (
    capture_source,
    read_source,
    restore_source,
    source_files,
    write_source,
)


class SourceArchiveTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.project = self.root / "project"
        self.package = self.project / "src/worldatlas"
        self.package.mkdir(parents=True)
        (self.package / "__init__.py").write_bytes(b"# source\r\n")
        (self.package / "module.py").write_bytes(b"value = 42\r\n")
        for name in ("environment.yml", "pyproject.toml", "README.md"):
            (self.project / name).write_text("setup: " + name)

    def test_capture_and_restore_preserve_bytes_without_git(self):
        captured = capture_source(self.package)
        (self.package / "module.py").write_text("changed after capture")
        archived = self.root / "source.json.gz"
        write_source(archived, captured)
        restore_source(read_source(archived), self.root / "restored")
        self.assertEqual(
            (self.root / "restored/src/worldatlas/module.py").read_bytes(),
            b"value = 42\r\n",
        )
        self.assertEqual(
            (self.root / "restored/environment.yml").read_bytes(),
            (self.project / "environment.yml").read_bytes(),
        )
        with self.assertRaises(FileExistsError):
            restore_source(captured, self.root / "restored")

    def test_installed_distribution_supplies_setup_files(self):
        package = self.root / "site-packages/worldatlas"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("")
        files = [
            PurePosixPath("../../../share/worldatlas/" + name)
            for name in ("environment.yml", "pyproject.toml", "README.md")
        ]
        installed = Mock(files=files)
        installed.locate_file.side_effect = lambda item: self.project / item.name
        with patch(
            "worldatlas.map_build.execution.code_archive.distribution",
            return_value=installed,
        ):
            result = capture_source(package)
        self.assertIn("environment.yml", result["files"])
        self.assertIn("src/worldatlas/__init__.py", result["files"])

    def test_capture_omits_bytecode_and_rejects_source_symlinks(self):
        cache = self.package / "__pycache__"
        cache.mkdir()
        (cache / "module.py").write_text("cached")
        self.assertFalse(
            any("__pycache__" in p for p in capture_source(self.package)["files"])
        )
        (self.package / "linked.py").symlink_to(self.package / "module.py")
        with self.assertRaisesRegex(ValueError, "symlink"):
            capture_source(self.package)

    def test_invalid_paths_and_bytes_fail_before_creating_output(self):
        for name, raw in [
            ("../escape.py", "YQ=="),
            ("/absolute.py", "YQ=="),
            ("a/../escape.py", "YQ=="),
            ("a\\escape.py", "YQ=="),
            ("bad.py", "not base64!"),
            (".", "YQ=="),
        ]:
            with self.subTest(name=name):
                content = capture_source(self.package)
                content["files"][name] = raw
                target = self.root / "invalid"
                with self.assertRaises(ValueError):
                    restore_source(content, target)
                self.assertFalse(target.exists())

    def test_file_directory_collisions_are_rejected(self):
        content = capture_source(self.package)
        content["files"]["src/worldatlas"] = base64.b64encode(b"file").decode()
        with self.assertRaisesRegex(ValueError, "file and a directory"):
            source_files(content)

    def test_archive_bytes_are_deterministic(self):
        content = capture_source(self.package)
        a, b = self.root / "a.gz", self.root / "b.gz"
        write_source(a, content)
        write_source(b, content)
        self.assertEqual(a.read_bytes(), b.read_bytes())

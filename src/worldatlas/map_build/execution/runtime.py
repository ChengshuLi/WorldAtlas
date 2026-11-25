"""Record pipeline identities and checkpoint completed build outputs."""

from __future__ import annotations

import fcntl
import hashlib
import os
import subprocess
import sys
import traceback
import uuid
from collections.abc import Callable, Generator, Iterable
from contextlib import closing, contextmanager
from functools import partial
from pathlib import Path
from stat import S_ISREG
from typing import Any, TypedDict, cast

import numpy
import pyarrow
import pyproj
import scipy
from osgeo import gdal
from pyproj import datadir

from worldatlas.map_build.execution.code_archive import capture_source, write_source
from worldatlas.map_build.execution.journal import verify_anchor
from worldatlas.map_build.execution.timing import (
    TIMING_LOG,
    SetupStart,
    Timing,
    verify_setup_timing,
)
from worldatlas.shared.files import (
    FilePin,
    JSONValue,
    json_bytes,
    pin_file,
    read_json,
    sha256_file,
    sync_directory,
    write_bytes_atomic,
    write_json,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
TASK_CHECKPOINT_SCHEMA = "worldatlas-task-checkpoint-v2"


def save_or_verify_settings(path: Path, settings: JSONValue) -> FilePin:
    """Save build settings once and return a pin for their exact JSON bytes.

    Args:
        path: Absolute path to the saved settings in the run directory.
        settings: Settings to encode as JSON.

    Returns:
        The settings file's absolute path and SHA-256 checksum.

    Raises:
        ValueError: An existing settings file differs from the current settings.
    """
    data = json_bytes(settings)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"saved build settings differ: {path}")
    else:
        write_bytes_atomic(path, data)
    return FilePin(path=str(path), sha256=hashlib.sha256(data).hexdigest())


class RunFilePins:
    """Remember file checksums while their filesystem identity is unchanged."""

    def __init__(self) -> None:
        """Start an empty checksum cache for one build attempt."""
        self.digests: dict[Path, tuple[os.stat_result, str]] = {}

    @staticmethod
    def stamp(stat: os.stat_result) -> tuple[int, int, int, int, int]:
        """Identify the file and the last changes to its bytes or metadata.

        Args:
            stat: File metadata returned by the operating system.

        Returns:
            Device, inode, size, modification time and change time. Both times
            use the full nanosecond values reported by the operating system.
        """
        return (
            stat.st_dev,
            stat.st_ino,
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
        )

    def pin(self, path: Path | str) -> FilePin:
        """Record a file's checksum, rehashing it whenever it changes.

        Args:
            path: Local path to a completed output or its pinned input.

        Returns:
            Absolute path and SHA-256, in the standard file pin format.

        Raises:
            ValueError: The path is not a regular file or changes during hashing.
        """
        path = Path(path).resolve(strict=True)
        before = path.stat()
        if not S_ISREG(before.st_mode):
            raise ValueError(f"not a file: {path}")
        previous = self.digests.get(path)
        if previous is not None and self.stamp(previous[0]) == self.stamp(before):
            return {"path": str(path), "sha256": previous[1]}
        checksum = sha256_file(path)
        if self.stamp(path.stat()) != self.stamp(before):
            raise ValueError(f"file changed while hashing: {path}")
        self.digests[path] = (before, checksum)
        return {"path": str(path), "sha256": checksum}

    def verify(self, pins: Iterable[FilePin]) -> None:
        """Check the file identity and checksum of every supplied pin.

        Args:
            pins: Records with a path and expected SHA-256.

        Raises:
            ValueError: One of the files no longer matches its pin.
        """
        for expected in pins:
            if self.pin(expected["path"])["sha256"] != expected["sha256"]:
                raise ValueError("checkpoint/input hash mismatch: " + expected["path"])

    def row_streams(self, directory: Path | str) -> list[FilePin]:
        """Record checksums for both files in a row-run layer.

        Args:
            directory: Physical, membership, or ownership layer directory.

        Returns:
            Pins for rows.u32le followed by runs.u32le.
        """
        return [
            self.pin(Path(directory) / name) for name in ("rows.u32le", "runs.u32le")
        ]

    def inventory(self, paths: Iterable[Path | str]) -> list[FilePin]:
        """List and hash the regular files in the supplied outputs.

        Args:
            paths: Files or directories to scan in order.

        Returns:
            File pins in traversal order, with each directory sorted by filename.

        Raises:
            ValueError: A path is missing, a symlink, or not a regular file or directory.
        """
        result = []

        def visit(path: Path) -> None:
            """Collect file pins beneath one path.

            Args:
                path: File or directory to visit.
            """
            if path.is_symlink():
                raise ValueError("symlink checkpoint output: " + str(path))
            elif path.is_file():
                result.append(self.pin(path))
            elif path.is_dir():
                for child in sorted(path.iterdir()):
                    visit(child)
            else:
                raise ValueError(
                    "missing or non-regular checkpoint output: " + str(path)
                )

        for value in paths:
            visit(Path(value))
        return result


type RuntimeIdentity = dict[str, str | FilePin]


def runtime_identity() -> RuntimeIdentity:
    """Record the Python and geographic libraries used by this run.

    Returns:
        Dictionary with version strings, the Python executable's SHA-256,
        and the PROJ database path and SHA-256.
    """
    return {
        "executable": sys.executable,
        "version": sys.version,
        "binary_sha256": sha256_file(Path(sys.executable).resolve()),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "pyproj": pyproj.__version__,
        "proj": pyproj.proj_version_str,
        "proj_database": pin_file(Path(datadir.get_data_dir()) / "proj.db"),
        "gdal": gdal.VersionInfo("RELEASE_NAME"),
        "pyarrow": pyarrow.__version__,
    }


def code_identity(scripts: Path | str) -> dict[str, str]:
    """Hash Python and native source files under a package.

    Args:
        scripts: Directory holding source files.

    Returns:
        Relative path strings mapped to lowercase SHA-256 digests.
    """
    return {
        str(path.relative_to(scripts)): sha256_file(path)
        for path in sorted(Path(scripts).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".cpp", ".c", ".h", ".hpp", ".sh"}
    }


class RepositoryIdentity(TypedDict):
    """Record the Git commit, local changes, and setup files for a build."""

    commit: str
    working_changes: str | None
    setup: dict[str, str]


def repository_identity(package: Path | str) -> RepositoryIdentity | None:
    """Record the Git checkout and setup files used for this build.

    Args:
        package: Package directory in a possible Git checkout.

    Returns:
        Dictionary with commit, local diff, and setup file text, or None
        when the package is outside a Git checkout.
    """
    root = next(
        (p for p in Path(package).resolve().parents if (p / ".git").exists()), None
    )
    if root is None:
        return None

    def git(*args: str) -> str | None:
        """Run Git in the source checkout without printing.

        Args:
            args: Git subcommand and its arguments.

        Returns:
            Command output text, or None if Git returns an error status.
        """
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, text=True
        )
        return result.stdout if result.returncode == 0 else None

    return {
        "commit": (git("rev-parse", "HEAD") or "").strip(),
        "working_changes": git("diff", "--binary", "HEAD"),
        "setup": {
            name: (root / name).read_text()
            for name in ("environment.yml", "pyproject.toml")
            if (root / name).is_file()
        },
    }


class RunLock:
    """Keep two processes from writing to the same build run."""

    def __init__(self, path: Path | str) -> None:
        """Take an exclusive lock on the run's local lock file.

        Args:
            path: Lock file to open or create.

        Raises:
            ValueError: Another runner holds the lock.
        """
        self.stream = Path(path).open("a+b")
        try:
            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.stream.close()
            raise ValueError("another pipeline runner still owns this run") from None

    def close(self) -> None:
        """Close the lock file and release the lock."""
        if not self.stream.closed:
            self.stream.close()

    def __del__(self) -> None:
        """Release the lock when the runner is collected."""
        self.close()


class Checkpoints:
    """Save and verify a build stage's completed outputs."""

    def __init__(self, root: Path | str, build_attempt_id: str) -> None:
        """Prepare the run's checkpoint directory.

        Args:
            root: Directory for stage checkpoint files.
            build_attempt_id: Identifier for this invocation of the build.
        """
        self.root = Path(root).resolve()
        self.build_attempt_id = build_attempt_id
        self.files = RunFilePins()
        self.root.mkdir(exist_ok=True)
        self.preserved = self.root.parent / "preserved"

    def stage(self, name: str) -> Path:
        """Create or open a named stage's checkpoint directory.

        Args:
            name: Stage ID using lowercase letters, digits, hyphens or underscores.

        Returns:
            Directory for the stage.

        Raises:
            ValueError: The stage name is invalid.
        """
        if not name or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in name
        ):
            raise ValueError("unsafe checkpoint name")
        path = self.root / name
        path.mkdir(exist_ok=True)
        return path

    def _verify_completion(
        self, path: Path, invocation: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Read a completion record and verify its files and timing log.

        Args:
            path: Path to the task's completion record.
            invocation: Current task request to compare with the saved request.

        Returns:
            The saved record, including the task's return value.

        Raises:
            ValueError: The record uses an unsupported format or its data changed.
        """
        receipt = read_json(path)
        name = path.parent.name
        if receipt.get("schema") != TASK_CHECKPOINT_SCHEMA:
            raise ValueError(
                "resume this task with its original checkpoint format: " + name
            )
        saved = receipt["invocation"]
        # The function name is provenance. Resume compares the task's data.
        if invocation is not None and any(
            saved[key] != invocation[key] for key in ("stage", "inputs", "outputs")
        ):
            raise ValueError("completed command identity changed: " + name)
        verify_anchor(receipt["timing_anchor"], self.root.parent / TIMING_LOG)
        self.files.verify(saved["inputs"])
        if self.files.inventory(saved["outputs"]) != receipt["outputs"]:
            raise ValueError("completed stage output changed: " + name)
        return receipt

    def preserve(
        self, name: str, paths: Iterable[Path | str]
    ) -> list[tuple[Path, Path]]:
        """Move incomplete outputs aside for debugging.

        Args:
            name: Stage ID used to name the preserved directory.
            paths: Output paths to move if present.

        Returns:
            List of (original_path, preserved_path) pairs.

        Raises:
            ValueError: A path is outside the current run.
        """
        existing = list(
            dict.fromkeys(
                Path(path)
                for path in paths
                if Path(path).exists() or Path(path).is_symlink()
            )
        )
        if not existing:
            return []
        destination = self.preserved / (name + "-" + uuid.uuid4().hex)
        destination.mkdir(parents=True)
        moved = []
        for index, path in enumerate(existing):
            if (
                not path.resolve().is_relative_to(self.root.parent)
                or path.resolve() == self.root.parent
            ):
                raise ValueError("partial output outside run cannot be moved")
            target = destination / f"{index}-{path.name}"
            path.rename(target)
            moved.append((path, target))
            sync_directory(path.parent)
        sync_directory(destination)
        sync_directory(destination.parent)
        return moved

    def verify_all(self) -> None:
        """Verify the timing log and saved files for every completed stage.

        Raises:
            ValueError: A log prefix or file differs from its saved record.
        """
        for path in self.root.glob("*/attempt-*/admitted.json"):
            admission = read_json(path)
            verify_anchor(admission["timing_anchor"], self.root.parent / TIMING_LOG)
        for path in self.root.glob("*/complete.json"):
            self._verify_completion(path)

    def begin(self, name: str) -> Path:
        """Create a directory for one attempt to run a checkpointed task.

        Args:
            name: Task ID used for the checkpoint directory.

        Returns:
            Path to the new task attempt directory under the task's checkpoint.
        """
        task_attempt_dir = self.stage(name) / ("attempt-" + uuid.uuid4().hex)
        task_attempt_dir.mkdir()
        sync_directory(task_attempt_dir.parent)
        return task_attempt_dir

    def _write_completion(
        self,
        path: Path,
        invocation: dict[str, Any],
        result: JSONValue,
        timing_anchor: dict[str, str | int],
    ) -> None:
        """Save the task's return value and verified files in one record.

        Args:
            path: Destination for the completion record.
            invocation: Task request with input pins and expected output paths.
            result: JSON-compatible value returned by the task.
            timing_anchor: Timing log path, prefix length and digest.
        """
        self.files.verify(invocation["inputs"])
        write_json(
            path,
            {
                "schema": TASK_CHECKPOINT_SCHEMA,
                "attempt": self.build_attempt_id,
                "timing_anchor": timing_anchor,
                "invocation": invocation,
                "outputs": self.files.inventory(invocation["outputs"]),
                "result": result,
            },
        )

    def run_function[Result: JSONValue](
        self,
        name: str,
        group: str,
        operation: Callable[[], Result],
        *,
        timing: Timing,
        inputs: Iterable[FilePin],
        outputs: Iterable[Path | str],
        timing_kind: str = "processing",
    ) -> Result:
        """Run a task or load its verified result from an earlier task attempt.

        Each new task attempt records its starting inputs in ``admitted.json``
        and stores any traceback from the operation in ``error.log``.

        Args:
            name: Task ID for the checkpoint.
            group: Stage that receives the task's elapsed time.
            operation: Task function with its arguments already supplied.
            timing: Timing journal for the run.
            inputs: Input file pins.
            outputs: Output files and directories to verify.
            timing_kind: How the operation counts toward stage timing.

        Returns:
            The task result decoded from ``complete.json``.

        Raises:
            ValueError: An output path escapes the run or saved data no longer matches.
        """
        input_pins = [FilePin(path=pin["path"], sha256=pin["sha256"]) for pin in inputs]
        outputs = [Path(path).absolute() for path in outputs]
        run = self.root.parent
        if any(
            not path.resolve().is_relative_to(run.resolve())
            or path.resolve() == run.resolve()
            for path in outputs
        ):
            raise ValueError("stage output outside run or replaces run root")
        completion_path = self.stage(name) / "complete.json"
        function = operation.func if isinstance(operation, partial) else operation
        invocation = {
            "stage": name,
            "inputs": input_pins,
            "outputs": list(map(str, outputs)),
            "code": {"module": function.__module__, "function": function.__qualname__},
        }
        if completion_path.exists():
            return cast(
                Result, self._verify_completion(completion_path, invocation)["result"]
            )
        self.preserve(name, outputs)
        task_attempt_dir = self.begin(name)
        self.files.verify(input_pins)
        write_json(
            task_attempt_dir / "admitted.json",
            {
                "invocation": invocation,
                "inputs": input_pins,
                "timing_anchor": timing.anchor(),
            },
        )
        try:
            with timing.measure(group, name, kind=timing_kind):
                result = operation()
            self._write_completion(completion_path, invocation, result, timing.anchor())
        except BaseException:
            (task_attempt_dir / "error.log").write_text(
                traceback.format_exc(), encoding="utf-8"
            )
            raise
        return cast(Result, read_json(completion_path)["result"])


def prepare_run_attempt(root: Path, *, resume: bool) -> tuple[Path, Checkpoints]:
    """Verify prior work and save the code used by the new build attempt.

    Args:
        root: Run directory whose lock the caller holds.
        resume: Whether to reuse the run's existing attempts directory.

    Returns:
        The new attempt directory and its checkpoint store.
    """
    attempt_id = uuid.uuid4().hex
    checkpoints = Checkpoints(root / "checkpoints", attempt_id)
    checkpoints.verify_all()
    verify_setup_timing(root)
    attempts = root / "attempts"
    attempts.mkdir(mode=0o700, exist_ok=resume)
    attempt_directory = attempts / attempt_id
    attempt_directory.mkdir()
    source_archive = attempt_directory / "source-code.json.gz"
    write_source(source_archive, capture_source(PACKAGE_ROOT))
    write_json(
        attempt_directory / "producer.json",
        {
            "code": code_identity(PACKAGE_ROOT),
            "repository": repository_identity(PACKAGE_ROOT),
            "runtime": runtime_identity(),
            "scripts_root": str(PACKAGE_ROOT),
            "source_archive": pin_file(source_archive),
        },
    )
    return attempt_directory, checkpoints


@contextmanager
def open_stage_workspace(
    root: Path, request: FilePin, *, resume: bool
) -> Generator[tuple[Checkpoints, Timing]]:
    """Open a workspace for a standalone stage with the ordinary run tools.

    Args:
        root: Output directory for the standalone run.
        request: Path and digest of its input configuration.
        resume: Whether to continue the saved request.

    Yields:
        The checkpoint store and timer, with the workspace locked.

    Raises:
        ValueError: The workspace state or saved request differs.
    """
    setup_started = SetupStart.now()
    if root.exists() != resume or not root.parent.is_dir():
        raise ValueError("output must have an existing parent and exist only on resume")
    if not resume:
        root.mkdir()
    with closing(RunLock(root / "run.lock")):
        saved = root / "run-request.json"
        if resume:
            if not saved.is_file() or read_json(saved) != request:
                raise ValueError("saved stage request changed or is missing")
        else:
            write_json(saved, request)
        attempt_dir, checkpoints = prepare_run_attempt(root, resume=resume)
        with closing(
            Timing.open_run(attempt_dir, setup_started, resume=resume)
        ) as timing:
            yield checkpoints, timing

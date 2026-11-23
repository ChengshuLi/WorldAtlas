"""Record pipeline identities and checkpoint completed build outputs."""

from __future__ import annotations

import fcntl
import os
import subprocess
import traceback
import uuid
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import closing, contextmanager
from functools import partial
from pathlib import Path
from stat import S_ISREG
from typing import Any, TypedDict, cast

from worldatlas.map_build.execution.journal import verify_anchor
from worldatlas.map_build.execution.timing import (
    TIMING_LOG,
    SetupStart,
    Timing,
    verify_setup_timing,
)
from worldatlas.map_build.inputs.configuration import FilePin
from worldatlas.shared.files import (
    JSONValue,
    read_json,
    sha256_file,
    sync_directory,
    write_json,
)


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

    def pin(self, path: Path | str) -> dict[str, str]:
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

    def verify(self, pins: Iterable[Mapping[str, str] | FilePin]) -> None:
        """Check the file identity and checksum of every supplied pin.

        Args:
            pins: Records with a path and expected SHA-256.

        Raises:
            ValueError: One of the files no longer matches its pin.
        """
        for expected in pins:
            if self.pin(expected["path"])["sha256"] != expected["sha256"]:
                raise ValueError("checkpoint/input hash mismatch: " + expected["path"])

    def row_streams(self, directory: Path | str) -> list[dict[str, str]]:
        """Record checksums for both files in a row-run layer.

        Args:
            directory: Physical, membership, or ownership layer directory.

        Returns:
            Pins for rows.u32le followed by runs.u32le.
        """
        return [
            self.pin(Path(directory) / name) for name in ("rows.u32le", "runs.u32le")
        ]

    def inventory(self, paths: Iterable[Path | str]) -> list[dict[str, str]]:
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

    def __init__(self, root: Path | str, attempt: str) -> None:
        """Prepare the run's checkpoint directory.

        Args:
            root: Directory for stage checkpoint files.
            attempt: Identifier of the current build attempt.
        """
        self.root, self.attempt = Path(root).resolve(), attempt
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

    def completed(
        self, name: str, invocation: dict[str, Any], outputs: Iterable[Path | str]
    ) -> bool:
        """Verify the inputs and output files of a completed stage.

        Args:
            name: Stage ID.
            invocation: Current stage inputs and expected output paths.
            outputs: Files or directories the stage should have written.

        Returns:
            True after successful verification, or False if no receipt exists.

        Raises:
            ValueError: Timing, input, or output records do not match.
        """
        path = self.stage(name) / "complete.json"
        if not path.exists():
            return False
        receipt = read_json(path)
        verify_anchor(receipt["timing_anchor"], self.root.parent / TIMING_LOG)
        request = lambda value: {k: v for k, v in value.items() if k != "code"}
        if receipt.get("schema") != "worldatlas-command-checkpoint-v1" or request(
            receipt["invocation"]
        ) != request(invocation):
            raise ValueError("completed command identity changed: " + name)
        self.files.verify(self.data_pins(receipt))
        if self.files.inventory(outputs) != receipt["outputs"]:
            raise ValueError("completed stage output changed: " + name)
        return True

    @staticmethod
    def data_pins(receipt: dict[str, Any]) -> list[dict[str, str]]:
        # Earlier checkpoints also included the executable Python file among
        # their inputs. Preserve the receipt and verify its data inputs only.
        """Find the input file pins that must still match on resume.

        Args:
            receipt: Completed stage record.

        Returns:
            Path and SHA-256 dictionaries for the stage's data files.
        """
        code_path = receipt["invocation"].get("code", {}).get("path")
        return [pin for pin in receipt["inputs"] if pin["path"] != code_path]

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
            receipt = read_json(path)
            verify_anchor(receipt["timing_anchor"], self.root.parent / TIMING_LOG)
            self.files.verify(self.data_pins(receipt))
            if self.files.inventory(receipt["output_roots"]) != receipt["outputs"]:
                raise ValueError("completed stage output changed: " + path.parent.name)

    def begin(self, name: str) -> Path:
        """Create a directory for one stage attempt.

        Args:
            name: Stage ID.

        Returns:
            Path to the new attempt directory.
        """
        path = self.stage(name) / ("attempt-" + uuid.uuid4().hex)
        path.mkdir()
        sync_directory(path.parent)
        return path

    def complete(
        self,
        name: str,
        invocation: dict[str, Any],
        outputs: list[Path],
        inputs: Iterable[Mapping[str, str] | FilePin],
        timing_anchor: dict[str, str | int],
    ) -> None:
        """Write a stage's completion record after verifying its saved outputs.

        Args:
            name: Stage ID.
            invocation: Stage request used to check resume compatibility.
            outputs: Directories and files to hash as completed outputs.
            inputs: Expected path and SHA-256 pins for the inputs.
            timing_anchor: Timing log path, prefix length and digest.
        """
        self.files.verify(inputs)
        write_json(
            self.stage(name) / "complete.json",
            {
                "schema": "worldatlas-command-checkpoint-v1",
                "attempt": self.attempt,
                "timing_anchor": timing_anchor,
                "invocation": invocation,
                "inputs": inputs,
                "output_roots": [os.path.abspath(p) for p in outputs],
                "outputs": self.files.inventory(outputs),
            },
        )

    def run_function[Result: JSONValue](
        self,
        name: str,
        group: str,
        operation: Callable[[], Result],
        *,
        timing: Timing,
        inputs: Iterable[Mapping[str, str] | FilePin],
        outputs: Iterable[Path | str],
        timing_kind: str = "processing",
    ) -> Result:
        """Run a stage or load its verified result from a previous attempt.

        Args:
            name: Stage ID for the checkpoint.
            group: Timing group that contains this stage.
            operation: Stage function with its inputs already supplied.
            timing: Timing journal for the run.
            inputs: Input file pins.
            outputs: Output files and directories to verify.
            timing_kind: How the operation counts toward stage timing.

        Returns:
            The stage result decoded from its saved JSON file.

        Raises:
            ValueError: An output path escapes the run or saved data no longer matches.
        """
        input_pins = [{"path": pin["path"], "sha256": pin["sha256"]} for pin in inputs]
        outputs = [Path(path).absolute() for path in outputs]
        run = self.root.parent
        if any(
            not path.resolve().is_relative_to(run.resolve())
            or path.resolve() == run.resolve()
            for path in outputs
        ):
            raise ValueError("stage output outside run or replaces run root")
        result_path = self.stage(name) / "result.json"
        function = operation.func if isinstance(operation, partial) else operation
        invocation = {
            "stage": name,
            "inputs": input_pins,
            "outputs": list(map(str, outputs)),
            "code": {"module": function.__module__, "function": function.__qualname__},
        }
        sealed = [*outputs, result_path]
        if self.completed(name, invocation, sealed):
            return cast(Result, read_json(result_path))
        self.preserve(name, sealed)
        attempt = self.begin(name)
        self.files.verify(input_pins)
        write_json(
            attempt / "admitted.json",
            {
                "invocation": invocation,
                "inputs": input_pins,
                "timing_anchor": timing.anchor(),
            },
        )
        try:
            with timing.measure(group, name, kind=timing_kind):
                result = operation()
            write_json(result_path, result)
        except BaseException:
            (attempt / "error.log").write_text(traceback.format_exc(), encoding="utf-8")
            raise
        self.complete(name, invocation, sealed, input_pins, timing.anchor())
        return cast(Result, read_json(result_path))


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
        attempt = uuid.uuid4().hex
        checkpoints = Checkpoints(root / "checkpoints", attempt)
        checkpoints.verify_all()
        verify_setup_timing(root)
        attempt_dir = root / "attempts" / attempt
        attempt_dir.mkdir(parents=True)
        with closing(
            Timing.open_run(attempt_dir, setup_started, resume=resume)
        ) as timing:
            yield checkpoints, timing

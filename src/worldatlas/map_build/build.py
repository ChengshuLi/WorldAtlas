#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas pipeline through final composition."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import signal
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from types import FrameType
from typing import Any, NotRequired, TypedDict, cast

import numpy
import pyarrow
import pyproj
import scipy
from osgeo import gdal
from pyproj import datadir

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.encoding import encode
from worldatlas.map_build.division.hierarchy import HierarchyDivision
from worldatlas.map_build.execution.code_archive import capture_source, write_source
from worldatlas.map_build.execution.control import stage as stage_context
from worldatlas.map_build.execution.runtime import (
    Checkpoints,
    RunLock,
    StageExecutor,
    Timing,
    code_identity,
    repository_identity,
    verify_anchor,
)
from worldatlas.map_build.inputs.configuration import (
    BUILD_CONFIGURATION,
    FilePin,
    PhysicalConfiguration,
    catalog_source_ids,
    physical_configuration,
    require_separate_cache_and_output,
)
from worldatlas.map_build.inputs.selection import (
    prepare_geography,
    read_saved,
    read_selection,
)
from worldatlas.map_build.inputs.selection_types import BuildSelection
from worldatlas.map_build.physical import build as physical_build
from worldatlas.shared.database import connect_neon, neon_connection_url
from worldatlas.shared.files import (
    compact_json_bytes,
    json_bytes,
    pin_file,
    read_json,
    sha256_file,
    verify_pins,
    write_bytes_atomic,
    write_json,
)

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent


type RuntimeIdentity = dict[str, str | dict[str, str]]


class PhysicalReuse(TypedDict):
    """Identify the completed physical grid and files reused by a build."""

    schema: str
    status: str
    source_run: str
    pins: list[dict[str, str]]


class RunIdentity(TypedDict):
    """Store the pinned inputs and options required to resume a build."""

    schema: str
    request: dict[str, str]
    output: str
    divide: list[int] | None
    reuse_from: str | None
    recompute_division: bool
    input_selection_sha256: str
    physical_reuse: NotRequired[PhysicalReuse]


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


def physical_reference(
    run: Path | str, configuration: PhysicalConfiguration
) -> PhysicalReuse:
    """Find reusable physical outputs for the same grid and raw inputs.

    Args:
        run: Earlier completed run directory.
        configuration: Current physical build request with pinned sources.

    Returns:
        The original run path and SHA-256 pins for the row files and grid report.

    Raises:
        ValueError: The earlier output is incomplete, its saved settings
            changed, or the new grid or source settings differ.
    """
    run = Path(run).resolve(strict=True)
    saved = run / "run-identity.json"
    if saved.is_file():
        reuse = read_json(saved).get("physical_reuse")
        if reuse is not None:
            run = Path(reuse["source_run"]).resolve(strict=True)
    root = run / "physical"
    report = read_json(root / "report.json")
    if report.get("status") != "candidate-only" or "configuration" not in report:
        raise ValueError("physical source run is incomplete or missing settings")
    if Grid(**report["grid"]) != Grid(**configuration["grid"]):
        raise ValueError("physical reuse requires the same grid as the source run")

    config_pin = report["configuration"]
    request = Path(config_pin["path"])
    data = request.read_bytes()
    if hashlib.sha256(data).hexdigest() != config_pin["sha256"]:
        raise ValueError("physical source configuration changed: " + str(request))
    previous = json.loads(data)
    for section in ("land_config", "inland_water"):
        if previous[section] != configuration[section]:
            raise ValueError("physical input differs from the source run: " + section)

    checksums = report["physical_output_sha256"]
    files = {
        "rows.u32le": checksums["rows.u32le"],
        "runs.u32le": checksums["runs.u32le"],
        "report.json": report["stage_reports"]["physical"]["sha256"],
    }
    return {
        "schema": "worldatlas-physical-reuse-v1",
        "status": "reused",
        "source_run": str(run),
        "pins": [
            {"path": str(root / "physical" / name), "sha256": digest}
            for name, digest in files.items()
        ],
    }


class Pipeline:
    """Build a map from pinned raw files and saved geographic rules.

    One instance owns the run lock and timing log until the run closes.
    """

    def __init__(
        self,
        config: Path | str,
        output: Path | str,
        *,
        work_dir: Path | str,
        resume: bool = False,
        selection: Path | str | None = None,
        divide: list[int] | None = None,
        reuse_from: Path | str | None = None,
        recompute_division: bool = False,
    ) -> None:
        """Prepare the work directory, pinned inputs, and run journal.

        Args:
            config: Path to the JSON build settings.
            output: Directory inside the workspace for this build's results.
            resume: Continue a run that already has an identity file.
            work_dir: Workspace holding the shared inputs cache and run directories.
            selection: Frozen geographic selection JSON file. Otherwise read the
                working selection.
            divide: Parent entity IDs to divide, including their necessary
                ancestors. Defaults to all configured divisions.
            reuse_from: Earlier run whose physical grid and all compatible
                geographic assignments may be reused.
            recompute_division: Reuse only the physical grid from the earlier run.
                By default, compatible geographic assignments are also reused.

        Raises:
            ValueError: Settings, pinned inputs, or resume options are incompatible.
        """
        setup_started = time.monotonic()
        setup_utc = datetime.now(timezone.utc).isoformat()
        config_path = Path(config).resolve(strict=True)
        config_bytes = config_path.read_bytes()
        self.config_pin = {
            "path": str(config_path),
            "sha256": hashlib.sha256(config_bytes).hexdigest(),
        }
        self.cfg = BUILD_CONFIGURATION.validate_json(config_bytes, strict=True)
        self.grid = Grid(**self.cfg["grid"])

        self.resume = resume
        self.cancelled = threading.Event()
        self._prepare_workspace(output, work_dir)
        saved_identity = self._resolve_run_options(
            divide, reuse_from, recompute_division
        )

        self.selection = self._load_selection(
            catalog_source_ids(self.cfg["sources"]), selection
        )
        self.compiled_divisions = prepare_geography(
            self.selection["geography"], self.requested_parents
        )
        if "coastal_band_metres" not in self.cfg and any(
            rule["operation"] == "nearest_coastal_water"
            for division in self.compiled_divisions.values()
            for rule in division.rules
        ):
            raise ValueError("nearest_coastal_water requires coastal_band_metres")
        self.physical_config = physical_configuration(
            self.cfg, self.selection["raw_sources"], self.grid, self.root / "inputs"
        )
        self.physical_reuse = (
            physical_reference(self.reuse_from, self.physical_config)
            if self.reuse_from is not None
            else None
        )
        self._prepare_run_identity()

        if not resume:
            self.out.mkdir(mode=0o700)
            write_json(self.out / "input-selection.json", self.selection)
        self.run_lock = RunLock(self.out / "run.lock")
        try:
            self._start_attempt(saved_identity, config_bytes)
            self._record_setup_timing(setup_started, setup_utc)
            self.checkpoints.preserve("failure", [self.out / "failure.json"])
        except BaseException:
            if hasattr(self, "timing"):
                self.timing.close()
            self.run_lock.close()
            raise

    def _prepare_workspace(self, output: Path | str, work_dir: Path | str) -> None:
        """Resolve the workspace and require a usable run directory within it.

        Args:
            output: Run directory supplied by the caller.
            work_dir: Workspace to create if needed.

        Raises:
            ValueError: The workspace or run directory is invalid for this mode.
        """
        self.root = Path(work_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.out = Path(output).resolve()
        if not self.out.is_relative_to(self.root):
            raise ValueError("output must be inside --work-dir")
        require_separate_cache_and_output((self.root / "inputs").resolve(), self.out)
        if not self.out.parent.is_dir():
            raise ValueError("output parent directory must exist")
        if self.resume:
            if not self.out.is_dir():
                raise ValueError("resume requires an existing output directory")
        elif self.out.exists():
            raise ValueError("a fresh build requires a new output directory")

    def _resolve_run_options(
        self,
        divide: list[int] | None,
        reuse_from: Path | str | None,
        recompute_division: bool,
    ) -> RunIdentity | None:
        """Apply the requested options or restore them from an interrupted run.

        Args:
            divide: Parent entity IDs to divide, or None for the default.
            reuse_from: Earlier run to reuse, if supplied.
            recompute_division: Whether to reuse only the physical grid.

        Returns:
            The saved run identity on resume, or None for a fresh build.

        Raises:
            ValueError: The checkpoint is missing or the options are incompatible.
        """
        saved_identity = None
        if self.resume:
            if any(
                (
                    divide is not None,
                    reuse_from is not None,
                    recompute_division,
                )
            ):
                raise ValueError(
                    "--resume uses saved options. Omit --divide, --reuse-from, "
                    "and --recompute-division."
                )
            identity_path = self.out / "run-identity.json"
            if not identity_path.is_file():
                raise ValueError(
                    "run has no supported checkpoint identity; preserve it and start a fresh run"
                )
            identity: RunIdentity = read_json(identity_path)
            saved_identity = identity
            divide = identity.get("divide")
            reuse_from = identity["reuse_from"]
            recompute_division = identity["recompute_division"]
        reuse = Path(reuse_from) if reuse_from is not None else None
        if reuse is not None and not self.resume:
            reuse = reuse.resolve()
        if recompute_division and reuse is None:
            raise ValueError("--recompute-division requires --reuse-from")
        self.reuse_from = reuse
        self.recompute_division = recompute_division
        self.requested_parents = divide
        return saved_identity

    def _load_selection(
        self, source_ids: set[str], selection: Path | str | None
    ) -> BuildSelection:
        """Load the geographic records that this run will use.

        Args:
            source_ids: Catalog IDs for physical inputs.
            selection: Saved geographic records for a fresh build.

        Returns:
            Saved records from the run, the supplied file, or the working database.

        Raises:
            ValueError: A selection was supplied with resume, or no
                database connection is configured for a new selection.
        """
        if self.resume:
            if selection is not None:
                raise ValueError("--resume uses the saved selection. Omit --selection.")
            return read_saved(self.out / "input-selection.json")
        if selection is not None:
            return read_saved(selection)
        try:
            url = neon_connection_url()
        except ValueError as exc:
            raise ValueError(f"{exc}, or supply --selection") from None
        with connect_neon(url=url) as database:
            return read_selection(
                database,
                raw_sources=source_ids,
                parents=self.requested_parents,
            )

    def _prepare_run_identity(self) -> None:
        """Record the inputs and options that must match when resuming."""
        self.identity: RunIdentity = {
            "schema": "worldatlas-end-to-end-run-identity-v1",
            "request": self.config_pin,
            "output": str(self.out),
            "divide": self.requested_parents,
            "reuse_from": str(self.reuse_from) if self.reuse_from is not None else None,
            "recompute_division": self.recompute_division,
            "input_selection_sha256": hashlib.sha256(
                compact_json_bytes(self.selection)
            ).hexdigest(),
        }
        if self.physical_reuse is not None:
            self.identity["physical_reuse"] = self.physical_reuse

    def _start_attempt(
        self, saved_identity: RunIdentity | None, config_bytes: bytes
    ) -> None:
        """Prepare the run's saved inputs and capture the code for this attempt.

        Args:
            saved_identity: Saved run identity on resume.
            config_bytes: Original request bytes used to load the settings.

        Raises:
            ValueError: Saved settings, identity, checkpoints or timing records changed.
        """
        self.saved_config = self.out / "build-config.json"
        if saved_identity is not None:
            saved = dict(saved_identity)
            # Earlier run identities also recorded the first attempt's provenance.
            for key in (
                "code",
                "repository",
                "runtime",
                "runtime_paths",
                "scripts_root",
            ):
                saved.pop(key, None)
            if saved != self.identity:
                raise ValueError(
                    "resume request, input selection or output identity changed"
                )
            if self.saved_config.read_bytes() != config_bytes:
                raise ValueError("saved build configuration changed")
        else:
            write_json(self.out / "run-identity.json", self.identity)
            write_bytes_atomic(self.saved_config, config_bytes)
        attempts = self.out / "attempts"
        self.attempt = uuid.uuid4().hex
        self.checkpoints = Checkpoints(self.out / "checkpoints", self.attempt)
        self.checkpoints.verify_all()
        for marker in attempts.glob("*/setup-timing.json"):
            verify_anchor(read_json(marker), self.out / "timing-events.jsonl")

        attempts.mkdir(mode=0o700, exist_ok=self.resume)
        self.attempt_dir = attempts / self.attempt
        self.attempt_dir.mkdir()
        source_archive = self.attempt_dir / "source-code.json.gz"
        write_source(source_archive, capture_source(PACKAGE_ROOT))
        write_json(
            self.attempt_dir / "producer.json",
            {
                "code": code_identity(PACKAGE_ROOT),
                "repository": repository_identity(PACKAGE_ROOT),
                "runtime": runtime_identity(),
                "scripts_root": str(PACKAGE_ROOT),
                "source_archive": pin_file(source_archive),
            },
        )

    def _record_setup_timing(self, setup_started: float, setup_utc: str) -> None:
        """Open the timing log and record the completed setup.

        Args:
            setup_started: Setup start time from the monotonic clock, in seconds.
            setup_utc: Setup start time as an ISO 8601 UTC string.

        Raises:
            ValueError: The saved timing log contains invalid events.
        """
        self.timing = Timing(
            self.out / "timing-events.jsonl",
            resume=self.resume,
            attempt=self.attempt,
            heartbeat_seconds=1.0,
            earlier_attempts=(
                path.name
                for path in self.attempt_dir.parent.iterdir()
                if path.is_dir() and path != self.attempt_dir
            ),
        )
        setup_finished = time.monotonic()
        token = uuid.uuid4().hex
        self.timing.event(
            {
                "event": "start",
                "token": token,
                "id": "setup/source-validation",
                "group": "setup",
                "monotonic_seconds": setup_started,
                "utc": setup_utc,
            }
        )
        self.timing.event(
            {
                "event": "complete",
                "token": token,
                "id": "setup/source-validation",
                "group": "setup",
                "start_monotonic_seconds": setup_started,
                "monotonic_seconds": setup_finished,
            }
        )
        self.timing.mark_complete("setup")
        write_json(self.attempt_dir / "setup-timing.json", self.timing.anchor())

    def physical_attempts(self) -> list[dict[str, Any]]:
        """Read complete events from the physical build's timing log.

        Returns:
            Event dictionaries in file order. Stop at an incomplete or invalid
            entry, and return an empty list when the log is absent.
        """
        path = self.out / "physical/processing-events.jsonl"
        if not path.exists():
            return []
        # Only newline-terminated, complete durable records can supply timing.
        lines = path.read_bytes().splitlines(keepends=True)
        records = []
        for line in lines:
            if not line.endswith(b"\n"):
                break
            try:
                records.append(json.loads(line))
            except ValueError:
                break
        return records

    def record_physical_invocation(
        self, measurement: dict[str, Any], previous: list[dict[str, Any]]
    ) -> None:
        """Record how much of a physical build call was processing or verification.

        Args:
            measurement: Start and end times for the call, from the timing journal.
            previous: Physical build events recorded before the call.

        Raises:
            ValueError: A recorded duration is invalid or the total exceeds
                the measured call time.
        """
        before = {
            record.get("attempt")
            for record in previous
            if record.get("event") == "attempt_start"
        }
        after = self.physical_attempts()
        started = {
            record.get("attempt")
            for record in after
            if record.get("event") == "attempt_start"
        } - before
        ends = [
            record
            for record in after
            if record.get("event") == "attempt_end" and record.get("attempt") in started
        ]
        elapsed = (
            measurement["end_monotonic_seconds"] - measurement["monotonic_seconds"]
        )
        if not started:
            # A completed producer verification (or rejected preflight) did not
            # start another producer attempt. Its entire invocation is validation.
            self.timing.event(
                {
                    "event": "physical-command-overhead",
                    "id": "physical",
                    "seconds": elapsed,
                }
            )
        elif len(started) == len(ends) == 1:
            processing = ends[0].get("processing_elapsed_seconds")
            downloads = ends[0].get("source_download_elapsed_seconds")
            if (
                not all(
                    type(value) in (int, float)
                    and math.isfinite(cast(float, value))
                    and cast(float, value) >= 0
                    for value in (processing, downloads)
                )
                or cast(float, processing) + cast(float, downloads) > elapsed
            ):
                raise ValueError("invalid physical invocation timing")
            self.timing.event(
                {
                    "event": "physical-command-overhead",
                    "id": "physical",
                    "seconds": elapsed
                    - cast(float, processing)
                    - cast(float, downloads),
                }
            )
            self.timing.event(
                {
                    "event": "physical-invocation-processing",
                    "id": "physical",
                    "seconds": processing,
                }
            )
        # A killed producer with no durable attempt end supplies no exact tail.
        # Its own report will retain timing_complete=false after shard resume.

    def close(self) -> None:
        """Close the timing journal and release the run lock."""
        self.timing.close()
        self.run_lock.close()

    def cancel(self) -> None:
        """Signal the current workers to stop at their next cancellation check."""
        self.cancelled.set()

    def physical(self) -> Path:
        """Build, resume, or reuse the physical land and water grid.

        Returns:
            Directory containing the physical row-run files and report.
        """
        request = self.out / "physical-build-config.json"
        data = json_bytes(self.physical_config)
        if request.exists():
            if request.read_bytes() != data:
                raise ValueError("saved physical build configuration changed")
        else:
            write_bytes_atomic(request, data)
        request_pin = FilePin(
            path=str(request), sha256=hashlib.sha256(data).hexdigest()
        )
        if self.physical_reuse is not None:
            verify_pins(self.physical_reuse["pins"])
            return Path(self.physical_reuse["source_run"]) / "physical" / "physical"
        marker = self.out / "physical/pipeline-identity.json"
        previous = self.physical_attempts()
        measurement = None
        try:
            with (
                stage_context(self.cancelled),
                self.timing.measure(
                    "physical", "physical-invocation", kind="command"
                ) as measurement,
            ):
                self.checkpoints.run_function(
                    "physical",
                    "physical",
                    partial(
                        physical_build.build,
                        self.physical_config,
                        self.grid,
                        request_pin,
                        self.out / 'physical',
                        resume=marker.is_file(),
                    ),
                    timing=self.timing,
                    inputs=[request_pin],
                    outputs=[self.out / "physical"],
                    resume_marker=marker,
                )
        finally:
            # A normal return always has an end time. Only an interruption
            # or timing error can bypass accounting and propagate an exception.
            if (
                measurement and "end_monotonic_seconds" in measurement
            ):  # pragma: no branch
                self.record_physical_invocation(measurement, previous)
        return self.out / "physical" / "physical"

    def divide(self, physical: Path) -> Path:
        """Assign cells to geographic entities using the saved rules.

        Args:
            physical: Directory with the physical row-run grid.

        Returns:
            Directory with the completed ownership row-run grid.
        """
        previous = None
        if self.reuse_from is not None and not self.recompute_division:
            division = self.reuse_from / "division"
            if (division / "report.json").is_file():
                previous = division
        operation = HierarchyDivision(
            self.selection["geography"],
            self.grid,
            physical,
            self.out / "division",
            dict(self.cfg),
            compiled_divisions=self.compiled_divisions,
            reuse=previous,
            executor=StageExecutor(self.checkpoints, self.timing),
        )
        return Path(operation.run()["directory"])

    def package(self, physical: Path, ownership: Path) -> Path:
        """Encode each cell's owner and land or water class as a map code.

        Args:
            physical: Directory containing the physical grid.
            ownership: Directory containing the ownership grid.

        Returns:
            Directory containing the final row-run files and count report.
        """
        output = self.out / "final"
        inputs = [pin_file(self.out / "input-selection.json")]
        inputs += [
            pin_file(root / name)
            for root in (physical, ownership)
            for name in ("rows.u32le", "runs.u32le")
        ]
        result = self.checkpoints.run_function(
            "encode",
            "package",
            partial(
                encode,
                self.grid,
                physical,
                ownership,
                self.selection['geography']['category_bindings'],
                output,
            ),
            timing=self.timing,
            inputs=inputs,
            outputs=[output],
        )
        return Path(result["directory"])

    def run(self) -> dict[str, Any]:
        """Run the build through physical grid, ownership, and final encoding.

        Write a success or failure report and close the run even if a stage fails.

        Returns:
            Build report with pinned inputs and outputs and stage timings.
        """
        physical = None
        try:
            if (self.out / "report.json").exists():
                report = read_json(self.out / "report.json")
                verify_pins(report["final"].values())
                verify_anchor(report["timing_anchor"], self.timing.path)
                return report
            with self.timing.measure("physical", "stage-total"):
                physical = self.physical()
            physical_inputs = (
                self.physical_reuse["pins"]
                if self.physical_reuse is not None
                else [
                    pin_file(physical / name)
                    for name in ("rows.u32le", "runs.u32le", "report.json")
                ]
            )
            physical_report = self.physical_reuse or read_json(
                self.out / "physical/report.json"
            )
            self.timing.mark_complete("physical", physical_report=physical_report)
            with (
                stage_context(self.cancelled),
                self.timing.measure("division", "stage-total"),
            ):
                ownership = self.divide(physical)
            self.timing.mark_complete("division")
            with self.timing.measure("package", "stage-total"):
                final = self.package(physical, ownership)
            self.timing.mark_complete("package")
            with self.timing.measure("verification", "stage-total"):
                verify_pins(physical_inputs)
                if sha256_file(self.saved_config) != self.config_pin["sha256"]:
                    raise ValueError(
                        "saved build configuration changed during pipeline"
                    )
                final_pins = {
                    key: pin_file(final / name)
                    for key, name in [
                        ("rows", "rows.u32le"),
                        ("runs", "runs.u32le"),
                        ("report", "report.json"),
                    ]
                }
            self.timing.mark_complete("verification")
            stages = self.timing.summary(physical_report)
            if not all(stage["outputs_complete"] for stage in stages.values()):
                raise ValueError("all stage outputs must be complete")
            result = {
                "schema": "worldatlas-end-to-end-report-v2",
                "status": "complete",
                "request": self.config_pin,
                "runner": pin_file(__file__),
                "original_run_identity": pin_file(self.out / "run-identity.json"),
                "stages": stages,
                "timing_complete": all(
                    stage["timing_complete"] for stage in stages.values()
                ),
                "timing_anchor": self.timing.anchor(),
                "physical_directory": str(physical),
                "physical_outputs": physical_inputs,
                "final": final_pins,
            }
            if self.physical_reuse is not None:
                result["physical_reuse"] = self.physical_reuse
            write_json(self.out / "report.json", result)
            return result
        except BaseException:
            report = self.out / "physical/report.json"
            try:
                physical_report = self.physical_reuse or (
                    read_json(report) if report.exists() else None
                )
            except (ValueError, OSError):
                physical_report = None
            write_json(
                self.out / "failure.json",
                {
                    "schema": "worldatlas-end-to-end-failure-v1",
                    "status": "incomplete",
                    "stages": self.timing.summary(physical_report),
                    "limitations": "Resume validates source and output pins. Code changes are recorded as provenance. Missing interrupted endpoints remain timing-incomplete; no downtime is added.",
                },
            )
            raise
        finally:
            self.close()


def main() -> None:
    """Read command-line options, run the map build, and print its report."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument(
        "output",
        type=Path,
        help="run directory inside the workspace; must exist only when resuming",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="workspace holding the shared inputs cache and run directories",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help=(
            "continue the saved run. Omit --selection, --divide, --reuse-from, "
            "and --recompute-division"
        ),
    )
    p.add_argument(
        "--selection",
        type=Path,
        help="start a new build from a saved geographic selection",
    )
    p.add_argument(
        "--divide",
        type=int,
        action="append",
        metavar="PARENT_ID",
        help=(
            "divide this parent and its ancestors; repeat to select several parents "
            "(default: divide every parent with saved rules)"
        ),
    )
    p.add_argument(
        "--reuse-from",
        type=Path,
        help=(
            "reuse the verified physical grid and all compatible geographic "
            "assignments unless --recompute-division is set"
        ),
    )
    p.add_argument(
        "--recompute-division",
        action="store_true",
        help=(
            "with --reuse-from, reuse only the physical grid and recalculate "
            "geographic assignments (off by default)"
        ),
    )
    a = p.parse_args()
    if a.recompute_division and a.reuse_from is None and not a.resume:
        p.error("--recompute-division requires --reuse-from")
    pipeline = Pipeline(
        a.config,
        a.output,
        resume=a.resume,
        work_dir=a.work_dir,
        reuse_from=a.reuse_from,
        recompute_division=a.recompute_division,
        divide=a.divide,
        selection=a.selection,
    )

    def stop(signum: int, frame: FrameType | None) -> None:
        """Request cancellation when the process receives a stop signal.

        Args:
            signum: Number of the received signal.
            frame: Python frame supplied by the signal handler.

        Raises:
            KeyboardInterrupt: Unwind the running build so it can save failure details.
        """
        pipeline.cancel()
        raise KeyboardInterrupt(f"interrupted by signal {signum}")

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(json.dumps(pipeline.run(), indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the pinned raw-source WorldAtlas pipeline through final composition."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import shutil
import signal
import sys
import threading
import time
import uuid
import zipfile
from collections.abc import Iterator
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Any, cast

import numpy
import psycopg
import pyarrow
import pyproj
import scipy
from osgeo import gdal
from pyproj import datadir

from worldatlas.map_build.core.comparison import compare
from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.division.contracts import CompiledRules
from worldatlas.map_build.division.encoding import encode
from worldatlas.map_build.division.hierarchy import HierarchyDivision
from worldatlas.map_build.execution.code_archive import capture_source, write_source
from worldatlas.map_build.execution.control import stage as stage_context
from worldatlas.map_build.execution.runtime import (
    Checkpoints,
    RunLock,
    Timing,
    code_identity,
    repository_identity,
    verify_anchor,
)
from worldatlas.map_build.inputs.releases import read_release_assets
from worldatlas.map_build.inputs.selection import (
    canonical_bytes,
    read_saved,
    read_selection,
)
from worldatlas.map_build.physical import build as physical_build
from worldatlas.map_releases.catalog import release_endpoint
from worldatlas.shared.files import (
    json_bytes,
    pin_file,
    read_json,
    sha256_file,
    verify_pins,
    write_json,
)
from worldatlas.source_assets.catalog import download_source

HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent


def runtime_identity() -> dict[str, Any]:
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


def catalog_references(value: object) -> Iterator[dict[str, Any]]:
    """Find R2 catalog references in a nested configuration.

    Args:
        value: A configuration value, which may contain lists and dictionaries.

    Yields:
        Each dictionary containing an "r2_source" selector, in traversal order.
    """
    if isinstance(value, list):
        for item in value:
            yield from catalog_references(item)
    elif isinstance(value, dict):
        if "r2_source" in value:
            yield value
        for key, item in value.items():
            if key != "r2_source":
                yield from catalog_references(item)


def catalog_keys(value: object) -> set[tuple[str, str | None]]:
    """Collect the distinct raw source IDs requested by a build.

    Args:
        value: Configuration containing dictionaries with "r2_source" selectors.

    Returns:
        Set of (source_id, version) pairs. Version is None for selectors
        without an explicit version.

    Raises:
        ValueError: A reference has invalid keys or mixes catalog selection
            with direct object metadata.
    """
    requested = set()
    for spec in catalog_references(value):
        identity = spec["r2_source"]
        if (
            not isinstance(identity, dict)
            or not {"source_id"} <= set(identity) <= {"source_id", "version"}
            or any(not isinstance(v, str) or not v.strip() for v in identity.values())
            or {
                "r2_bucket",
                "r2_key",
                "source_id",
                "version",
                "sha256",
                "size_bytes",
                "size",
            }
            & spec.keys()
        ):
            raise ValueError("invalid raw catalog reference")
        requested.add((identity["source_id"], identity.get("version")))
    return requested


def physical_reference(run: Path | str, sources: dict[str, Path]) -> dict[str, Any]:
    """Find reusable physical outputs for the same grid and raw inputs.

    Args:
        run: Earlier completed run directory.
        sources: Paths to the current land, water and raw source settings.

    Returns:
        Dictionary with the original run path and SHA-256 pins for its
        reports and physical grid files.

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
    identity = read_json(root / "pipeline-identity.json")
    report = read_json(root / "report.json")
    if report.get("status") != "candidate-only":
        raise ValueError("physical source run is incomplete")
    output = root / "physical"
    produced = read_json(output / "report.json")
    if Grid(**produced["grid"]) != Grid(**read_json(sources["land_config"])["grid"]):
        raise ValueError("physical reuse requires the same grid as the source run")
    for key, selected in [
        ("land_config", "land_config"),
        ("water_config", "water_config"),
        ("source_manifest", "raw_manifest"),
    ]:
        previous = Path(identity[key]["path"])
        if sha256_file(previous) != identity[key]["sha256"]:
            raise ValueError("physical source configuration changed: " + key)

        def data(value: object) -> Any:
            """Keep only settings that affect physical rasterization.

            Args:
                value: Value in a saved physical request.

            Returns:
                A copy without notes and legacy catalog version labels.
            """
            if isinstance(value, list):
                return [data(item) for item in value]
            if isinstance(value, dict):
                # Old catalog labels do not change pinned bytes or rasterization.
                return {
                    key: data(item)
                    for key, item in value.items()
                    if key != "selection_notes"
                    and not (key == "version" and "source_id" in value)
                }
            return value

        old_request, new_request = (
            data(read_json(previous)),
            data(read_json(sources[selected])),
        )
        if old_request != new_request:
            raise ValueError("physical input differs from the source run: " + key)
    pins = [
        pin_file(root / "report.json"),
        {
            "path": str(root / "pipeline-identity.json"),
            "sha256": report["pipeline_identity_sha256"],
        },
        {
            "path": str(output / "report.json"),
            "sha256": report["stage_reports"]["physical"]["sha256"],
        },
    ]
    pins.extend(
        {"path": str(output / name), "sha256": produced["output_sha256"][name]}
        for name in ("physical-dry.tif", "rows.u32le", "runs.u32le")
    )
    return {
        "schema": "worldatlas-physical-reuse-v1",
        "status": "reused",
        "source_run": str(run),
        "pins": pins,
    }


def _source_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Check which physical inputs the build configuration supplies.

    Args:
        config: Parsed build configuration.

    Returns:
        Source settings with inline coastline and inland-water inputs.

    Raises:
        ValueError: The source settings have missing or invalid entries.
    """
    sources = config.get("sources")
    if not isinstance(sources, dict):
        raise ValueError("sources must be a JSON object")
    required_sources = {"land_config", "inland_water"}
    allowed_sources = required_sources | {"reference_rows", "reference_runs"}
    missing = required_sources.difference(sources)
    if missing:
        raise ValueError(f"sources is missing {', '.join(sorted(missing))}")
    unexpected = set(sources).difference(allowed_sources)
    if unexpected:
        raise ValueError(f"sources has unexpected keys {', '.join(sorted(unexpected))}")
    coastline, water = sources["land_config"], sources["inland_water"]
    if not isinstance(coastline, dict) or not isinstance(coastline.get("land"), list):
        raise ValueError("land_config must provide its land datasets inline")
    if (
        not isinstance(water, dict)
        or not isinstance(water.get("rasterization"), dict)
        or not isinstance(water.get("files"), list)
    ):
        raise ValueError("inland_water must provide rasterization and files inline")
    return sources


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
        compare_release: str | None = None,
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
            compare_release: Release name to compare with the finished map.
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
        self.config_path = Path(config).resolve(strict=True)
        self.config_pin = pin_file(self.config_path)
        self.cfg = read_json(self.config_path)
        if self.cfg.get("schema") != "worldatlas-end-to-end-pipeline-v3":
            raise ValueError("unsupported end-to-end configuration")
        self.grid = Grid(**self.cfg["grid"])
        sources = _source_settings(self.cfg)

        self.resume = resume
        self._prepare_workspace(output, work_dir)
        saved_identity, compare_release = self._load_run_options(
            divide, compare_release, reuse_from, recompute_division
        )
        self.runtime = runtime_identity()

        # Save input paths and hashes so the builder can detect changes.
        self.source_pins = []
        # Reuse verified cloud files within this run without hashing them again.
        self.input_cache = {}
        # Track download start and end times separately from the rest of setup.
        self.acquisition_intervals = []
        self.selection, self.compiled_divisions = self._load_selection(
            sources, selection
        )
        self._prepare_source_files(sources)
        comparison_inputs = self._prepare_comparison(compare_release, saved_identity)
        self.collect_source_files()
        self.physical_reuse = (
            physical_reference(self.reuse_from, self.sources)
            if self.reuse_from is not None
            else None
        )
        if self.physical_reuse is not None:
            self.source_pins.extend(
                p for p in self.physical_reuse["pins"] if p not in self.source_pins
            )
        self._prepare_run_identity(compare_release, comparison_inputs)

        if not resume:
            self.out.mkdir(mode=0o700)
            write_json(self.out / "input-selection.json", self.selection)
        self.run_lock = RunLock(self.out / "run.lock")
        try:
            self._start_attempt(saved_identity)
            self._record_setup_timing(setup_started, setup_utc)
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
        if (
            (self.out.exists() != self.resume)
            or not self.out.parent.is_dir()
            or not self.out.is_relative_to(self.root)
            or self.config_path.is_relative_to(self.out)
        ):
            raise ValueError(
                "output must be inside --work-dir with an existing parent and "
                "exist only when resuming. Keep the configuration outside output."
            )

    def _load_run_options(
        self,
        divide: list[int] | None,
        compare_release: str | None,
        reuse_from: Path | str | None,
        recompute_division: bool,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Apply the requested options or restore them from an interrupted run.

        Args:
            divide: Parent entity IDs to divide, or None for the default.
            compare_release: Release name to compare against, if supplied.
            reuse_from: Earlier run to reuse, if supplied.
            recompute_division: Whether to reuse only the physical grid.

        Returns:
            Previous run identity and comparison release name. Each is None when absent.

        Raises:
            ValueError: The checkpoint is missing or the options are incompatible.
        """
        identity_path = self.out / "run-identity.json"
        if self.resume and not identity_path.is_file():
            raise ValueError(
                "run has no supported checkpoint identity; preserve it and start a fresh run"
            )
        saved_identity = read_json(identity_path) if self.resume else None
        reuse = Path(reuse_from).resolve() if reuse_from is not None else None
        if saved_identity is not None:
            if divide is not None and divide != saved_identity.get("divide"):
                raise ValueError("resume uses a different --divide selection")
            if compare_release is not None and compare_release != saved_identity.get(
                "compare_release"
            ):
                raise ValueError("resume uses a different --compare-release selection")
            divide = saved_identity.get("divide")
            compare_release = saved_identity.get("compare_release")
            saved_reuse = saved_identity["reuse_from"]
            saved_path = Path(saved_reuse) if saved_reuse is not None else None
            if reuse is not None and reuse != saved_path:
                raise ValueError("resume uses a different --reuse-from run")
            if recompute_division and not saved_identity["recompute_division"]:
                raise ValueError("resume uses a different --recompute-division setting")
            reuse = saved_path
            recompute_division = saved_identity["recompute_division"]
        if recompute_division and reuse is None:
            raise ValueError("--recompute-division requires --reuse-from")
        self.reuse_from = reuse
        self.recompute_division = recompute_division
        self.requested_parents = divide
        return saved_identity, compare_release

    def _load_selection(
        self, sources: dict[str, Any], selection: Path | str | None
    ) -> tuple[dict[str, Any], dict[int, CompiledRules]]:
        """Load the geographic records and prepare each parent's rules.

        Args:
            sources: Physical inputs that may refer to cataloged raw files.
            selection: Caller-supplied file with already saved geographic records.

        Returns:
            (selection, compiled_divisions). The selection contains the original
            records. The compiled divisions are keyed by parent ID.

        Raises:
            ValueError: A supplied selection differs from the saved run, or no
                database connection is configured for a new selection.
        """
        selected_path = self.out / "input-selection.json"
        if self.resume:
            saved, compiled = read_saved(selected_path)
            if selection is not None and canonical_bytes(
                read_json(selection)
            ) != canonical_bytes(saved):
                raise ValueError("resume uses a different saved geographic selection")
            return saved, compiled
        if selection is not None:
            return read_saved(selection)
        connection = os.environ.get("NEON_DATABASE_URL")
        if not connection:
            raise ValueError(
                "set NEON_DATABASE_URL to freeze working geography, or supply --selection"
            )
        with psycopg.connect(connection, connect_timeout=15) as database:
            references = {key[0] for key in catalog_keys(sources)}
            return read_selection(
                database, raw_sources=references, parents=self.requested_parents
            )

    def _prepare_source_files(self, sources: dict[str, Any]) -> None:
        """Resolve the physical inputs and any local reference files.

        Args:
            sources: Validated source settings from the build configuration.
        """
        resolved = self.resolve_raw_catalog(sources)
        coastline = resolved.pop("land_config")
        water = resolved.pop("inland_water")
        rasterization = water.pop("rasterization")
        for settings in (coastline, rasterization):
            settings["grid"] = vars(self.grid)
        # Each shard receives its own file and the shared rasterization settings.
        self.sources = {
            "land_config": self.save_source_document(self.coastline_request(coastline)),
            "water_config": self.save_source_document(rasterization),
            "raw_manifest": self.save_source_document(water),
        }
        for name, spec in resolved.items():
            if isinstance(spec, dict) and ("r2_bucket" in spec or "archive" in spec):
                self.sources[name] = self.cloud_file(spec)
            else:
                self.sources[name] = cast(Path, self.resolve_pins(spec))

    def _prepare_comparison(
        self, compare_release: str | None, saved_identity: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Prepare the pinned files for a comparison with a release.

        Args:
            compare_release: Release name, if the caller requested one.
            saved_identity: Saved run identity on resume.

        Returns:
            File pins keyed by input name, or None without a comparison release.

        Raises:
            ValueError: Comparison inputs are incomplete or use conflicting options.
        """
        comparison_inputs = None
        if compare_release is not None:
            if {"reference_rows", "reference_runs"} & self.sources.keys():
                raise ValueError(
                    "choose a published comparison release or local reference streams"
                )
            if saved_identity is not None:
                comparison_inputs = saved_identity.get("comparison_inputs")
                if comparison_inputs is None:
                    raise ValueError("resume is missing saved comparison files")
                self.sources.update(
                    cast(dict[str, Path], self.resolve_pins(comparison_inputs))
                )
            else:
                start = len(self.source_pins)
                files = self.release_reference(compare_release)
                self.sources.update(files)
                # Once decoded, the streams and mapping suffice for comparison.
                by_path = {p["path"]: p for p in self.source_pins}
                comparison_inputs = {
                    name: by_path[str(files[name])] for name in sorted(files)
                }
                self.source_pins[start:] = list(comparison_inputs.values())
        if ("reference_rows" in self.sources) != ("reference_runs" in self.sources):
            raise ValueError("both reference stream pins are required")
        return comparison_inputs

    def _prepare_run_identity(
        self,
        compare_release: str | None,
        comparison_inputs: dict[str, Any] | None,
    ) -> None:
        """Collect the inputs, code and options to save for the run.

        Args:
            compare_release: Release name used for comparison, if supplied.
            comparison_inputs: Pinned comparison files keyed by input name.
        """
        self.code = code_identity(PACKAGE_ROOT)
        self.repository = repository_identity(PACKAGE_ROOT)
        self.identity = {
            "schema": "worldatlas-end-to-end-run-identity-v1",
            "request": self.config_pin,
            "source_pins": self.source_pins,
            "code": self.code,
            "repository": self.repository,
            "scripts_root": str(PACKAGE_ROOT),
            "output": str(self.out),
            "runtime": self.runtime,
            "divide": self.requested_parents,
            "reuse_from": str(self.reuse_from) if self.reuse_from is not None else None,
            "recompute_division": self.recompute_division,
            "runtime_paths": {
                key: os.environ.get(key) for key in ("PROJ_DATA", "PROJ_LIB")
            },
        }
        self.identity["input_selection_sha256"] = hashlib.sha256(
            canonical_bytes(self.selection)
        ).hexdigest()
        if compare_release is not None:
            self.identity["compare_release"] = compare_release
        if comparison_inputs is not None:
            self.identity["comparison_inputs"] = comparison_inputs
        if self.physical_reuse is not None:
            self.identity["physical_reuse"] = self.physical_reuse

    def _start_attempt(self, saved_identity: dict[str, Any] | None) -> None:
        """Verify the run identity and save the code for this attempt.

        Args:
            saved_identity: Saved run identity on resume.

        Raises:
            ValueError: The saved identity, checkpoints or timing records changed.
        """
        if self.resume:
            saved = cast(dict[str, Any], saved_identity).copy()
            current = self.identity.copy()
            # A new attempt can use different code and installed libraries.
            for key in (
                "code",
                "repository",
                "runtime",
                "runtime_paths",
                "scripts_root",
            ):
                saved.pop(key, None)
                current.pop(key, None)
            if saved != current:
                raise ValueError(
                    "resume request, input selection or output identity changed"
                )
        else:
            write_json(self.out / "run-identity.json", self.identity)
        attempts = self.out / "attempts"
        attempts.mkdir(mode=0o700, exist_ok=self.resume)
        self.attempt = uuid.uuid4().hex
        self.attempt_dir = attempts / self.attempt
        self.attempt_dir.mkdir()
        source_archive = self.attempt_dir / "source-code.json.gz"
        write_source(source_archive, capture_source(PACKAGE_ROOT))
        write_json(
            self.attempt_dir / "producer.json",
            {
                "code": self.code,
                "repository": self.repository,
                "runtime": self.runtime,
                "scripts_root": str(PACKAGE_ROOT),
                "source_archive": pin_file(source_archive),
            },
        )
        self.checkpoints = Checkpoints(self.out / "checkpoints", self.attempt)
        self.checkpoints.verify_all()
        for marker in (self.out / "attempts").glob("*/setup-timing.json"):
            verify_anchor(read_json(marker), self.out / "timing-events.jsonl")

    def _record_setup_timing(self, setup_started: float, setup_utc: str) -> None:
        """Open the timing log and record the completed setup.

        Args:
            setup_started: Setup start time from the monotonic clock, in seconds.
            setup_utc: Setup start time as an ISO 8601 UTC string.

        Raises:
            ValueError: The saved build configuration changed.
        """
        self.timing = Timing(
            self.out / "timing-events.jsonl",
            resume=self.resume,
            attempt=self.attempt,
            heartbeat_seconds=1.0,
        )
        self.cancelled = threading.Event()
        saved_config = self.out / "build-config.json"
        if not self.resume:
            write_json(saved_config, self.cfg)
        elif saved_config.read_bytes() != json_bytes(self.cfg):
            raise ValueError("saved build configuration changed")
        self.checkpoints.preserve("failure", [self.out / "failure.json"])
        cursor = setup_started
        for start, end in [*self.acquisition_intervals, (time.monotonic(), None)]:
            token = uuid.uuid4().hex
            self.timing.event(
                {
                    "event": "start",
                    "token": token,
                    "id": "setup/source-validation",
                    "group": "setup",
                    "monotonic_seconds": cursor,
                    "utc": setup_utc,
                }
            )
            self.timing.event(
                {
                    "event": "complete",
                    "token": token,
                    "id": "setup/source-validation",
                    "group": "setup",
                    "start_monotonic_seconds": cursor,
                    "monotonic_seconds": start,
                }
            )
            cursor = end
        if self.resume:
            for earlier_attempt in (self.out / "attempts").iterdir():
                if (
                    earlier_attempt != self.attempt_dir
                    and not (earlier_attempt / "setup-timing.json").exists()
                ):
                    self.timing.event(
                        {
                            "event": "unmeasured-initialization",
                            "attempt": earlier_attempt.name,
                            "id": "setup/interrupted-initialization",
                            "group": "setup",
                        }
                    )
        self.timing.mark_complete("setup")
        write_json(self.attempt_dir / "setup-timing.json", self.timing.anchor())

    def resolve_raw_catalog(self, selections: dict[str, Any]) -> dict[str, Any]:
        """Expand raw source selectors using the frozen catalog.

        Args:
            selections: Inline source settings with optional "r2_source" selectors.

        Returns:
            Copy of the settings with selected object keys, byte sizes and hashes.

        Raises:
            ValueError: A selector is invalid or its catalog row is missing.
        """
        resolved = copy.deepcopy(selections)
        references = [
            (spec, "size" if name == "inland_water" else "size_bytes")
            for name, value in resolved.items()
            for spec in catalog_references(value)
        ]
        if not references:
            return resolved

        requested = catalog_keys(resolved)

        # Older snapshots can contain multiple captures under one source ID.
        catalog = {
            key: source
            for key in requested
            for source in self.selection["raw_sources"]
            if source["source_id"] == key[0]
            and (key[1] is None or source.get("version") == key[1])
        }
        if catalog.keys() != requested:
            raise ValueError("raw catalog is missing selected sources")
        for spec, size_field in references:
            identity = spec.pop("r2_source")
            source = catalog[identity["source_id"], identity.get("version")]
            spec.update(
                {
                    key: source[key]
                    for key in ("source_id", "r2_bucket", "r2_key", "sha256")
                }
            )
            spec[size_field] = source["size_bytes"]
        return resolved

    def cloud_file(self, spec: dict[str, Any], *, endpoint: str | None = None) -> Path:
        """Find or acquire a verified R2 object or ZIP member.

        Args:
            spec: Object location or archive and member, plus byte size and SHA-256.
            endpoint: R2 account URL. Defaults to the physical-source endpoint.

        Returns:
            Local path to the verified bytes in the work directory.

        Raises:
            ValueError: The reference is invalid or the bytes fail verification.
        """
        expected = spec.get("sha256")
        size = spec.get("size_bytes")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
            or type(size) is not int
            or size < 0
        ):
            raise ValueError("cloud inputs require explicit SHA-256 and byte size")
        archive_member: tuple[Path, str] | None = None
        if "archive" in spec:
            archive = self.cloud_file(spec["archive"], endpoint=endpoint)
            member = spec["member"]
            if not isinstance(member, str):
                raise ValueError("unsafe ZIP member")
            rel = Path(member)
            if (
                not member
                or rel.is_absolute()
                or "\\" in member
                or any(part in ("", ".", "..") for part in member.split("/"))
            ):
                raise ValueError("unsafe ZIP member")
            path = self.root / "inputs" / spec["archive"]["sha256"] / rel
            identity = ("member", str(archive), member, expected, size)
            archive_member = archive, member
        else:
            bucket, key = spec.get("r2_bucket"), spec.get("r2_key")
            if (
                not isinstance(bucket, str)
                or not bucket
                or not isinstance(key, str)
                or not key
                or key.endswith("/")
                or "\\" in key
                or any(p in ("", ".", "..") for p in key.split("/"))
            ):
                raise ValueError("invalid pinned R2 location")
            path = self.root / "inputs" / expected / Path(key).name
            identity = ("r2", bucket, key, expected, size)
        if identity in self.input_cache:
            return self.input_cache[identity]
        path = path.resolve()
        if not path.is_relative_to(self.root) or path.is_relative_to(self.out):
            raise ValueError("cloud input overlaps output or escapes work directory")
        if path.exists():
            if (
                not path.is_file()
                or path.stat().st_size != size
                or sha256_file(path) != expected
            ):
                raise ValueError(
                    "cached cloud input size/SHA-256 mismatch: " + str(path)
                )
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if archive_member is not None:
                archive, member = archive_member
                partial = path.with_name(
                    path.name + "." + uuid.uuid4().hex + ".partial"
                )
                try:
                    with zipfile.ZipFile(archive) as packed:
                        members = [
                            item
                            for item in packed.infolist()
                            if item.filename == member
                        ]
                        if (
                            len(members) != 1
                            or members[0].is_dir()
                            or ((members[0].external_attr >> 16) & 0o170000) == 0o120000
                        ):
                            raise ValueError("ZIP member must be one regular file")
                        with packed.open(members[0]) as src, partial.open("xb") as dst:
                            shutil.copyfileobj(src, dst, 1 << 20)
                    if (
                        partial.stat().st_size != size
                        or sha256_file(partial) != expected
                    ):
                        raise ValueError(
                            "cloud input size/SHA-256 mismatch: " + str(path)
                        )
                    try:
                        os.link(partial, path)
                    except FileExistsError:
                        if (
                            not path.is_file()
                            or path.stat().st_size != size
                            or sha256_file(path) != expected
                        ):
                            raise ValueError("concurrent cloud input changed") from None
                finally:
                    partial.unlink(missing_ok=True)
            else:
                if endpoint is None:
                    staging = self.cfg.get("physical_controls", {}).get(
                        "source_staging", {}
                    )
                    endpoint = staging.get("endpoint_url")
                transfer = {}
                try:
                    with closing(physical_build.make_r2_client(endpoint)) as client:
                        download_source(
                            client,
                            spec,
                            self.root / "inputs",
                            filename=path.name,
                            timing=transfer,
                        )
                except ValueError as exc:
                    raise ValueError(
                        "cloud input size/SHA-256 mismatch: " + str(path)
                    ) from exc
                finally:
                    self.acquisition_intervals.extend(
                        transfer.get("download_intervals", [])
                    )
        result = pin_file(path)
        if result not in self.source_pins:
            self.source_pins.append(result)
        self.input_cache[identity] = path
        return path

    def coastline_request(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Prepare coastline rasterization settings using cached local files.

        Args:
            settings: Coastline settings with selected datasets and their file pins.

        Returns:
            Copy of the settings with cloud references replaced by local paths
            and file pins.
        """
        layers = []
        for layer in settings["land"]:
            dataset = layer["dataset"]
            if isinstance(dataset, dict):
                dataset = str(self.cloud_file(dataset))
            files = [
                dict(pin_file(self.cloud_file(spec)), size_bytes=spec["size_bytes"])
                if "r2_bucket" in spec or "archive" in spec
                else spec
                for spec in layer["files"]
            ]
            layers.append(dict(layer, dataset=dataset, files=files))
        return dict(settings, land=layers)

    def save_source_document(self, document: dict[str, Any]) -> Path:
        """Cache a generated input document and record its SHA-256.

        Args:
            document: Build input to write as JSON.

        Returns:
            Local path whose filename includes the digest of the JSON bytes.

        Raises:
            ValueError: The path overlaps the run or the cached bytes differ.
        """
        data = json_bytes(document)
        path = (
            self.root / "inputs" / (hashlib.sha256(data).hexdigest() + ".json")
        ).resolve()
        if not path.is_relative_to(self.root) or path.is_relative_to(self.out):
            raise ValueError("generated input overlaps output")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            try:
                write_json(path, document)
            except FileExistsError:
                # Another build may have published this same cache entry.
                pass
        if path.read_bytes() != data:
            raise ValueError("generated input changed")
        result = pin_file(path)
        if result not in self.source_pins:
            self.source_pins.append(result)
        return path

    def release_reference(self, version: str) -> dict[str, Path]:
        """Cache and verify a published map's comparison files.

        Args:
            version: Official version or numbered preview.

        Returns:
            Paths keyed by "reference_rows", "reference_runs", and, when
            available, "reference_config". The map streams are decompressed.
        """
        streams, config = read_release_assets(version)
        endpoint = release_endpoint()
        digest = hashlib.sha256(json_bytes(streams)).hexdigest()
        directory = (self.root / "inputs" / ("release-" + digest)).resolve()
        if not directory.is_relative_to(self.root) or directory.is_relative_to(
            self.out
        ):
            raise ValueError(
                "release reference overlaps output or escapes the work directory"
            )
        directory.mkdir(parents=True, exist_ok=True)
        reference = {}
        for stream, bucket, key, size, stored_hash, decoded_hash in streams:
            path = directory / (stream + ".u32le")
            compressed = self.cloud_file(
                {
                    "r2_bucket": bucket,
                    "r2_key": key,
                    "size_bytes": size,
                    "sha256": stored_hash,
                },
                endpoint=endpoint,
            )
            if not path.exists():
                partial = path.with_name(
                    path.name + "." + uuid.uuid4().hex + ".partial"
                )
                try:
                    with gzip.open(compressed, "rb") as src, partial.open("xb") as dst:
                        shutil.copyfileobj(src, dst, 1 << 20)
                    if sha256_file(partial) != decoded_hash:
                        raise ValueError("decoded reference stream hash mismatch")
                    try:
                        os.link(partial, path)
                    except FileExistsError:
                        pass
                finally:
                    partial.unlink(missing_ok=True)
            reference["reference_" + stream] = cast(
                Path, self.resolve_pins({"path": str(path), "sha256": decoded_hash})
            )
        if config is not None:
            reference["reference_config"] = self.cloud_file(config, endpoint=endpoint)
        return reference

    def resolve_pins(self, value: dict[str, Any]) -> Path | dict[str, Any]:
        """Verify a file pin or a tree of file pins.

        Args:
            value: A {"path": ..., "sha256": ...} pin or a dictionary of pins.

        Returns:
            Resolved file path or a dictionary with the same keys and resolved leaves.

        Raises:
            ValueError: A pin is invalid, outside the input directory, or has a
                different SHA-256.
        """
        if isinstance(value, dict) and set(value) == {"path", "sha256"}:
            path = Path(value["path"])
            if not path.is_absolute():
                path = self.config_path.parent / path
            path = path.resolve(strict=True)
            if (
                not path.is_relative_to(self.root)
                or path.is_relative_to(self.out)
                or sha256_file(path) != value["sha256"]
            ):
                raise ValueError(
                    f"source pin mismatch or outside the work directory: {path}"
                )
            self.source_pins.append({"path": str(path), "sha256": value["sha256"]})
            return path
        if isinstance(value, dict):
            return {key: self.resolve_pins(item) for key, item in value.items()}
        raise ValueError("all source selections must be explicit path/SHA-256 pins")

    def collect_source_files(self) -> None:
        """Verify local coastline files and record their pins for this run.

        Raises:
            ValueError: A file is outside the work directory or has changed.
        """
        for layer in read_json(self.sources["land_config"]).get("land", []):
            for spec in layer["files"]:
                expected = pin_file(spec["path"])
                if expected["sha256"] != spec["sha256"] or not Path(
                    expected["path"]
                ).is_relative_to(self.root):
                    raise ValueError(
                        "selected source file differs or is outside the work directory"
                    )
                if expected not in self.source_pins:
                    self.source_pins.append(expected)

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
            Directory containing the physical raster, row-run files and report.
        """
        if self.physical_reuse is not None:
            verify_pins(self.physical_reuse["pins"])
            return Path(self.physical_reuse["source_run"]) / "physical" / "physical"
        cfg = {
            "schema": "raw-physical-pipeline-v1",
            "selection_notes": self.cfg["selection_notes"],
            **self.cfg.get("physical_controls", {}),
            **{
                key: pin_file(self.sources[source])
                for key, source in [
                    ("land_config", "land_config"),
                    ("water_config", "water_config"),
                    ("source_manifest", "raw_manifest"),
                ]
            },
        }
        request = self.out / "physical-build-config.json"
        if request.exists():
            if request.read_bytes() != json_bytes(cfg):
                raise ValueError("saved physical build configuration changed")
        else:
            write_json(request, cfg)
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
                    physical_build.run,
                    (request, self.out / "physical"),
                    kwargs={"resume": marker.is_file()},
                    timing=self.timing,
                    inputs=[pin_file(request)],
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
            Grid(**self.cfg["grid"]),
            physical,
            self.out / "division",
            self.cfg,
            compiled_divisions=self.compiled_divisions,
            requested=self.requested_parents,
            reuse=previous,
            checkpoints=self.checkpoints,
            timing=self.timing,
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
            encode,
            (
                Grid(**self.cfg["grid"]),
                physical,
                ownership,
                self.selection["geography"]["category_bindings"],
                output,
            ),
            timing=self.timing,
            inputs=inputs,
            outputs=[output],
        )
        return Path(result["directory"])

    def compare(self, final: Path, physical: Path) -> dict[str, str] | None:
        """Record changed assignments against the chosen reference grid.

        Args:
            final: Directory containing the final row-run grid.
            physical: Physical grid directory, used for its dimensions.

        Returns:
            Comparison report's path and SHA-256, or None if no reference was selected.

        Raises:
            ValueError: The paired reference streams do not use the expected paths.
        """
        rows = self.sources.get("reference_rows")
        if rows is None:
            return None
        runs = self.sources["reference_runs"]
        if (
            rows.name != "rows.u32le"
            or runs.name != "runs.u32le"
            or rows.parent != runs.parent
        ):
            raise ValueError(
                "reference must use rows.u32le and runs.u32le in one directory"
            )
        grid = Grid(**read_json(physical / "report.json")["grid"])
        inputs = [
            pin_file(root / name)
            for root in (final, rows.parent)
            for name in ("rows.u32le", "runs.u32le")
        ]
        bindings = {}
        if config := self.sources.get("reference_config"):
            inputs += [pin_file(config), pin_file(self.out / "input-selection.json")]
            bindings = dict(
                reference_bindings=[
                    dict(
                        code=category["id"],
                        entity_id=category["entity_id"],
                        physical_class=category["physical_class"],
                    )
                    for category in read_json(config)["categories"]
                ],
                candidate_bindings=self.selection["geography"]["category_bindings"],
            )
        self.checkpoints.run_function(
            "compare",
            "verification",
            compare,
            (
                final,
                rows.parent,
                grid,
                self.out / "comparison",
                {"rows.u32le": sha256_file(rows), "runs.u32le": sha256_file(runs)},
            ),
            timing=self.timing,
            inputs=inputs,
            outputs=[self.out / "comparison"],
            kwargs=bindings,
        )
        return pin_file(self.out / "comparison" / "report.json")

    def run(self) -> dict[str, Any]:
        """Run the build through physical grid, ownership, and final encoding.

        Write a success or failure report and close the run even if a stage fails.

        Returns:
            Build report with pinned inputs and outputs, stage timings, and
            an optional comparison report pin.
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
            physical_inputs = [
                pin_file(physical / name)
                for name in ("rows.u32le", "runs.u32le", "report.json")
            ]
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
                comparison = self.compare(final, physical)
                verify_pins(physical_inputs)
                if pin_file(self.config_path) != self.config_pin or any(
                    pin_file(p["path"]) != p for p in self.source_pins
                ):
                    raise ValueError("source configuration changed during pipeline")
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
                "comparison": comparison,
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
        help="validate and continue the same checkpoint-enabled run",
    )
    p.add_argument(
        "--selection", type=Path, help="replay a saved complete geographic selection"
    )
    p.add_argument(
        "--compare-release",
        help="compare with an official version or numbered candidate in Neon",
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
        compare_release=a.compare_release,
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

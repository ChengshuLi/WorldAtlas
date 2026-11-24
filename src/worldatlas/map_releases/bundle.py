"""Build the local release files from a completed map and viewer assets."""

import gzip
import hashlib
import json
import mimetypes
import re
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.execution.code_archive import read_source
from worldatlas.map_build.inputs.configuration import BuildConfiguration
from worldatlas.map_build.inputs.selection import validate_map_code_bindings
from worldatlas.map_build.inputs.selection_types import (
    BuildSelection,
    GeographicSelection,
)
from worldatlas.map_releases.catalog import HOMEPAGE, release_prefix, version
from worldatlas.map_releases.inputs import (
    FILENAME,
    validate_replay_sources,
    write_inputs,
)
from worldatlas.shared.files import (
    FilePin,
    JSONValue,
    compact_json_bytes,
    json_bytes,
    read_json,
    sha256_file,
    verify_pins,
)

STREAM_FILES = {"rows": "rows.u32le", "runs": "runs.u32le"}
LEGEND_FILE = "legend/entities.json"
# Use Python's built-in media types to keep manifests stable across machines.
MEDIA_TYPES = mimetypes.MimeTypes()


def _read_pinned_json(path: Path, digest: str, error: str) -> dict[str, Any]:
    """Check the exact JSON bytes that will be read.

    Args:
        path: Saved JSON file.
        digest: SHA-256 from the completed build report.
        error: Message to show when the checksum differs.

    Returns:
        The saved JSON object.

    Raises:
        ValueError: The checksum differs or the JSON cannot be read.
    """
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(error)
    return json.loads(raw)


def _read_build(
    run: Path,
) -> tuple[dict[str, Any], dict[str, Any], BuildConfiguration, BuildSelection]:
    """Read the completed build report and verify the saved inputs it names.

    Args:
        run: Resolved directory containing the build reports and inputs.

    Returns:
        (report, run identity, configuration, frozen selection).

    Raises:
        ValueError: The build is incomplete or its inputs differ from the report.
    """
    report = read_json(run / "report.json")
    if (
        report.get("schema") != "worldatlas-end-to-end-report-v2"
        or report.get("status") != "complete"
    ):
        raise ValueError("a completed map build is required")

    identity_path = run / "run-identity.json"
    identity_pin = report["original_run_identity"]
    if identity_pin["path"] != str(identity_path.resolve()):
        raise ValueError("build identity does not match the report")
    identity = _read_pinned_json(
        identity_path,
        identity_pin["sha256"],
        "build identity does not match the report",
    )
    request = report["request"]
    if request != identity["request"]:
        raise ValueError("build configuration does not match the run")
    # The completed build already parsed these exact bytes as BuildConfiguration.
    configuration = cast(
        BuildConfiguration,
        _read_pinned_json(
            run / "build-config.json",
            request["sha256"],
            "build configuration checksum does not match the report",
        ),
    )

    selection: BuildSelection = read_json(run / "input-selection.json")
    if (
        hashlib.sha256(compact_json_bytes(selection)).hexdigest()
        != identity["input_selection_sha256"]
    ):
        raise ValueError("the saved geographic selection changed after the build")
    validate_replay_sources(configuration, selection)
    return report, identity, configuration, selection


def _read_final_grid(
    final: Path, pins: Mapping[str, FilePin], geography: GeographicSelection
) -> tuple[Grid, dict[str, Any]]:
    """Check the final grid files and the counts that will go into the legend.

    Args:
        final: The build's final grid directory.
        pins: Saved file paths and checksums for the final grid.
        geography: Saved entities and category bindings.

    Returns:
        (grid, report), where the report has counts by map code and the run count.

    Raises:
        ValueError: A path, checksum, or count differs from the saved build.
    """
    for key, filename in {**STREAM_FILES, "report": "report.json"}.items():
        if Path(pins[key]["path"]).resolve() != final / filename:
            raise ValueError(
                "expected final outputs together inside the build directory"
            )
    summary = _read_pinned_json(
        final / "report.json",
        pins["report"]["sha256"],
        "final map report checksum does not match the completed build",
    )
    grid = Grid(**summary["grid"])
    counts = summary["counts"]
    if sum(counts.values()) != grid.width * grid.height:
        raise ValueError("the output counts must cover the entire grid")
    validate_map_code_bindings(geography)
    known_codes = {str(binding["code"]) for binding in geography["category_bindings"]}
    if any(count and code not in known_codes for code, count in counts.items()):
        raise ValueError("geographic snapshot is missing categories used by the map")
    return grid, summary


def _read_attempts(
    run: Path,
) -> tuple[list[dict[str, JSONValue]], dict[str, dict[str, JSONValue]]]:
    """Collect each attempt's record and store identical code snapshots once.

    Args:
        run: Completed build directory.

    Returns:
        (attempt records, code snapshots keyed by their SHA-256).

    Raises:
        ValueError: An attempt's saved code is missing or differs from its pin.
    """
    attempts = []
    snapshots = {}
    for producer in sorted((run / "attempts").glob("*/producer.json")):
        attempt_id = producer.parent.name
        attempt = read_json(producer)
        source = attempt.get("source_archive")
        if not source:
            raise ValueError(
                f"build attempt {attempt_id} has no captured code snapshot"
            )
        if (
            Path(source["path"]).resolve()
            != (producer.parent / "source-code.json.gz").resolve()
        ):
            raise ValueError("source archive must be inside its build attempt")
        verify_pins([source])
        attempts.append(dict(attempt, attempt_id=attempt_id))
        if source["sha256"] not in snapshots:
            snapshots[source["sha256"]] = read_source(Path(source["path"]))
    if not attempts:
        raise ValueError("completed build has no captured code snapshot")
    return attempts, snapshots


def _copy_viewer(viewer: Path, bundle: Path, prefix: str) -> None:
    """Copy viewer files and make their relative URLs point into this release.

    Args:
        viewer: Directory containing the website source files.
        bundle: Local release output directory.
        prefix: Release folder key with its trailing slash.

    Raises:
        ValueError: A viewer path is unsafe or its homepage already has a base URL.
    """
    for source in sorted(viewer.rglob("*")):
        relative = source.relative_to(viewer)
        if source.is_symlink() or not all(
            re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*", part)
            for part in relative.parts
        ):
            raise ValueError(f"invalid viewer asset path: {relative}")
        if source.is_dir() or source.suffix == ".md" or relative.as_posix() == HOMEPAGE:
            continue
        destination = bundle / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)

    html = (viewer / HOMEPAGE).read_text()
    if html.count("<head>") != 1 or re.search(r"<base\b", html, re.I):
        raise ValueError("the viewer homepage must have a single head and no base URL")
    # The same HTML serves the candidate URL and the site homepage.
    (bundle / HOMEPAGE).write_text(
        html.replace("<head>", f'<head><base href="/{prefix}">', 1)
    )


def _compress_grid(
    final: Path,
    bundle: Path,
    pins: Mapping[str, FilePin],
    height: int,
    run_count: int,
) -> tuple[str, dict[str, str]]:
    """Verify and compress both grid files in one pass over their bytes.

    Args:
        final: Directory containing the uncompressed map streams.
        bundle: Local release output directory.
        pins: Expected SHA-256 for each original file.
        height: Number of grid rows.
        run_count: Total number of encoded runs.

    Returns:
        (combined SHA-256, SHA-256 by stream name), all for the uncompressed bytes.

    Raises:
        ValueError: The stream size or checksum differs from the completed build.
    """
    # Each row offset takes 4 bytes. Each run stores an end column and map code.
    sizes = {"rows": 4 * (height + 1), "runs": 8 * run_count}
    combined = hashlib.sha256()
    decoded = {}
    for stream, filename in STREAM_FILES.items():
        checksum = hashlib.sha256()
        size = 0
        with (
            (final / filename).open("rb") as source,
            (bundle / f"{filename}.gz").open("xb") as destination,
            gzip.GzipFile(
                filename="", fileobj=destination, mode="wb", mtime=0
            ) as compressed,
        ):
            while chunk := source.read(4 << 20):
                size += len(chunk)
                checksum.update(chunk)
                combined.update(chunk)
                compressed.write(chunk)
        digest = checksum.hexdigest()
        if size != sizes[stream] or digest != pins[stream]["sha256"]:
            raise ValueError(
                f"{stream} size or checksum differs from the completed build"
            )
        decoded[stream] = digest
    return combined.hexdigest(), decoded


def _write_viewer_data(
    bundle: Path,
    geography: GeographicSelection,
    summary: dict[str, Any],
    grid: Grid,
    *,
    map_version: str,
    water_edition: str | None,
    combined: str,
    decoded: dict[str, str],
) -> None:
    """Write the viewer's code lookup and legend from the saved bindings and counts.

    Args:
        bundle: Local release folder containing the copied viewer settings.
        geography: Saved entities, colors, and map-code bindings.
        summary: Final grid report with counts by map code and the number of runs.
        grid: Final dimensions and cell size.
        map_version: Display version such as v8.4.
        water_edition: Source edition to display, when recorded.
        combined: SHA-256 over both uncompressed streams in rows-first order.
        decoded: SHA-256 for each uncompressed stream.

    Raises:
        ValueError: A land entity has no color.
    """
    counts = summary["counts"]
    bindings = sorted(
        geography["category_bindings"], key=lambda binding: binding["code"]
    )
    config = bundle / "config.json"
    viewer = read_json(config)
    if water_edition:
        viewer["inland_water_release"] = water_edition
    entities = {entity["id"]: entity for entity in geography["entities"]}
    categories = []
    legend = {}
    for binding in bindings:
        code, entity_id, physical_class = (
            binding["code"],
            binding["entity_id"],
            binding["physical_class"],
        )
        entity = entities[entity_id]
        categories.append(
            {"id": code, "entity_id": entity_id, "physical_class": physical_class}
        )
        # Land and water have separate codes but share a legend row.
        entry = legend.setdefault(
            entity_id,
            {
                "id": entity_id,
                "name": entity["name"],
                "color": viewer["water_rgb"],
                "count": 0,
            },
        )
        entry["count"] += counts.get(str(code), 0)
        if physical_class == "land":
            color = entity.get("color_rgb")
            if color is None:
                raise ValueError(
                    f"Saved colors are missing for land entities [{entity_id}]"
                )
            entry["color"] = list(bytes.fromhex(color[1:]))

    legend_path = bundle / LEGEND_FILE
    legend_path.parent.mkdir(exist_ok=True)
    legend_path.write_bytes(json_bytes(list(legend.values())))
    streams: dict[str, JSONValue] = {"run_count": summary["run_count"]}
    for stream, filename in STREAM_FILES.items():
        streams[stream] = f"{filename}.gz"
        streams[f"{stream}_sha256"] = decoded[stream]
    viewer.update(
        width=grid.width,
        height=grid.height,
        step=grid.step,
        map_version=map_version,
        local_grid=streams,
        combined_sha256=combined,
        legend=LEGEND_FILE,
        categories=categories,
    )
    config.write_bytes(json_bytes(viewer))


def _file_manifest(bundle: Path, prefix: str) -> dict[str, dict[str, JSONValue]]:
    """Pin the files ready to upload.

    Args:
        bundle: Local release folder.
        prefix: Release folder key with its trailing slash.

    Returns:
        Map from relative filenames to R2 keys, checksums, sizes and content types.
    """
    objects = {}
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            name = path.relative_to(bundle).as_posix()
            objects[name] = {
                "r2_key": prefix + name,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "content_type": (
                    "application/gzip"
                    if path.suffix == ".gz"
                    else MEDIA_TYPES.guess_file_type(path)[0]
                    or "application/octet-stream"
                ),
            }
    return objects


def build_bundle(
    candidate: str, run: Path, viewer: Path, bundle: Path
) -> dict[str, Any]:
    """Package a completed build and its captured inputs in a local directory.

    Args:
        candidate: Numbered release ID used in asset URLs.
        run: Directory containing the completed build and its frozen inputs.
        viewer: Directory containing the unbundled website files.
        bundle: Empty directory that will receive the release files.

    Returns:
        The release manifest with file checksums and decoded grid checksums.

    Raises:
        ValueError: The build is incomplete or its saved files cannot be verified.
    """
    map_version = version(candidate)
    prefix = release_prefix(candidate)
    run = run.resolve()
    report, identity, configuration, selection = _read_build(run)
    final = run / "final"
    grid, summary = _read_final_grid(final, report["final"], selection["geography"])
    attempts, code = _read_attempts(run)

    _copy_viewer(viewer, bundle, prefix)
    combined, decoded = _compress_grid(
        final, bundle, report["final"], grid.height, summary["run_count"]
    )
    _write_viewer_data(
        bundle,
        selection["geography"],
        summary,
        grid,
        map_version=map_version,
        water_edition=configuration["sources"]["inland_water"].get("release"),
        combined=combined,
        decoded=decoded,
    )
    write_inputs(
        bundle / FILENAME,
        release_id=candidate,
        configuration=configuration,
        selection=selection,
        run=dict(identity, attempts=attempts),
        report=report,
        source_code=code,
    )
    return {
        "inputs": {"archive": FILENAME},
        "decoded_sha256": decoded,
        "objects": _file_manifest(bundle, prefix),
    }

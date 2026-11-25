"""Save and restore the inputs and code used by a completed map build."""

import gzip
import json
import re
from pathlib import Path
from typing import TypedDict, cast

from pydantic import TypeAdapter

from worldatlas.map_build.execution.code_archive import restore_source, source_files
from worldatlas.map_build.inputs.configuration import (
    BuildConfiguration,
    RawFileReference,
    iter_physical_source_files,
)
from worldatlas.map_build.inputs.selection_types import BuildSelection
from worldatlas.shared.files import SHA256_PATTERN, JSONValue, json_bytes

FILENAME = "inputs.json.gz"
SCHEMA = "worldatlas-release-inputs-v1"
REPLAY_FILES = ("configuration", "selection", "run", "report")
RAW_FILE_REFERENCE = TypeAdapter(RawFileReference)


class ReleaseInputs(TypedDict):
    """Record a completed build and the code needed to replay it."""

    schema: str
    release_id: str
    configuration: BuildConfiguration
    selection: BuildSelection
    run: dict[str, JSONValue]
    report: dict[str, JSONValue]
    source_code: dict[str, dict[str, JSONValue]]


def validate_replay_sources(
    configuration: BuildConfiguration, selection: BuildSelection
) -> None:
    """Check that a fresh machine can download the build's physical inputs.

    For a file selected from a ZIP archive, check how to fetch the ZIP itself.

    Args:
        configuration: Settings already validated and used by the map build.
        selection: Frozen geographic records, including the raw source catalog.

    Raises:
        ValueError: A reference is invalid or its catalog entry is missing.
    """
    source_ids = {row["source_id"] for row in selection["raw_sources"]}
    for saved_source in iter_physical_source_files(configuration["sources"]):
        # A saved build may have used an earlier version of the input schema.
        source = RAW_FILE_REFERENCE.validate_python(saved_source, strict=True)
        if "r2_source" in source and source["r2_source"] not in source_ids:
            raise ValueError(
                f"release replay is missing catalog source {source['r2_source']!r}"
            )


def write_inputs(
    path: Path | str,
    *,
    release_id: str,
    configuration: BuildConfiguration,
    selection: BuildSelection,
    run: dict[str, JSONValue],
    report: dict[str, JSONValue],
    source_code: dict[str, dict[str, JSONValue]],
) -> None:
    """Write the completed build's inputs and code as gzip-compressed JSON.

    Args:
        path: Destination file, which must be new.
        release_id: Exact release ID recorded inside the archive.
        configuration: Saved map build settings.
        selection: Frozen geographic records and raw source catalog.
        run: Saved run identity and build attempt records.
        report: Saved build report with output references and timings.
        source_code: Captured code snapshots keyed by their SHA-256 checksums.

    Raises:
        FileExistsError: The destination file already exists.
    """
    content = ReleaseInputs(
        schema=SCHEMA,
        release_id=release_id,
        configuration=configuration,
        selection=selection,
        run=run,
        report=report,
        source_code=source_code,
    )
    # Staging retries must produce the same bytes.
    with Path(path).open("xb") as output:
        output.write(gzip.compress(json_bytes(content), compresslevel=6, mtime=0))


def read_inputs(raw: bytes, release_id: str) -> ReleaseInputs:
    """Read the frozen inputs for one release.

    Args:
        raw: Gzip-compressed JSON bytes already checked against the manifest.
        release_id: Release ID expected inside the archive.

    Returns:
        Saved configuration, selection, run, report, and source code.

    Raises:
        ValueError: The release identity or archive format differs from what is expected.
        OSError: The gzip stream is invalid.
    """
    content = json.loads(gzip.decompress(raw))
    if (
        not isinstance(content, dict)
        or content.get("schema") != SCHEMA
        or content.get("release_id") != release_id
    ):
        raise ValueError("input archive has a different format or release identity")
    if (
        content.keys() != ReleaseInputs.__required_keys__
        or not all(
            isinstance(content[key], dict) for key in (*REPLAY_FILES, "source_code")
        )
        or not content["source_code"]
    ):
        raise ValueError("input archive requires a complete build and captured code")
    return cast(ReleaseInputs, content)


def restore_inputs(content: ReleaseInputs, output: Path | str) -> None:
    """Save the archived build records and unpack its code into a new directory.

    Args:
        content: Parsed release archive from ``read_inputs``.
        output: Directory for configuration.json, selection.json, run.json,
            report.json, and the captured code under code/.

    Raises:
        FileExistsError: The destination already exists.
        ValueError: A captured code snapshot has an invalid identity or contents.
    """
    # Check the code paths before creating any output files.
    snapshots = {}
    for checksum, code in content["source_code"].items():
        if not re.fullmatch(SHA256_PATTERN, checksum):
            raise ValueError("invalid source archive identity")
        snapshots[checksum] = source_files(code)

    output = Path(output)
    output.mkdir(parents=True)
    for key in REPLAY_FILES:
        (output / f"{key}.json").write_bytes(json_bytes(content[key]))
    for checksum, files in snapshots.items():
        restore_source(files, output / "code" / checksum)

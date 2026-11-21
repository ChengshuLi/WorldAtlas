"""Capture and restore a release's frozen inputs without querying working geography."""

import gzip
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from worldatlas.map_build.execution.code_archive import restore_source, source_files
from worldatlas.map_build.physical.build import (
    validate_r2_shard_location,
    validate_shard_staging,
)
from worldatlas.shared.files import json_bytes

FILENAME = "inputs.json.gz"
SCHEMA = "worldatlas-release-inputs-v1"


def validate_replay_sources(
    configuration: dict[str, Any], selection: dict[str, Any]
) -> None:
    """Check that physical inputs can be read again on a fresh machine.

    Args:
        configuration: Original build request to include in the archive.
        selection: Frozen source catalog and geographic records.

    Raises:
        ValueError: A physical input or shard setting would prevent an empty-cache replay.
    """
    sources = configuration["sources"]
    catalog_rows = selection["raw_sources"]
    # Current source IDs identify exact bytes. Older frozen selections can
    # also carry a version, which must match when a request specifies one.
    catalog = {(row["source_id"], None): row for row in catalog_rows}
    catalog.update(
        {(row["source_id"], row.get("version")): row for row in catalog_rows}
    )

    def catalog_asset(spec: dict[str, Any]) -> dict[str, Any] | None:
        """Look up a physical input in the frozen raw source catalog.

        Args:
            spec: Input with an R2 source selector.

        Returns:
            Matching catalog dictionary, or None if the source is missing.
        """
        reference = spec["r2_source"]
        return catalog.get((reference["source_id"], reference.get("version")))

    def r2_source(spec: object) -> bool:
        """Check whether a specification can be downloaded using the frozen inputs.

        Args:
            spec: Candidate physical input or archive member.

        Returns:
            True if the specification identifies an R2 object.
        """
        if not isinstance(spec, dict):
            return False
        if "r2_source" in spec:
            return catalog_asset(spec) is not None
        if "archive" in spec:
            return r2_source(spec["archive"])
        return all(spec.get(key) for key in ("r2_bucket", "r2_key", "sha256"))

    def require_source(name: str, spec: object) -> None:
        """Reject an input that a new machine could not download.

        Args:
            name: Input name for error messages.
            spec: Candidate physical input.

        Raises:
            ValueError: The input specifies only a local file.
        """
        if not r2_source(spec):
            raise ValueError(f"release replay requires an R2 pin for {name}")

    for index, layer in enumerate(sources["land_config"]["land"]):
        require_source(f"land_config.land[{index}].dataset", layer["dataset"])
        for file_index, spec in enumerate(layer["files"]):
            require_source(f"land_config.land[{index}].files[{file_index}]", spec)
    validate_shard_staging(configuration.get("physical_controls", {}), require_r2=True)
    # Each shard's ``path`` names a place in the build's cache. The catalog
    # reference or the direct R2 key and byte size tell a fresh build what to fetch.
    for index, spec in enumerate(sources["inland_water"]["files"]):
        name = f"inland_water.files[{index}]"
        require_source(name, spec)
        if "r2_source" not in spec:
            try:
                validate_r2_shard_location(spec)
            except ValueError as error:
                raise ValueError(
                    f"release replay requires an R2 object and byte size for {name}"
                ) from error


def write_inputs(
    path: Path | str,
    *,
    release_id: str,
    configuration: dict[str, Any],
    selection: dict[str, Any],
    run: dict[str, Any],
    report: dict[str, Any],
    records: Sequence[dict[str, Any]] = (),
    raw_sources: Sequence[dict[str, Any]] = (),
    notes: Sequence[str] = (),
    relocations: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    source_code: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Write the frozen build inputs as a new gzip-compressed JSON file.

    Args:
        path: Destination file, which must be new.
        release_id: Exact release ID recorded inside the archive.
        configuration: Saved map build request.
        selection: Frozen geographic records and raw source catalog entries.
        run: Saved run identity and attempt records.
        report: Saved build report with output references and timings.
        records: Optional supporting records retained during a historical backfill.
        raw_sources: Optional raw source records stored separately by a backfill.
        notes: Optional notes on the provenance or gaps in a historical archive.
        relocations: Optional mapping from old source locations to new locations.
        metadata: Optional archive metadata, such as its historical origin.
        source_code: Captured code snapshots keyed by their archive checksums.

    Raises:
        FileExistsError: The destination file already exists.
    """
    content: dict[str, Any] = dict(
        schema=SCHEMA,
        release_id=release_id,
        configuration=configuration,
        selection=selection,
        run=run,
        report=report,
    )
    if source_code:
        content["source_code"] = source_code
    if records:
        content["supporting_records"] = records
    if raw_sources:
        content["raw_sources"] = raw_sources
    if notes:
        content["notes"] = list(notes)
    if relocations:
        content["relocations"] = relocations
    if metadata:
        content["metadata"] = metadata
    # Omit per-run gzip metadata so a staging retry can match the stored bytes.
    with (
        Path(path).open("xb") as output,
        gzip.GzipFile(
            filename="", fileobj=output, mode="wb", mtime=0, compresslevel=6
        ) as compressed,
    ):
        compressed.write(json_bytes(content))


def read_inputs(raw: bytes, release_id: str) -> dict[str, Any]:
    """Read a verified input archive and check its release identity.

    Args:
        raw: Gzip-compressed JSON bytes already checked against the manifest.
        release_id: Release ID expected inside the archive.

    Returns:
        Parsed configuration, selection, and any other saved records.

    Raises:
        ValueError: The archive format or release ID differs from the expected value.
        OSError: The gzip stream is invalid.
    """
    content = json.loads(gzip.decompress(raw))
    if content.get("schema") != SCHEMA or content.get("release_id") != release_id:
        raise ValueError("input archive has a different format or release identity")
    return content


def restore_inputs(content: dict[str, Any], output: Path | str) -> None:
    """Extract the saved inputs that a separate map build can use for replay.

    Args:
        content: Parsed release archive from ``read_inputs``.
        output: New directory for the saved JSON records and code snapshots.

    Raises:
        FileExistsError: The destination already exists.
        ValueError: A captured code snapshot has an invalid identity or contents.
    """
    # Check all code snapshots before creating any output files.
    for identity, code in content.get("source_code", {}).items():
        if (
            not isinstance(identity, str)
            or len(identity) != 64
            or any(c not in "0123456789abcdef" for c in identity)
        ):
            raise ValueError("invalid source archive identity")
        source_files(code)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)

    def relocated(value: object) -> Any:
        """Copy a JSON value and update source locations.

        Args:
            value: Value from the saved release inputs.

        Returns:
            JSON-compatible copy with matching paths replaced.
        """
        if isinstance(value, dict):
            return {key: relocated(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relocated(item) for item in value]
        if isinstance(value, str):
            return content.get("relocations", {}).get(value, value)
        return value

    for key in (
        "configuration",
        "selection",
        "run",
        "report",
        "supporting_records",
        "raw_sources",
        "notes",
        "metadata",
    ):
        if content.get(key) is not None:
            # Update replay inputs. Keep the historical report and run record
            # as captured so their paths still describe what the original run did.
            value = (
                relocated(content[key])
                if key in ("configuration", "selection", "raw_sources")
                else content[key]
            )
            if key == "configuration" and isinstance(value.get("sources"), dict):
                # Comparisons validate an earlier run; they do not produce map
                # cells. Their local paths need not exist on the replay machine.
                value["sources"].pop("reference_rows", None)
                value["sources"].pop("reference_runs", None)
            (output / (key + ".json")).write_bytes(json_bytes(value))

    for identity, code in content.get("source_code", {}).items():
        restore_source(code, output / "code" / identity)

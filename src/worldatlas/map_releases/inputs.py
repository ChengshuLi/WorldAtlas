"""Capture and restore a release's frozen inputs without querying working geography."""

import gzip
import hashlib
import json
from pathlib import Path

from worldatlas.map_build.execution.code_archive import restore_source, source_files
from worldatlas.map_build.execution.runtime import json_bytes
from worldatlas.map_build.physical.build import validate_r2_shard_location

FILENAME = "inputs.json.gz"
SCHEMA = "worldatlas-release-inputs-v1"


def validate_replay_sources(configuration, selection, source_pins):
    """Check that physical inputs can be read again on a fresh machine.

    Args:
        configuration: Original build request to include in the archive.
        selection: Frozen source catalog and geographic records.
        source_pins: Local paths and checksums recorded by the build. These
            let staging inspect R2-backed input documents already on disk.

    Raises:
        ValueError: A physical input would require files from the build machine.
    """
    cached_paths = {pin["sha256"]: Path(pin["path"]) for pin in source_pins}
    sources = configuration["sources"]
    catalog_rows = selection["raw_sources"]
    # Current source IDs identify exact bytes. Older frozen selections can
    # also carry a version, which must match when a request specifies one.
    catalog = {(row["source_id"], None): row for row in catalog_rows}
    catalog.update({(row["source_id"], row.get("version")): row for row in catalog_rows})

    def catalog_asset(spec):
        reference = spec["r2_source"]
        return catalog.get((reference["source_id"], reference.get("version")))

    def r2_source(spec):
        """Recognize a catalog reference, a pinned object, or an archive member."""
        if not isinstance(spec, dict):
            return False
        if "r2_source" in spec:
            return catalog_asset(spec) is not None
        if "archive" in spec:
            return r2_source(spec["archive"])
        return all(spec.get(key) for key in ("r2_bucket", "r2_key", "sha256"))

    def require_source(name, spec, *, inline=False):
        if r2_source(spec) or (inline and isinstance(spec, dict) and set(spec) == {"json"}):
            return
        options = "inline JSON or an R2 pin" if inline else "an R2 pin"
        raise ValueError(f"release replay requires {options} for {name}")

    def read_document(name, spec):
        """Inspect inline JSON or reuse the exact R2 document cached by the build."""
        require_source(name, spec, inline=True)
        if "json" in spec:
            return spec["json"]
        pin = catalog_asset(spec) if "r2_source" in spec else spec
        checksum = pin["sha256"]
        path = cached_paths.get(checksum)
        if path is None or not path.is_file():
            raise ValueError(f"release replay needs the build's cached R2 document for {name}")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError(f"cached R2 document changed after the build: {name}")
        return json.loads(raw)

    require_source("water_config", sources["water_config"], inline=True)
    land = read_document("land_config", sources["land_config"])
    for index, layer in enumerate(land.get("land", [])):
        require_source(f"land_config.land[{index}].dataset", layer["dataset"], inline=True)
        for file_index, spec in enumerate(layer["files"]):
            require_source(f"land_config.land[{index}].files[{file_index}]", spec, inline=True)
    raw_spec = sources["raw_manifest"]
    raw = read_document("raw_manifest", raw_spec)
    # The builder resolves catalog references in the request before fetching
    # any external documents. A fetched manifest already needs R2 locations.
    inline_manifest = "json" in raw_spec
    staging = configuration.get("physical_controls", {}).get("source_staging") or {}
    # Each shard's ``path`` names a place in the build's cache. The catalog
    # reference or the direct R2 key and byte size tell a fresh build what to fetch.
    for index, spec in enumerate(raw["files"]):
        name = f"raw_manifest.files[{index}]"
        require_source(name, spec)
        if not (inline_manifest and "r2_source" in spec):
            try:
                validate_r2_shard_location(spec)
            except ValueError as error:
                raise ValueError(f"release replay requires an R2 object and byte size for {name}") from error
        # The physical stage only downloads uncached shards in R2 staging mode.
        if staging.get("mode") != "r2-s3":
            raise ValueError(f"release replay requires R2 staging for {name}")


def write_inputs(
    path,
    *,
    release_id,
    configuration,
    selection,
    run,
    report,
    records=(),
    raw_sources=(),
    notes=(),
    relocations=None,
    metadata=None,
    source_code=None,
):
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
    content = dict(
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


def read_inputs(raw, release_id):
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


def restore_inputs(content, output):
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

    def relocated(value):
        """Copy a JSON value while replacing any recorded source locations."""
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

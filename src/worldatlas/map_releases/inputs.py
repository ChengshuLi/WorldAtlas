"""Capture and restore a release's frozen inputs without querying working geography."""

import gzip
import hashlib
import json
from pathlib import Path

from worldatlas.map_build.execution.code_archive import restore_source, source_files
from worldatlas.map_build.execution.runtime import json_bytes

FILENAME = "inputs.json.gz"
SCHEMA = "worldatlas-release-inputs-v1"


def validate_replay_sources(configuration, selection, source_pins):
    """Require staged builds to obtain physical inputs from the archive or R2.

    Args:
        configuration: Original build request to include in the archive.
        selection: Frozen source catalog and geographic records.
        source_pins: Local copies of physical inputs verified by the build.

    Raises:
        ValueError: A physical input would require files from the build machine.
    """
    cached_paths = {pin["sha256"]: Path(pin["path"]) for pin in source_pins}
    sources = configuration["sources"]
    catalog_rows = selection["raw_sources"]
    catalog = {(row["source_id"], None): row for row in catalog_rows}
    catalog.update({(row["source_id"], row.get("version")): row for row in catalog_rows})

    def catalog_asset(spec):
        reference = spec["r2_source"]
        return catalog.get((reference["source_id"], reference.get("version")))

    def r2_source(spec):
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
    raw = read_document("raw_manifest", sources["raw_manifest"])
    staging = configuration.get("physical_controls", {}).get("source_staging") or {}
    for index, spec in enumerate(raw["files"]):
        name = f"raw_manifest.files[{index}]"
        require_source(name, spec)
        if "r2_source" not in spec and (
            type(spec.get("size")) is not int or spec["size"] < 0 or "archive" in spec
        ):
            raise ValueError(f"release replay requires an R2 object and byte size for {name}")
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
    """Use captured run data. Historical gaps are recorded rather than guessed."""
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
    with (
        Path(path).open("xb") as output,
        gzip.GzipFile(
            filename="", fileobj=output, mode="wb", mtime=0, compresslevel=6
        ) as compressed,
    ):
        compressed.write(json_bytes(content))


def read_inputs(raw, release_id):
    content = json.loads(gzip.decompress(raw))
    if content.get("schema") != SCHEMA or content.get("release_id") != release_id:
        raise ValueError("input archive has a different format or release identity")
    return content


def restore_inputs(content, output):
    """Extract saved configuration and selection for the ordinary build command."""
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

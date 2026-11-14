"""Capture and restore a release's frozen inputs without querying working geography."""

import gzip
import json
from pathlib import Path

from worldatlas.map_build.execution.runtime import json_bytes

FILENAME = "inputs.json.gz"
SCHEMA = "worldatlas-release-inputs-v1"


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
    from worldatlas.map_build.execution.code_archive import source_files, restore_source

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
            (output / (key + ".json")).write_bytes(json_bytes(value))

    for identity, code in content.get("source_code", {}).items():
        restore_source(code, output / "code" / identity)

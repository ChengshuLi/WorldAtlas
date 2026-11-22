"""Types and parsers for build requests and saved file pins."""

from pathlib import Path
from typing import Annotated, Literal, NotRequired, TypedDict

from pydantic import (
    Field,
    JsonValue,
    StringConstraints,
    TypeAdapter,
    with_config,
)

type PositiveInt = Annotated[int, Field(gt=0)]
type ByteCount = Annotated[int, Field(ge=0)]
type NonemptyString = Annotated[str, StringConstraints(min_length=1)]
type Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
type FileEntry = dict[str, JsonValue]


@with_config(extra="forbid")
class FilePin(TypedDict):
    """Identify a local file by path and expected SHA-256."""

    path: NonemptyString
    sha256: Digest


@with_config(extra="forbid")
class GridSettings(TypedDict):
    """Describe the dimensions, origin, and cell size of the map grid."""

    width: PositiveInt
    height: PositiveInt
    step: int | float
    west: NotRequired[int | float]
    north: NotRequired[int | float]


@with_config(extra="allow")
class LandLayer(TypedDict):
    """Choose the main coastline file and pin every file GDAL will read.

    The ``dataset`` names an entry in ``files``. For a Shapefile, it identifies
    the .shp, and ``files`` also lists its companions such as .shx, .dbf, and .prj.
    """

    dataset: NonemptyString
    files: list[FileEntry]


@with_config(extra="allow")
class LandSettings(TypedDict):
    """Specify coastline layers and how to rasterize them."""

    land: list[LandLayer]
    strip_rows: NotRequired[PositiveInt]
    minimum_free_bytes: NotRequired[ByteCount]


@with_config(extra="allow")
class WaterSettings(TypedDict):
    """Specify how to rasterize each inland-water file."""

    rasterizer: NotRequired[Literal["gdal", "python"]]
    batch_size: NotRequired[PositiveInt]
    tile_size: NotRequired[PositiveInt]
    minimum_free_bytes: NotRequired[ByteCount]


@with_config(extra="allow")
class InlandWaterSettings(WaterSettings):
    """Select the inland-water files and their shared rasterization settings."""

    files: list[FileEntry]
    file_count: NotRequired[PositiveInt]


@with_config(extra="forbid")
class BuildSources(TypedDict):
    """Select the physical inputs and optional map comparison inputs."""

    land_config: LandSettings
    inland_water: InlandWaterSettings
    reference_rows: NotRequired[FileEntry]
    reference_runs: NotRequired[FileEntry]


@with_config(extra="allow")
class PhysicalControls(TypedDict):
    """Set physical-stage processing and download options."""

    minimum_free_bytes: NotRequired[ByteCount]
    max_parallel_shards: NotRequired[PositiveInt]
    union_rows_per_block: NotRequired[PositiveInt]
    physical_rows_per_block: NotRequired[PositiveInt]


@with_config(extra="allow")
class BuildConfiguration(TypedDict):
    """Describe the editable request for an end-to-end map build."""

    schema: Literal["worldatlas-end-to-end-pipeline-v3"]
    grid: GridSettings
    r2_endpoint: NotRequired[NonemptyString]
    sources: BuildSources
    selection_notes: NotRequired[str]
    physical_controls: NotRequired[PhysicalControls]
    coastal_band_metres: NotRequired[int | float]
    division_workers: NotRequired[PositiveInt]


@with_config(extra="allow")
class WaterFile(FilePin):
    """Describe a water file available locally or pinned to an R2 object."""

    r2_bucket: NotRequired[str]
    r2_key: NotRequired[str]
    size_bytes: NotRequired[ByteCount]


@with_config(extra="allow")
class PinnedInlandWaterSettings(WaterSettings):
    """Specify the water rasterizer and every file it will read."""

    file_count: PositiveInt
    files: Annotated[list[WaterFile], Field(min_length=1)]


@with_config(extra="allow")
class PhysicalConfiguration(PhysicalControls):
    """Describe the saved request consumed by the standalone physical runner."""

    schema: Literal["raw-physical-pipeline-v3"]
    selection_notes: NonemptyString
    source_directory: NonemptyString
    grid: GridSettings
    r2_endpoint: NotRequired[NonemptyString]
    land_config: LandSettings
    inland_water: PinnedInlandWaterSettings
    water_reference: NotRequired[FilePin]
    physical_reference_mask: NotRequired[FilePin]
    physical_reference_streams: NotRequired[dict[str, FilePin]]


BUILD_CONFIGURATION = TypeAdapter(BuildConfiguration)
PHYSICAL_CONFIGURATION = TypeAdapter(PhysicalConfiguration)
PHYSICAL_CONTROLS = TypeAdapter(PhysicalControls)
FILE_PIN = TypeAdapter(FilePin)
COMPARISON_PINS = TypeAdapter(dict[str, FilePin])


def require_separate_cache_and_output(cache: Path, output: Path) -> None:
    """Require the input cache and the build output to use separate directories.

    Args:
        cache: Resolved input cache directory.
        output: Resolved build output directory.

    Raises:
        ValueError: Either directory contains or equals the other.
    """
    if output.is_relative_to(cache) or cache.is_relative_to(output):
        raise ValueError("output and the input cache must use separate directories")


def land_dataset_index(layer: LandLayer) -> int:
    """Find which pinned coastline file GDAL should open.

    Args:
        layer: Coastline file pins and the dataset's member path, local path,
            R2 key, or Neon source ID.

    Returns:
        Index of the matching entry in the layer's ``files`` list.

    Raises:
        ValueError: The dataset identifies zero or multiple file entries.
    """
    dataset = layer["dataset"]
    matches = [
        index
        for index, file in enumerate(layer["files"])
        if dataset
        in (
            file.get("member"),
            file.get("path"),
            file.get("r2_key"),
            file.get("r2_source"),
            file.get("source_id"),
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"coastline dataset {dataset!r} must name exactly one entry in files"
        )
    return matches[0]


def catalog_source_id(entry: FileEntry) -> str:
    """Validate and return the Neon source ID in a file or ZIP archive entry.

    Args:
        entry: File or archive settings containing an ``r2_source`` selector.

    Returns:
        The source ID from the catalog.

    Raises:
        ValueError: The selector is invalid or the same entry also pins its R2 bytes.
    """
    source_id = entry["r2_source"]
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("r2_source must be a nonblank Neon source ID")
    # With r2_source, Neon supplies the file details. Reject those keys in the
    # same entry so the lookup cannot silently overwrite them.
    pinned_fields = {
        "r2_bucket",
        "r2_key",
        "source_id",
        "sha256",
        "size_bytes",
        "size",
    }
    if pinned_fields.intersection(entry):
        raise ValueError("invalid raw catalog reference: remove explicit file metadata")
    return source_id

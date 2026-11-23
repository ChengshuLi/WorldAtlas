"""Types and parsers for build requests and saved file pins."""

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Annotated, Literal, NotRequired

from pydantic import (
    AfterValidator,
    Field,
    StringConstraints,
    TypeAdapter,
    with_config,
)
from typing_extensions import TypedDict

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.inputs.selection_types import SourceAsset

type PositiveInt = Annotated[int, Field(gt=0)]
type ByteCount = Annotated[int, Field(ge=0)]
type NonemptyString = Annotated[str, StringConstraints(min_length=1)]
type Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
type SourceName = Annotated[str, StringConstraints(pattern=r"\S")]


class FilePin(TypedDict):
    """Identify a local file by path and expected SHA-256."""

    path: NonemptyString
    sha256: Digest


class LocalFile(FilePin, closed=True):
    """Pin a local source without requiring access to R2."""

    size_bytes: NotRequired[ByteCount]


class CatalogFile(TypedDict, closed=True):
    """Select a raw source by its ID in the frozen catalog."""

    r2_source: SourceName


class ObjectFile(TypedDict, closed=True):
    """Pin a complete R2 object's identity and transfer location."""

    r2_bucket: NonemptyString
    r2_key: NonemptyString
    sha256: Digest
    size_bytes: ByteCount
    source_id: NotRequired[SourceName]


class ArchiveMember[Archive](TypedDict, closed=True):
    """Pin a local extraction of one member of a remote ZIP file."""

    archive: Archive
    member: NonemptyString
    sha256: Digest
    size_bytes: ByteCount


type WaterFile = LocalFile | CatalogFile | ObjectFile
type LandFile = WaterFile | ArchiveMember[CatalogFile | ObjectFile]
type ResolvedLandFile = LocalFile | ObjectFile | ArchiveMember[ObjectFile]
type ResolvedWaterFile = LocalFile | ObjectFile


@with_config(extra="forbid")
class GridSettings(TypedDict):
    """Describe the dimensions, origin, and cell size of the map grid."""

    width: PositiveInt
    height: PositiveInt
    step: int | float
    west: NotRequired[int | float]
    north: NotRequired[int | float]


@with_config(extra="forbid")
class LandLayer[File](TypedDict):
    """Choose the main coastline file and pin every file GDAL will read.

    The ``dataset`` names an entry in ``files``. For a Shapefile, it identifies
    the .shp, and ``files`` also lists its companions such as .shx, .dbf, and .prj.
    """

    dataset: NonemptyString
    files: list[File]
    layer: NotRequired[NonemptyString | None]
    where: NotRequired[str | None]


@with_config(extra="forbid")
class LandSettings[File](TypedDict):
    """Specify coastline layers and how to rasterize them."""

    land: list[LandLayer[File]]
    schema: NotRequired[Literal["land-raster-candidate-v1"]]
    selection_notes: NotRequired[NonemptyString]
    strip_rows: NotRequired[PositiveInt]
    feature_index: NotRequired[Literal["row-fids", "scan"]]


@with_config(extra="forbid")
class WaterPolicy(TypedDict):
    """Select the supported Overture inland-water subtype policy."""

    method: Literal["overture-inland-subtype-v1"]


@with_config(extra="forbid")
class WaterSettings(TypedDict):
    """Specify how to rasterize each inland-water file."""

    rasterizer: NotRequired[Literal["gdal", "python"]]
    batch_size: NotRequired[PositiveInt]
    tile_size: NotRequired[Annotated[int, Field(ge=1, le=4096)]]
    batch_method: NotRequired[Literal["hybrid", "tiled"]]
    selection_notes: NotRequired[NonemptyString]
    schema: NotRequired[Literal["water-shard-candidate-v2"]]
    policy: NotRequired[WaterPolicy]


@with_config(extra="forbid")
class InlandWaterSettings[File](WaterSettings):
    """Select the inland-water files and their shared rasterization settings."""

    files: Annotated[list[File], Field(min_length=1)]
    file_count: PositiveInt
    source: NotRequired[NonemptyString]
    release: NotRequired[NonemptyString]
    theme: NotRequired[NonemptyString]
    type: NotRequired[NonemptyString]
    total_bytes: NotRequired[ByteCount]


def check_shard_count[File](
    settings: InlandWaterSettings[File],
) -> InlandWaterSettings[File]:
    """Confirm the declared number of inland-water files matches the list.

    Args:
        settings: Validated inland-water settings.

    Returns:
        The same settings when the declared size matches the list.

    Raises:
        ValueError: The selected file list is incomplete or has extra entries.
    """
    if settings["file_count"] != len(settings["files"]):
        raise ValueError("inland water must list every raw shard")
    return settings


@with_config(extra="forbid")
class BuildSources(TypedDict):
    """Select the physical coastline and inland-water inputs."""

    land_config: LandSettings[LandFile]
    inland_water: Annotated[
        InlandWaterSettings[WaterFile], AfterValidator(check_shard_count)
    ]


@with_config(extra="forbid")
class PhysicalControls(TypedDict):
    """Set physical-stage processing and download options."""

    minimum_free_bytes: NotRequired[ByteCount]
    max_parallel_shards: NotRequired[PositiveInt]
    union_rows_per_block: NotRequired[PositiveInt]
    physical_rows_per_block: NotRequired[PositiveInt]


@with_config(extra="forbid")
class BuildConfiguration(TypedDict):
    """Describe the editable request for an end-to-end map build."""

    schema: Literal["worldatlas-end-to-end-pipeline-v3"]
    grid: GridSettings
    sources: BuildSources
    selection_notes: NotRequired[NonemptyString]
    physical_controls: NotRequired[PhysicalControls]
    coastal_band_metres: NotRequired[Annotated[float, Field(ge=0, allow_inf_nan=False)]]
    division_workers: NotRequired[PositiveInt]


@with_config(extra="forbid")
class PhysicalConfiguration(PhysicalControls):
    """Describe the saved request consumed by the standalone physical runner."""

    schema: Literal["raw-physical-pipeline-v3"]
    selection_notes: NotRequired[NonemptyString]
    source_directory: NonemptyString
    grid: GridSettings
    land_config: LandSettings[ResolvedLandFile]
    inland_water: Annotated[
        InlandWaterSettings[ResolvedWaterFile], AfterValidator(check_shard_count)
    ]


BUILD_CONFIGURATION = TypeAdapter(BuildConfiguration)
PHYSICAL_CONFIGURATION = TypeAdapter(PhysicalConfiguration)


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


def land_dataset_index[File: LandFile | ResolvedLandFile](
    layer: LandLayer[File],
) -> int:
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


def file_requests(sources: BuildSources) -> Iterator[LandFile]:
    """Visit the file specifications in a map build request.

    Args:
        sources: Validated coastline and inland-water settings.

    Yields:
        Each water file followed by each coastline file in layer order.
    """
    yield from sources["inland_water"]["files"]
    for layer in sources["land_config"]["land"]:
        yield from layer["files"]


def source_file(spec: LandFile) -> WaterFile:
    """Get the source file selected directly or containing a selected ZIP member.

    Args:
        spec: A direct file pin, catalog ID or ZIP member.

    Returns:
        The direct file specification used to obtain source bytes.
    """
    return spec["archive"] if "archive" in spec else spec


def catalog_source_ids(sources: BuildSources) -> set[str]:
    """Collect the raw catalog IDs needed to resolve a request.

    Args:
        sources: Coastline and inland-water selections.

    Returns:
        Distinct source IDs, including ZIP containers selected by catalog ID.
    """
    return {
        entry["r2_source"]
        for selection in file_requests(sources)
        if "r2_source" in (entry := source_file(selection))
    }


def resolve_object(
    file: CatalogFile | ObjectFile, catalog: Mapping[str, ObjectFile]
) -> ObjectFile:
    """Replace a catalog selection with its R2 location and byte identity.

    Args:
        file: Direct R2 pin or catalog selector.
        catalog: Object pins by ID from the frozen selection.

    Returns:
        One resolved R2 pin.
    """
    if "r2_source" not in file:
        return file
    source_id = file["r2_source"]
    if source_id not in catalog:
        raise ValueError(f"raw catalog is missing selected sources: {source_id}")
    return catalog[source_id]


def resolve_land_file(
    file: LandFile, catalog: Mapping[str, ObjectFile]
) -> ResolvedLandFile:
    """Resolve a coastline file or the R2 archive containing it.

    Args:
        file: Coastline file selection.
        catalog: Object pins by ID from the frozen selection.

    Returns:
        A file pin or ZIP member with its archive pinned in R2.
    """
    if "archive" in file:
        return {**file, "archive": resolve_object(file["archive"], catalog)}
    return file if "path" in file else resolve_object(file, catalog)


def physical_configuration(
    configuration: BuildConfiguration,
    sources: Sequence[SourceAsset],
    grid: Grid,
    cache: Path,
) -> PhysicalConfiguration:
    """Build a standalone physical request with every R2 input pinned.

    Args:
        configuration: Validated editable build settings.
        sources: Frozen raw source catalog from the selection.
        grid: Validated grid used by all stages.
        cache: Workspace input directory.

    Returns:
        A JSON-ready physical request. The original settings are left intact.
    """
    catalog: dict[str, ObjectFile] = {
        row["source_id"]: {
            "source_id": row["source_id"],
            "r2_bucket": row["r2_bucket"],
            "r2_key": row["r2_key"],
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        for row in sources
    }
    land = configuration["sources"]["land_config"]
    water = configuration["sources"]["inland_water"]
    layers: list[LandLayer[ResolvedLandFile]] = [
        {
            **layer,
            "files": [resolve_land_file(file, catalog) for file in layer["files"]],
        }
        for layer in land["land"]
    ]
    shards: list[ResolvedWaterFile] = [
        file if "path" in file else resolve_object(file, catalog)
        for file in water["files"]
    ]
    controls: PhysicalControls = configuration.get("physical_controls", {})
    result: PhysicalConfiguration = {
        **controls,
        "schema": "raw-physical-pipeline-v3",
        "source_directory": str(cache),
        "grid": {
            "width": grid.width,
            "height": grid.height,
            "step": grid.step,
            "west": grid.west,
            "north": grid.north,
        },
        "land_config": {**land, "land": layers},
        "inland_water": {**water, "files": shards},
    }
    if "selection_notes" in configuration:
        result["selection_notes"] = configuration["selection_notes"]
    return result

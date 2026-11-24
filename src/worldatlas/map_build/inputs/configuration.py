"""Types and parsers for build requests and saved file pins."""

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Annotated, Literal, NotRequired

from pydantic import (
    AfterValidator,
    Field,
    TypeAdapter,
    with_config,
)
from typing_extensions import TypedDict

from worldatlas.map_build.core.grid import Grid
from worldatlas.map_build.inputs.selection_types import SourceAsset
from worldatlas.shared.files import ByteCount
from worldatlas.shared.text import NonEmptyText
from worldatlas.source_assets.pins import ArchiveMember, R2ObjectPin, RemoteFile

type PositiveInt = Annotated[int, Field(gt=0)]


class CatalogFile(TypedDict, closed=True):
    """Select a raw source by its ID in the frozen catalog."""

    r2_source: NonEmptyText


type RawFileReference = CatalogFile | R2ObjectPin
type CoastlineFileReference = RawFileReference | ArchiveMember[RawFileReference]


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
    Set ``where`` to a filter string or to null to select the whole layer.
    """

    dataset: NonEmptyText
    files: list[File]
    where: str | None
    layer: NotRequired[NonEmptyText | None]


@with_config(extra="forbid")
class LandSettings[File](TypedDict):
    """Specify coastline layers and how to rasterize them."""

    land: list[LandLayer[File]]
    schema: NotRequired[Literal["land-raster-candidate-v1"]]
    selection_notes: NotRequired[NonEmptyText]
    strip_rows: NotRequired[PositiveInt]


@with_config(extra="forbid")
class WaterSettings(TypedDict):
    """Specify how to rasterize each inland-water file."""

    rasterizer: NotRequired[Literal["gdal"]]
    batch_size: NotRequired[PositiveInt]
    tile_size: NotRequired[Annotated[int, Field(ge=1, le=4096)]]
    selection_notes: NotRequired[NonEmptyText]
    schema: NotRequired[Literal["water-shard-candidate-v2"]]


@with_config(extra="forbid")
class InlandWaterSettings[File](WaterSettings):
    """Select the inland-water files and their shared rasterization settings."""

    files: Annotated[list[File], Field(min_length=1)]
    file_count: PositiveInt
    source: NotRequired[NonEmptyText]
    release: NotRequired[NonEmptyText]
    theme: NotRequired[NonEmptyText]
    type: NotRequired[NonEmptyText]
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

    land_config: LandSettings[CoastlineFileReference]
    inland_water: Annotated[
        InlandWaterSettings[RawFileReference], AfterValidator(check_shard_count)
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
    selection_notes: NotRequired[NonEmptyText]
    physical_controls: NotRequired[PhysicalControls]
    coastal_band_metres: NotRequired[Annotated[float, Field(ge=0, allow_inf_nan=False)]]
    division_workers: NotRequired[PositiveInt]


@with_config(extra="forbid")
class PhysicalConfiguration(PhysicalControls):
    """Describe the saved request consumed by the standalone physical runner."""

    schema: Literal["raw-physical-pipeline-v3"]
    source_directory: NonEmptyText
    grid: GridSettings
    land_config: LandSettings[RemoteFile]
    inland_water: Annotated[
        InlandWaterSettings[R2ObjectPin], AfterValidator(check_shard_count)
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


def land_dataset_index(layer: LandLayer[RemoteFile]) -> int:
    """Find which pinned coastline file GDAL should open.

    Args:
        layer: Resolved coastline file pins and the dataset's ZIP member path,
            R2 key, or saved Neon source ID.

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
            file.get("r2_key"),
            file.get("source_id"),
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"coastline dataset {dataset!r} must name exactly one entry in files"
        )
    return matches[0]


def iter_physical_source_files(sources: BuildSources) -> Iterator[RawFileReference]:
    """Yield the raw files needed to build the physical grid.

    Args:
        sources: Validated coastline and inland-water settings.

    Yields:
        Water inputs followed by coastline inputs in layer order. A ZIP
        member yields its archive's specification because that is the raw file.
    """
    yield from sources["inland_water"]["files"]
    for layer in sources["land_config"]["land"]:
        for spec in layer["files"]:
            if "archive" in spec:
                yield spec["archive"]
            else:
                yield spec


def physical_catalog_source_ids(sources: BuildSources) -> set[str]:
    """Collect the physical source IDs needed in the saved catalog snapshot.

    Args:
        sources: Coastline and inland-water selections.

    Returns:
        Distinct source IDs, including ZIP containers selected by catalog ID.
    """
    return {
        spec["r2_source"]
        for spec in iter_physical_source_files(sources)
        if "r2_source" in spec
    }


def _resolve_r2_pin(
    file: RawFileReference, catalog: Mapping[str, R2ObjectPin]
) -> R2ObjectPin:
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


def _resolve_coastline_file(
    file: CoastlineFileReference, catalog: Mapping[str, R2ObjectPin]
) -> RemoteFile:
    """Resolve a coastline file or the R2 archive containing it.

    Args:
        file: Coastline file selection.
        catalog: Object pins by ID from the frozen selection.

    Returns:
        A direct R2 pin or a ZIP member with its archive pinned in R2.
    """
    if "archive" in file:
        return {**file, "archive": _resolve_r2_pin(file["archive"], catalog)}
    return _resolve_r2_pin(file, catalog)


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
    catalog: dict[str, R2ObjectPin] = {
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
    layers: list[LandLayer[RemoteFile]] = [
        {
            **layer,
            "files": [
                _resolve_coastline_file(file, catalog) for file in layer["files"]
            ],
        }
        for layer in land["land"]
    ]
    shards = [_resolve_r2_pin(file, catalog) for file in water["files"]]
    controls: PhysicalControls = configuration.get("physical_controls", {})
    return {
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

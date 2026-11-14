"""Import selected source features into existing Neon decision records."""

import time
from typing import Literal, NotRequired, TypedDict

from worldatlas.source_imports.contracts import NonEmptyText, Runtime
from worldatlas.source_imports.atlas_sources.catalog import (
    catalog_source,
    download_source,
    check_source,
)
from worldatlas.source_imports.features.geometry import save_features


class FeatureIdentity(TypedDict):
    feature_id: NonEmptyText
    source_feature_id: NonEmptyText | int


class Selection(FeatureIdentity):
    expected_geometry_sha256: NotRequired[NonEmptyText]


class VectorSelection(Selection):
    collection: NotRequired[bool]
    expected_feature_count: NotRequired[int]


class ParentRelation(TypedDict):
    id: NonEmptyText | int
    version: NonEmptyText | int
    role: str
    expected_tags: NotRequired[dict[str, str]]


class RingAnchor(TypedDict):
    node_id: NonEmptyText | int
    way_id: NonEmptyText | int
    node_version: NonEmptyText | int
    expected_tags: dict[str, str]


class OsmSelection(TypedDict):
    feature_id: NonEmptyText
    source_feature_id: NonEmptyText | int
    object_type: Literal["node", "way", "relation"]
    object_version: NonEmptyText | int
    expected_tags: NotRequired[dict[str, str]]
    expected_geometry_sha256: NotRequired[NonEmptyText]
    parent_relation: NotRequired[ParentRelation]
    ignored_member_roles: NotRequired[list[tuple[Literal["n", "w", "r"], str]]]
    ring_anchors: NotRequired[list[RingAnchor]]
    holes: NotRequired[Literal["preserve", "outer_envelope"]]
    geometry_type: NotRequired[Literal["Polygon", "MultiPolygon"]]


def _build(runtime, reader, arguments):
    started = time.monotonic()
    recipe = runtime.recipe(arguments)
    with runtime.connect() as database:
        with database.transaction():
            source = catalog_source(database, recipe["source_id"])
        timing = {}
        path = download_source(runtime.storage, source, runtime.work_dir, timing=timing)
        features = reader(path, source, recipe)
        check_source(path, source)
        for feature in features:
            feature.update(source_id=source["source_id"])
        with runtime.saving(database):
            hashes = save_features(database, features, recipe)
    elapsed = time.monotonic() - started
    return {
        "geometry_sha256": hashes,
        "source": str(path),
        "timing": {
            "download_seconds": timing.get("download_seconds", 0.0),
            "processing_seconds": elapsed - timing.get("download_seconds", 0.0),
        },
    }


def selected_vector_features(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    basis: NonEmptyText,
    id_field: NonEmptyText,
    selections: list[VectorSelection],
    member: NonEmptyText | None = None,
    layer: NonEmptyText | None = None,
    coordinate_operation: NonEmptyText | None = None,
):
    """Select provider vector features and convert them to WGS84 longitude/latitude."""
    arguments = locals()
    from worldatlas.source_imports.features.vector import read_features

    return _build(
        runtime, lambda path, source, settings: read_features(path, settings), arguments
    )


def selected_table_points(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    basis: NonEmptyText,
    id_field: NonEmptyText,
    longitude_field: NonEmptyText,
    latitude_field: NonEmptyText,
    selections: list[Selection] | None = None,
    member: NonEmptyText | None = None,
    columns: list[NonEmptyText] | None = None,
    delimiter: str = ",",
    encoding: NonEmptyText = "utf-8",
    where: dict[NonEmptyText, str] | None = None,
    feature_id_prefix: NonEmptyText | None = None,
    bounds_lon_lat: tuple[float, float, float, float] | None = None,
):
    """Select provider table points by ID or property matches, optionally within bounds."""
    arguments = locals()
    from worldatlas.source_imports.features.points import read_points

    return _build(
        runtime, lambda path, source, settings: read_points(path, settings), arguments
    )


def selected_osm_features(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    basis: NonEmptyText,
    selections: list[OsmSelection],
):
    """Assemble selected archived OSM nodes, ways and relations."""
    arguments = locals()
    from worldatlas.source_imports.osm.features import read_features

    return _build(
        runtime, lambda path, source, settings: read_features(path, settings), arguments
    )


def s130_areas(
    runtime: Runtime,
    *,
    source_id: NonEmptyText,
    basis: NonEmptyText,
    gml_member: NonEmptyText,
    gml_sha256: NonEmptyText,
    selections: list[FeatureIdentity],
):
    """Import complete S-130 geographic areas, including linked surfaces and holes."""
    arguments = locals()
    from worldatlas.source_imports.iho.areas import read_areas

    return _build(runtime, read_areas, arguments)

"""Import selected source features into Neon.

Constructor signatures define the database contracts. The shared builder
passes the saved arguments to each reader.
"""

import time
from typing import Literal, NotRequired, TypedDict

from worldatlas.source_imports.contracts import NonEmptyText, Runtime, SourceId
from worldatlas.source_assets.catalog import (
    catalog_source,
    download_source,
    check_source,
)
from worldatlas.source_imports.features.geometry import save_features


class FeatureIdentity(TypedDict):
    feature_id: NonEmptyText
    source_feature_id: NonEmptyText | int


class VectorSelection(FeatureIdentity):
    collection: NotRequired[bool]
    expected_feature_count: NotRequired[int]
    polygon_containing: NotRequired[tuple[float, float]]
    holes: NotRequired[Literal["preserve", "outer_envelope"]]


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
    parent_relation: NotRequired[ParentRelation]
    ignored_member_roles: NotRequired[list[tuple[Literal["n", "w", "r"], str]]]
    ring_anchors: NotRequired[list[RingAnchor]]
    holes: NotRequired[Literal["preserve", "outer_envelope"]]
    geometry_type: NotRequired[Literal["Polygon", "MultiPolygon"]]


def _build(runtime, reader):
    started = time.monotonic()
    with runtime.connect() as database:
        with database.transaction():
            source = catalog_source(database, runtime.arguments["source_id"])
        timing = {}
        path = download_source(runtime.storage, source, runtime.work_dir, timing=timing)
        features = reader(path, source, runtime.arguments)
        check_source(path, source)
        with runtime.saving(database):
            hashes = save_features(database, features, construction_id=runtime.recipe_id)
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
    source_id: SourceId,
    basis: NonEmptyText,
    id_field: NonEmptyText,
    selections: list[VectorSelection],
    member: NonEmptyText | None = None,
    layer: NonEmptyText | None = None,
    coordinate_operation: NonEmptyText | None = None,
):
    """Select provider vector features and convert them to WGS84 longitude/latitude."""
    from worldatlas.source_imports.features.vector import read_features

    return _build(runtime, lambda path, source, settings: read_features(path, settings))


def selected_osm_features(
    runtime: Runtime,
    *,
    source_id: SourceId,
    basis: NonEmptyText,
    selections: list[OsmSelection],
):
    """Assemble selected archived OSM nodes, ways and relations."""
    from worldatlas.source_imports.osm.features import read_features

    return _build(runtime, lambda path, source, settings: read_features(path, settings))


def s130_areas(
    runtime: Runtime,
    *,
    source_id: SourceId,
    basis: NonEmptyText,
    gml_member: NonEmptyText,
    gml_sha256: NonEmptyText,
    selections: list[FeatureIdentity],
):
    """Import complete S-130 geographic areas, including linked surfaces and holes."""
    from worldatlas.source_imports.iho.areas import read_areas

    return _build(runtime, read_areas)

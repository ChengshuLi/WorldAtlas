"""Import selected points and areas from an archived OpenStreetMap extract."""

import json
import time
from typing import Literal, NotRequired, TypedDict

import osmium

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features


class OsmSelection(TypedDict):
    """Identify an OSM object in one archived extract."""

    # ID of the feature saved in Neon.
    feature_id: NonEmptyText
    # ID of the OSM object in the archived extract.
    source_feature_id: NonEmptyText | int
    # OSM nodes produce points. Closed ways and polygon relations produce areas.
    object_type: Literal["node", "way", "relation"]
    # Optional OSM tag names and values that the selected object must match.
    expected_tags: NotRequired[dict[str, str]]


OBJECT_TYPES = {"node": "n", "way": "w", "relation": "r"}


def read_features(path, selections):
    """Read selected OSM points and assemble areas through Osmium.

    Args:
        path: Verified local OSM extract.
        selections: Unique object types and IDs, with optional tag checks.

    Returns:
        Selected features in recipe order, with output IDs and geometries.

    Raises:
        ValueError: A selected object is missing, duplicated, or invalid.
    """
    # Index selections by OSM identity. Insertion order also gives the output order.
    requested = {}
    for selection in selections:
        kind = OBJECT_TYPES.get(selection["object_type"])
        if kind is None:
            raise ValueError("unsupported selected OSM object type")
        key = kind, int(selection["source_feature_id"])
        if key in requested:
            raise ValueError(f"OSM {selection['object_type']} {key[1]} is selected more than once")
        requested[key] = selection

    # Relation assembly also loads node locations for any selected ways.
    processor = osmium.FileProcessor(str(path))
    if any(kind == "r" for kind, _ in requested):
        processor = processor.with_areas()
    elif any(kind == "w" for kind, _ in requested):
        processor = processor.with_locations()
    factory = osmium.geom.GeoJSONFactory()
    seen, geometries = set(), {}
    for obj in processor:
        if obj.is_area():
            # Osmium gives each assembled area a synthetic ID. Match its source relation.
            key = "r", obj.orig_id()
            if not obj.from_way() and key in requested:
                try:
                    geometries[key] = json.loads(factory.create_multipolygon(obj))
                except RuntimeError as error:
                    raise ValueError(f"Osmium returned an invalid area for {key}") from error
            continue

        # The original object supplies its identity and tags.
        key = obj.type_str(), obj.id
        if key not in requested:
            continue
        if obj.id <= 0 or key in seen:
            raise ValueError(f"duplicate or invalid selected OSM object {key}")
        if obj.deleted:
            raise ValueError(f"selected OSM object {key} is deleted")
        seen.add(key)
        if any(
            obj.tags.get(name) != value
            for name, value in requested[key].get("expected_tags", {}).items()
        ):
            raise ValueError(f"selected OSM identity tags differ for {key}")
        if obj.is_node():
            if not obj.location.valid():
                raise ValueError(f"selected OSM node {obj.id} has no valid coordinates")
            geometries[key] = json.loads(factory.create_point(obj.location))
        elif obj.is_way():
            if not obj.is_closed():
                raise ValueError(f"selected OSM way {obj.id} is open")
            # The recipe can select a closed way even when its tags do not mark it as an area.
            try:
                ring = json.loads(factory.create_linestring(obj.nodes))["coordinates"]
            except (RuntimeError, osmium.InvalidLocationError) as error:
                raise ValueError(f"Osmium could not read the outline of {key}") from error
            geometries[key] = {"type": "MultiPolygon", "coordinates": [[ring]]}
        elif obj.is_relation() and any(
            (member.type, member.role) not in (("w", "outer"), ("w", "inner"), ("n", "label"))
            for member in obj.members
        ):
            raise ValueError(f"unsupported member role in selected OSM relation {obj.id}")

    for key in requested:
        if key not in seen:
            raise ValueError(f"selected OSM object {key} is missing")
        # A relation may be present even when its members are too incomplete to form an area.
        if key not in geometries:
            raise ValueError(f"Osmium could not assemble selected OSM area {key}")
        geometry = geometries[key]
        validate_geometry(geometry)
        if key[0] != "n" and any(
            abs(a[0] - b[0]) > 180
            for polygon in geometry["coordinates"]
            for ring in polygon
            for a, b in zip(ring, ring[1:])
        ):
            raise ValueError("OSM ring crosses the longitude seam; an explicit wrapped construction is needed")

    return [
        dict(
            feature_id=selection["feature_id"],
            source_feature_id=selection["source_feature_id"],
            geometry=geometries[key],
        )
        for key, selection in requested.items()
    ]


def selected_osm_features(
    runtime: Runtime,
    *,
    source_id: SourceId,
    selections: list[OsmSelection],
):
    """Import selected OSM nodes, closed ways, and relation polygons.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the archived OSM extract.
        selections: Provider objects, output IDs, and optional tag checks.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    feature_ids = save_features(runtime, read_features(path, selections))
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))

"""Construct selected OSM points and polygons from one archived object graph."""

from collections import defaultdict
from dataclasses import dataclass, field
import time
from typing import Literal, NotRequired, TypedDict

import osmium
from shapely import union_all
from shapely.geometry import Polygon, mapping, shape

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


@dataclass
class Graph:
    """Hold the nodes, ways, and relations from one archived OSM extract."""

    nodes: dict = field(default_factory=dict)
    ways: dict = field(default_factory=dict)
    relations: dict = field(default_factory=dict)


def read_graph(path):
    """Read one OSM extract and omit label nodes from relation memberships.

    Args:
        path: Local extract understood by osmium.

    Returns:
        Nodes, ways, and relations keyed by their provider object IDs.

    Raises:
        ValueError: An object ID, tag, or node position is invalid.
    """
    graph = Graph()

    class Reader(osmium.SimpleHandler):
        def record(self, obj, records, **values):
            if obj.id in records or obj.id <= 0:
                raise ValueError("duplicate or invalid OSM object ID")
            tags = dict(obj.tags)
            if len(tags) != len(obj.tags):
                raise ValueError("duplicate OSM tag")
            records[obj.id] = dict(tags=tags, deleted=obj.deleted, **values)

        def node(self, obj):
            if not obj.location.valid():
                raise ValueError("OSM node has no valid coordinates")
            self.record(
                obj, graph.nodes, coordinates=[obj.location.lon, obj.location.lat]
            )

        def way(self, obj):
            self.record(obj, graph.ways, nodes=[n.ref for n in obj.nodes])

        def relation(self, obj):
            self.record(
                obj,
                graph.relations,
                # Label nodes position map text and do not form polygon outlines.
                members=[
                    (m.type, m.ref, m.role)
                    for m in obj.members
                    if (m.type, m.role) != ("n", "label")
                ],
            )

    Reader().apply_file(str(path))
    return graph


def assemble_rings(ways):
    """Join way endpoints into closed rings in stable provider-ID order.

    Args:
        ways: Mapping from way IDs to ordered node IDs.

    Returns:
        Closed rings of node IDs.

    Raises:
        ValueError: The ways don't form complete, unambiguous rings.
    """
    owners, rings, remaining = defaultdict(list), [], set()
    for ident, nodes in ways.items():
        if len(nodes) < 2:
            raise ValueError("short OSM way")
        if nodes[0] == nodes[-1]:
            rings.append((ident, list(nodes)))
        else:
            owners[nodes[0]].append(ident)
            owners[nodes[-1]].append(ident)
            remaining.add(ident)
    if any(len(items) != 2 for items in owners.values()):
        raise ValueError("open or branched OSM ring")
    while remaining:
        first = min(remaining)
        ring = list(ways[first])
        remaining.remove(first)
        while ring[0] != ring[-1]:
            choices = [i for i in owners[ring[-1]] if i in remaining]
            if len(choices) != 1:
                raise ValueError("incomplete or ambiguous OSM ring")
            ident = choices[0]
            remaining.remove(ident)
            part = ways[ident]
            ring.extend(part[1:] if part[0] == ring[-1] else reversed(part[:-1]))
        rings.append((first, ring))
    result = [ring for _, ring in sorted(rings)]
    if not result or any(
        len(r) < 4 or r[0] != r[-1] or any(a == b for a, b in zip(r, r[1:]))
        for r in result
    ):
        raise ValueError("invalid OSM ring")
    return result


def selected_object(records, ident, tags):
    """Read the selected object after checking its identity and attributes.

    Args:
        records: Archive objects keyed by integer ID.
        ident: Selected object ID.
        tags: Expected values for selected provider tags.

    Returns:
        The matching object record.

    Raises:
        ValueError: The object is missing, deleted, or fails an identity check.
    """
    record = records.get(int(ident))
    if record is None or record["deleted"]:
        raise ValueError("selected OSM object is missing")
    if any(record["tags"].get(key) != value for key, value in tags.items()):
        raise ValueError("selected OSM identity tags differ")
    return record


def polygon_geometry(graph, selected, record, ancestry=()):
    """Assemble the complete selected polygon, preserving its holes.

    Args:
        graph: Nodes, ways, and relations from the archived extract.
        selected: Selected object type and ID.
        record: Chosen OSM way or relation.
        ancestry: Parent relation IDs used to detect cycles.

    Returns:
        The selected GeoJSON MultiPolygon.
    """
    if selected["object_type"] == "relation" and record["tags"].get("type") in (
        "group",
        "collection",
    ):
        return group_geometry(graph, selected, record, ancestry)
    if selected["object_type"] == "way":
        outer = {int(selected["source_feature_id"]): record["nodes"]}
        inner = {}
    else:
        outer, inner = {}, {}
        for kind, ident, role in record["members"]:
            if kind == "w" and role in ("outer", "inner"):
                target = outer if role == "outer" else inner
                if ident in outer or ident in inner or ident not in graph.ways:
                    raise ValueError("duplicate or missing geometric OSM member")
                if graph.ways[ident]["deleted"]:
                    raise ValueError("selected OSM member is deleted")
                target[ident] = graph.ways[ident]["nodes"]
            else:
                raise ValueError("unsupported OSM geometric or metadata member role")
    rings = assemble_rings(outer)
    holes = assemble_rings(inner) if inner else []

    def coordinates(ring):
        if any(n not in graph.nodes or graph.nodes[n]["deleted"] for n in ring):
            raise ValueError("OSM ring has missing nodes")
        points = [list(graph.nodes[n]["coordinates"]) for n in ring]
        if any(abs(a[0] - b[0]) > 180 for a, b in zip(points, points[1:])):
            raise ValueError(
                "OSM ring crosses the longitude seam; an explicit wrapped construction is needed"
            )
        return points

    polygons = [[coordinates(ring)] for ring in rings]
    for hole in holes:
        points = coordinates(hole)
        owners = [
            polygon
            for polygon in polygons
            if Polygon(polygon[0]).contains(Polygon(points))
        ]
        if len(owners) != 1:
            raise ValueError("OSM inner ring needs exactly one containing outer ring")
        owners[0].append(points)
    geometry = {"type": "MultiPolygon", "coordinates": polygons}
    validate_geometry(geometry)
    return geometry


def group_geometry(graph, selected, record, ancestry):
    """Union the polygon members of a provider-defined geographic group.

    Args:
        graph: Nodes, ways, and relations from the archived extract.
        selected: Selected relation ID.
        record: Chosen OSM group or collection relation.
        ancestry: Parent relation IDs used to detect cycles.

    Returns:
        The combined GeoJSON MultiPolygon.
    """
    ident = int(selected["source_feature_id"])
    if ident in ancestry:
        raise ValueError("cyclic OSM geographic group")
    ancestry = (*ancestry, ident)
    polygons, ways = [], []
    for kind, member, role in record["members"]:
        records = {"n": graph.nodes, "w": graph.ways, "r": graph.relations}[kind]
        if member not in records or records[member]["deleted"]:
            raise ValueError("missing OSM group member")
        if kind == "w" and role in ("", "outer"):
            ways.append(("w", member, "outer"))
        elif kind == "r" and role in ("", "outer"):
            child = dict(
                object_type="relation",
                source_feature_id=str(member),
            )
            polygons.append(
                shape(polygon_geometry(graph, child, records[member], ancestry))
            )
        else:
            raise ValueError("unsupported OSM geographic group member role")
    if ways:
        direct = dict(object_type="relation", source_feature_id=str(ident))
        polygons.append(
            shape(
                polygon_geometry(
                    graph, direct, dict(tags={"type": "multipolygon"}, members=ways)
                )
            )
        )
    if not polygons:
        raise ValueError("OSM geographic group has no polygon members")
    result = union_all(polygons)
    if result.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError("OSM geographic group needs polygon geometry")
    coordinates = mapping(result)["coordinates"]
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [coordinates] if result.geom_type == "Polygon" else coordinates,
    }
    validate_geometry(geometry)
    return geometry


def read_features(path, selections):
    """Assemble the selected points and polygons from an archived OSM graph.

    Args:
        path: Verified local OSM extract.
        selections: Object types and IDs, with optional tag checks.

    Returns:
        Selected features with their output IDs, provider IDs, and geometries.
    """
    graph = read_graph(path)
    result = []
    for selection in selections:
        kind = selection["object_type"]
        objects = {"node": graph.nodes, "way": graph.ways, "relation": graph.relations}
        if kind not in objects:
            raise ValueError("unsupported selected OSM object type")
        record = selected_object(
            objects[kind],
            selection["source_feature_id"],
            selection.get("expected_tags", {}),
        )
        geometry = (
            {"type": "Point", "coordinates": list(record["coordinates"])}
            if kind == "node"
            else polygon_geometry(graph, selection, record)
        )
        validate_geometry(geometry)
        result.append(
            dict(
                feature_id=selection["feature_id"],
                source_feature_id=selection["source_feature_id"],
                geometry=geometry,
            )
        )
    return result


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

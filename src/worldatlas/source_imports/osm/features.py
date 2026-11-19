"""Construct selected OSM points and polygons from one archived object graph."""

from collections import defaultdict
from dataclasses import dataclass, field
import time
from typing import Literal, NotRequired, TypedDict

import osmium
from shapely.geometry import Polygon

from worldatlas.geodesy.geojson import validate_geometry
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import feature_result, save_features


class ParentRelation(TypedDict):
    """Require membership in an exact archived OSM relation."""

    id: NonEmptyText | int
    version: NonEmptyText | int
    role: str
    expected_tags: NotRequired[dict[str, str]]


class RingAnchor(TypedDict):
    """Select an outer ring by its tagged node and member way."""

    node_id: NonEmptyText | int
    way_id: NonEmptyText | int
    node_version: NonEmptyText | int
    expected_tags: dict[str, str]


class OsmSelection(TypedDict):
    """Select a versioned OSM object and how to interpret its geometry."""

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


@dataclass
class Graph:
    """Hold the nodes, ways, and relations from one archived OSM extract."""

    nodes: dict = field(default_factory=dict)
    ways: dict = field(default_factory=dict)
    relations: dict = field(default_factory=dict)


def read_graph(path):
    """Read one OSM extract while preserving object versions and tags.

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
            records[obj.id] = dict(
                version=str(obj.version), tags=tags, deleted=obj.deleted, **values
            )

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
                members=[(m.type, m.ref, m.role) for m in obj.members],
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


def selected_object(records, ident, version, tags):
    """Read the selected object after checking its identity and attributes.

    Args:
        records: Archive objects keyed by integer ID.
        ident: Selected object ID.
        version: Expected archive object version.
        tags: Expected values for selected provider tags.

    Returns:
        The matching object record.

    Raises:
        ValueError: The object is missing, deleted, or fails an identity check.
    """
    if isinstance(version, float) and version.is_integer():
        version = int(version)
    record = records.get(int(ident))
    if record is None or record["deleted"] or record["version"] != str(version):
        raise ValueError("selected OSM object or version is missing")
    if any(record["tags"].get(key) != value for key, value in tags.items()):
        raise ValueError("selected OSM identity tags differ")
    return record


def polygon_geometry(graph, selected, record, ancestry=()):
    """Assemble a source polygon with its selected rings and hole treatment.

    Args:
        graph: Nodes, ways, and relations from the archived extract.
        selected: Geometry type, member roles, and optional ring selections.
        record: Chosen OSM way or relation.
        ancestry: Parent relation IDs used to detect cycles.

    Returns:
        The selected GeoJSON polygon or multipolygon.
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
        ignored = {tuple(item) for item in selected.get("ignored_member_roles", [])}
        for kind, ident, role in record["members"]:
            if kind == "w" and role in ("outer", "inner"):
                target = outer if role == "outer" else inner
                if ident in outer or ident in inner or ident not in graph.ways:
                    raise ValueError("duplicate or missing geometric OSM member")
                if graph.ways[ident]["deleted"]:
                    raise ValueError("selected OSM member is deleted")
                target[ident] = graph.ways[ident]["nodes"]
            elif (kind, role) in ignored:
                records = {"n": graph.nodes, "w": graph.ways, "r": graph.relations}[
                    kind
                ]
                if ident not in records or records[ident]["deleted"]:
                    raise ValueError("selected OSM metadata member is missing")
            else:
                raise ValueError("unsupported OSM geometric or metadata member role")
    rings = assemble_rings(outer)
    holes = assemble_rings(inner) if inner else []
    chosen = None
    if anchors := selected.get("ring_anchors"):
        chosen = []
        for anchor in sorted(anchors, key=lambda a: int(a["node_id"])):
            node, way = int(anchor["node_id"]), int(anchor["way_id"])
            selected_object(
                graph.nodes, node, anchor["node_version"], anchor["expected_tags"]
            )
            if [ident for ident, refs in outer.items() if node in refs] != [
                way
            ] or outer[way].count(node) != 1:
                raise ValueError(
                    "OSM anchor must belong to exactly its selected outer way"
                )
            matches = [ring for ring in rings if ring.count(node) == 1]
            if len(matches) != 1 or matches[0] in chosen:
                raise ValueError("OSM anchor does not select one distinct ring")
            chosen.append(matches[0])

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
    complete = {"type": "MultiPolygon", "coordinates": polygons}
    validate_geometry(complete)
    if chosen is not None:
        polygons = [polygons[rings.index(ring)] for ring in chosen]
    treatment = selected.get("holes", "preserve")
    if treatment == "outer_envelope":
        polygons = [[polygon[0]] for polygon in polygons]
    elif treatment != "preserve":
        raise ValueError("unsupported OSM hole treatment")
    kind = selected.get("geometry_type", "MultiPolygon")
    if kind == "Polygon" and len(polygons) == 1:
        return {"type": kind, "coordinates": polygons[0]}
    if kind != "MultiPolygon":
        raise ValueError("polygon output needs one polygon or a multipolygon")
    return {"type": kind, "coordinates": polygons}


def group_geometry(graph, selected, record, ancestry):
    """Union the polygon members of a provider-defined geographic group.

    Args:
        graph: Nodes, ways, and relations from the archived extract.
        selected: Geometry type, ignored roles, and hole treatment.
        record: Chosen OSM group or collection relation.
        ancestry: Parent relation IDs used to detect cycles.

    Returns:
        The combined GeoJSON polygon or multipolygon.
    """
    from shapely import union_all
    from shapely.geometry import mapping, shape

    ident = int(selected["source_feature_id"])
    if ident in ancestry:
        raise ValueError("cyclic OSM geographic group")
    ancestry = (*ancestry, ident)
    ignored = {tuple(item) for item in selected.get("ignored_member_roles", [])}
    polygons, ways = [], []
    for kind, member, role in record["members"]:
        records = {"n": graph.nodes, "w": graph.ways, "r": graph.relations}[kind]
        if member not in records or records[member]["deleted"]:
            raise ValueError("missing OSM group member")
        if (kind, role) in ignored:
            continue
        if kind == "w" and role in ("", "outer"):
            ways.append(("w", member, "outer"))
        elif kind == "r" and role in ("", "outer"):
            child = dict(
                object_type="relation",
                source_feature_id=str(member),
                ignored_member_roles=selected.get("ignored_member_roles", []),
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
    geometry = mapping(result)
    if selected.get("holes", "preserve") == "outer_envelope":
        parts = (
            [geometry["coordinates"]]
            if result.geom_type == "Polygon"
            else geometry["coordinates"]
        )
        geometry = dict(type="MultiPolygon", coordinates=[[part[0]] for part in parts])
    elif selected.get("holes", "preserve") != "preserve":
        raise ValueError("unsupported OSM hole treatment")
    if selected.get("ring_anchors"):
        raise ValueError(
            "ring anchors apply to individual polygons, not geographic groups"
        )
    wanted = selected.get("geometry_type", "MultiPolygon")
    if geometry["type"] == "Polygon" and wanted == "MultiPolygon":
        geometry = dict(type="MultiPolygon", coordinates=[geometry["coordinates"]])
    elif (
        geometry["type"] == "MultiPolygon"
        and wanted == "Polygon"
        and len(geometry["coordinates"]) == 1
    ):
        geometry = dict(type="Polygon", coordinates=geometry["coordinates"][0])
    if geometry["type"] != wanted:
        raise ValueError("group does not have the requested polygon type")
    validate_geometry(geometry)
    return geometry


def read_features(path, selections):
    """Assemble the selected points and polygons from an archived OSM graph.

    Args:
        path: Verified local OSM extract.
        selections: Provider object IDs, versions, and geometry options.

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
            selection["object_version"],
            selection.get("expected_tags", {}),
        )
        if parent := selection.get("parent_relation"):
            relation = selected_object(
                graph.relations,
                parent["id"],
                parent["version"],
                parent.get("expected_tags", {}),
            )
            member = (
                {"node": "n", "way": "w", "relation": "r"}[kind],
                int(selection["source_feature_id"]),
                parent["role"],
            )
            if relation["members"].count(member) != 1:
                raise ValueError(
                    "selected OSM object must be one member of its selected parent"
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
    basis: NonEmptyText,
    selections: list[OsmSelection],
):
    """Import selected OSM nodes, closed ways, and relation polygons.

    Args:
        runtime: Import resources and saved recipe snapshot.
        source_id: Catalog ID of the archived OSM extract.
        basis: Human-readable explanation retained in the recipe.
        selections: Provider objects and their output IDs and options.

    Returns:
        Saved feature IDs, the local source path, and timings.
    """
    started, timing = time.monotonic(), {}
    path, = acquire_sources(runtime, [source_id], timing=timing)
    feature_ids = save_features(runtime, read_features(path, selections))
    return feature_result(feature_ids, time.monotonic() - started, source=path,
                          download_seconds=timing.get("download_seconds", 0.0))

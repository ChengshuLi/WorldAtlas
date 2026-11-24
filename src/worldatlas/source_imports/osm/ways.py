"""Assemble boundary geometry from individual OpenStreetMap way responses."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from shapely import line_merge
from shapely.geometry import MultiLineString

from worldatlas.shared.files import read_json
from worldatlas.shared.text import NonEmptyText
from worldatlas.source_imports.shared.recipe_types import SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import save_features


def _read_way_sources(
    paths: Iterable[Path],
) -> tuple[dict[int, tuple[float, ...]], dict[int, list[int]]]:
    """Read the nodes and ways from a set of archived OSM responses.

    Args:
        paths: Verified local archives containing one OSM way each.

    Returns:
        A pair of dictionaries keyed by OSM ID. Nodes map to longitude and
        latitude pairs, and ways map to ordered node IDs.

    Raises:
        ValueError: A response contains an invalid way or conflicting data.
    """
    nodes, ways = {}, {}
    for path in paths:
        elements = read_json(path)['elements']
        source_ways = [element for element in elements if element['type'] == 'way']
        if len(source_ways) != 1:
            raise ValueError('each source must contain exactly one OSM way')
        (way,) = source_ways
        way_id, node_ids = way['id'], way['nodes']
        if (
            type(way_id) is not int
            or len(node_ids) < 2
            or any(type(node) is not int for node in node_ids)
        ):
            raise ValueError('invalid OSM way')
        if way_id in ways:
            raise ValueError(f'duplicate OSM way {way_id}')
        ways[way_id] = node_ids
        for element in elements:
            if element['type'] != 'node':
                continue
            node_id = element['id']
            longitude, latitude = element['lon'], element['lat']
            point = longitude, latitude
            if any(type(value) not in (int, float) for value in point) or not (
                -180 <= longitude <= 180 and -90 <= latitude <= 90
            ):
                raise ValueError('invalid node coordinates')
            if node_id in nodes and nodes[node_id] != point:
                raise ValueError('conflicting node coordinates')
            nodes[node_id] = point
    return nodes, ways


def assemble(paths: Iterable[Path]) -> dict[str, Any]:
    """Merge selected ways into one open boundary.

    Args:
        paths: Verified local archives containing one OSM way each.

    Returns:
        GeoJSON LineString starting at the endpoint with the lower OSM ID.

    Raises:
        ValueError: The selected ways cannot form one valid open chain.
    """
    nodes, ways = _read_way_sources(paths)
    if not ways:
        raise ValueError('missing way inputs')
    parts = []
    for node_ids in ways.values():
        try:
            coordinates = [nodes[node] for node in node_ids]
        except KeyError as error:
            raise ValueError('missing node in selected OSM way') from error
        if any(a == b for a, b in zip(coordinates, coordinates[1:])):
            raise ValueError('duplicate adjacent coordinates')
        parts.append(coordinates)
    # Shapely joins equal coordinates. Require each endpoint to identify one OSM node.
    endpoints = {
        node for node_ids in ways.values() for node in (node_ids[0], node_ids[-1])
    }
    endpoint_ids = {nodes[node]: node for node in endpoints}
    if len(endpoint_ids) != len(endpoints):
        raise ValueError('distinct OSM endpoints share coordinates')
    line = line_merge(MultiLineString(parts))
    if line.geom_type != 'LineString' or line.is_closed:
        raise ValueError('ways must form one open, unbranched chain')
    if not line.is_simple:
        raise ValueError('assembled boundary has a self-intersection')
    coords = list(line.coords)
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(coords, coords[1:])):
        raise ValueError('antimeridian-crossing boundaries require a split source line')
    if endpoint_ids[coords[0]] > endpoint_ids[coords[-1]]:
        coords.reverse()
    return {'type': 'LineString', 'coordinates': [list(point) for point in coords]}


def osm_way_chain(
    runtime: Runtime,
    *,
    way_source_ids: list[SourceId],
    feature_id: NonEmptyText,
    evidence_source_ids: list[SourceId] | None = None,
) -> dict[str, str | int]:
    """Join archived OSM ways into one boundary and save their coordinates.

    Args:
        runtime: Import resources and saved recipe snapshot.
        way_source_ids: Distinct catalog IDs of the archived ways.
        feature_id: Output feature ID in Neon.
        evidence_source_ids: Additional raw sources cited for provenance.

    Returns:
        Saved feature ID and vertex count.

    Raises:
        ValueError: The source files, assembled line, or save fails validation.
    """
    # The saved recipe links its evidence to the catalog. Read only the ways.
    paths = acquire_sources(runtime, way_source_ids)
    geometry = assemble(paths)
    save_features(runtime, [{"feature_id": feature_id, "geometry": geometry}])
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']))

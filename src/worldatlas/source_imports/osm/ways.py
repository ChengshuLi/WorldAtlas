"""Assemble boundary geometry from individual OpenStreetMap way responses."""
import json
import math
from collections import Counter

from shapely import line_merge
from shapely.geometry import MultiLineString
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import save_features


def assemble(paths):
    """Traverse one open chain from its lower-ID endpoint.

    Args:
        paths: Verified local archives containing one OSM way each.

    Returns:
        GeoJSON LineString with the archived coordinates in chain order.

    Raises:
        ValueError: The selected ways cannot form one valid open chain.
    """
    nodes, ways = {}, {}
    for path in paths:
        with path.open(encoding='utf-8') as source:
            elements = json.load(source)['elements']
        found = [element for element in elements if element['type'] == 'way']
        if len(found) != 1:
            raise ValueError('each source must contain exactly one OSM way')
        way, = found
        way_id, refs = way['id'], way['nodes']
        if type(way_id) is not int or len(refs) < 2 or any(type(ref) is not int for ref in refs):
            raise ValueError('invalid OSM way')
        if way_id in ways:
            raise ValueError(f'duplicate OSM way {way_id}')
        ways[way_id] = refs
        for e in elements:
            if e['type'] == 'node':
                point = (e['lon'], e['lat'])
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in point) or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                    raise ValueError('invalid node coordinates')
                if e['id'] in nodes and nodes[e['id']] != point:
                    raise ValueError('conflicting node coordinates')
                nodes[e['id']] = point
    if not ways:
        raise ValueError('missing way inputs')
    ends = Counter(node for refs in ways.values() for node in (refs[0], refs[-1]))
    terminals = [node for node, count in ends.items() if count == 1]
    if len(terminals) != 2 or any(count > 2 for count in ends.values()):
        raise ValueError('ways do not form one unbranched chain')
    parts = []
    for refs in ways.values():
        if any(node not in nodes for node in refs):
            raise ValueError('missing node in selected OSM way')
        coordinates = [nodes[node] for node in refs]
        if any(a == b for a, b in zip(coordinates, coordinates[1:])):
            raise ValueError('duplicate adjacent coordinates')
        parts.append(coordinates)
    # Shapely merges by coordinate. Require each endpoint coordinate to identify one OSM node.
    if len({nodes[node] for node in ends}) != len(ends):
        raise ValueError('distinct OSM endpoints share coordinates')
    line = line_merge(MultiLineString(parts))
    if line.geom_type != 'LineString':
        raise ValueError('disconnected OSM ways')
    if not line.is_simple:
        raise ValueError('assembled boundary has a self-intersection')
    coords = list(line.coords)
    # Choose a stable coordinate order even if Shapely starts at the other endpoint.
    if coords[0] != nodes[min(terminals)]:
        coords.reverse()
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(coords, coords[1:])):
        raise ValueError('antimeridian-crossing boundaries require a split source line')
    return {'type': 'LineString', 'coordinates': [list(point) for point in coords]}


def osm_way_chain(
    runtime: Runtime, *, way_source_ids: list[SourceId],
    feature_id: NonEmptyText,
    evidence_source_ids: list[SourceId] | None = None,
):
    """Join archived OSM ways into one boundary and save their coordinates.

    Args:
        runtime: Import resources and saved recipe snapshot.
        way_source_ids: Distinct catalog IDs of the archived ways.
        feature_id: Output feature ID in Neon.
        evidence_source_ids: Additional raw sources cited for provenance.

    Returns:
        Saved feature ID and vertex count.
    """
    if not way_source_ids or len(set(way_source_ids)) != len(way_source_ids):
        raise ValueError('way_source_ids must list distinct OSM way sources')
    paths = acquire_sources(runtime, way_source_ids, evidence_source_ids=evidence_source_ids or ())
    geometry = assemble(paths)
    save_features(runtime, [dict(feature_id=feature_id, geometry=geometry)])
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']))

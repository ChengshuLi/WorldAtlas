"""Assemble boundary geometry from individual OpenStreetMap way responses."""
import json
import math
from collections import defaultdict

from shapely.geometry import LineString
from worldatlas.source_imports.shared.contracts import NonEmptyText, SourceId
from worldatlas.source_imports.shared.runtime import Runtime
from worldatlas.source_imports.shared.sources import acquire_sources
from worldatlas.source_imports.shared.storage import save_features, storage_geometry


def assemble(paths, start_node_id):
    """Traverse one open chain starting at the specified endpoint.

    Args:
        paths: Verified local archives containing one OSM way each.
        start_node_id: The first node of the final line.

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
    ends = defaultdict(list)
    for way_id, refs in ways.items():
        ends[refs[0]].append(way_id)
        ends[refs[-1]].append(way_id)
    terminals = [n for n, refs in ends.items() if len(refs) == 1]
    if len(terminals) != 2 or any(len(refs) > 2 for refs in ends.values()):
        raise ValueError('ways do not form one unbranched chain')
    start = start_node_id
    if start not in terminals:
        raise ValueError('start node is not a chain terminal')
    current, remaining, chain = start, set(ways), []
    while remaining:
        candidates = [i for i in ends[current] if i in remaining]
        if len(candidates) != 1:
            raise ValueError('disconnected or ambiguous chain')
        way_id = candidates[0]
        remaining.remove(way_id)
        refs = ways[way_id]
        refs = refs if refs[0] == current else refs[::-1]
        chain.extend(refs if not chain else refs[1:])
        current = refs[-1]
    if current == start or current not in terminals or any(n not in nodes for n in chain):
        raise ValueError('invalid terminal or missing node')
    if len(set(chain)) != len(chain):
        raise ValueError('boundary revisits a node')
    coords = [[float(v) for v in nodes[n]] for n in chain]
    if any(a == b for a, b in zip(coords, coords[1:])):
        raise ValueError('duplicate adjacent coordinates')
    line = LineString(coords)
    if line.is_closed:
        raise ValueError('assembled boundary must be open')
    if not line.is_simple:
        raise ValueError('assembled boundary has a self-intersection')
    if any(abs(a[0] - b[0]) > 180 for a, b in zip(coords, coords[1:])):
        raise ValueError('antimeridian-crossing boundaries require a split source line')
    return storage_geometry({'type': 'LineString', 'coordinates': coords})


def osm_way_chain(
    runtime: Runtime, *, way_source_ids: list[SourceId], start_node_id: int,
    feature_id: NonEmptyText, basis: NonEmptyText,
    evidence_source_ids: list[SourceId] | None = None,
):
    """Join archived OSM ways into one boundary and save their coordinates.

    Args:
        runtime: Import resources and saved recipe snapshot.
        way_source_ids: Distinct catalog IDs of the archived ways.
        start_node_id: Endpoint that starts the final chain.
        feature_id: Output feature ID in Neon.
        basis: Human-readable explanation retained in the recipe.
        evidence_source_ids: Additional raw sources cited for provenance.

    Returns:
        Saved feature ID, vertex count, and geometry checksum.
    """
    if not way_source_ids or len(set(way_source_ids)) != len(way_source_ids):
        raise ValueError('way_source_ids must list distinct OSM way sources')
    paths = acquire_sources(runtime, way_source_ids, evidence_source_ids=evidence_source_ids or ())
    geometry = assemble(paths, start_node_id)
    hashes = save_features(runtime, [dict(feature_id=feature_id, geometry=geometry)])
    return dict(feature_id=feature_id, vertices=len(geometry['coordinates']), sha256=hashes[feature_id])

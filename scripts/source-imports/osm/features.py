"""Construct selected OSM points and polygons from one archived object graph."""
from collections import defaultdict
from dataclasses import dataclass, field

import osmium
from shapely.geometry import Polygon

from features.geometry import geometry_hash, validate_geometry


@dataclass
class Graph:
    nodes: dict = field(default_factory=dict)
    ways: dict = field(default_factory=dict)
    relations: dict = field(default_factory=dict)


def read_graph(path):
    graph = Graph()

    class Reader(osmium.SimpleHandler):
        def record(self, obj, records, **values):
            if obj.id in records or obj.id <= 0:
                raise ValueError('duplicate or invalid OSM object ID')
            tags = dict(obj.tags)
            if len(tags) != len(obj.tags):
                raise ValueError('duplicate OSM tag')
            records[obj.id] = dict(version=str(obj.version), tags=tags,
                                   deleted=obj.deleted, **values)

        def node(self, obj):
            if not obj.location.valid():
                raise ValueError('OSM node has no valid coordinates')
            self.record(obj, graph.nodes, coordinates=[obj.location.lon, obj.location.lat])

        def way(self, obj):
            self.record(obj, graph.ways, nodes=[n.ref for n in obj.nodes])

        def relation(self, obj):
            self.record(obj, graph.relations,
                        members=[(m.type, m.ref, m.role) for m in obj.members])

    Reader().apply_file(str(path))
    return graph


def assemble_rings(ways):
    """Follow degree-two way endpoints in stable provider-ID order."""
    owners, rings, remaining = defaultdict(list), [], set()
    for ident, nodes in ways.items():
        if len(nodes) < 2:
            raise ValueError('short OSM way')
        if nodes[0] == nodes[-1]:
            rings.append((ident, list(nodes)))
        else:
            owners[nodes[0]].append(ident)
            owners[nodes[-1]].append(ident)
            remaining.add(ident)
    if any(len(items) != 2 for items in owners.values()):
        raise ValueError('open or branched OSM ring')
    while remaining:
        first = min(remaining)
        ring = list(ways[first])
        remaining.remove(first)
        while ring[0] != ring[-1]:
            choices = [i for i in owners[ring[-1]] if i in remaining]
            if len(choices) != 1:
                raise ValueError('incomplete or ambiguous OSM ring')
            ident = choices[0]
            remaining.remove(ident)
            part = ways[ident]
            ring.extend(part[1:] if part[0] == ring[-1] else reversed(part[:-1]))
        rings.append((first, ring))
    result = [ring for _, ring in sorted(rings)]
    if not result or any(len(r) < 4 or r[0] != r[-1]
                         or any(a == b for a, b in zip(r, r[1:])) for r in result):
        raise ValueError('invalid OSM ring')
    return result


def selected_object(records, ident, version, tags):
    record = records.get(int(ident))
    if record is None or record['deleted'] or record['version'] != str(version):
        raise ValueError('selected OSM object or version is missing')
    if any(record['tags'].get(key) != value for key, value in tags.items()):
        raise ValueError('selected OSM identity tags differ')
    return record


def polygon_geometry(graph, selected, record):
    """Assemble source rings; choices about envelopes and anchors are data."""
    if selected['object_type'] == 'way':
        outer = {int(selected['source_feature_id']): record['nodes']}
        inner = {}
    else:
        outer, inner = {}, {}
        ignored = {tuple(item) for item in selected.get('ignored_member_roles', [])}
        for kind, ident, role in record['members']:
            if kind == 'w' and role in ('outer', 'inner'):
                target = outer if role == 'outer' else inner
                if ident in outer or ident in inner or ident not in graph.ways:
                    raise ValueError('duplicate or missing geometric OSM member')
                if graph.ways[ident]['deleted']:
                    raise ValueError('selected OSM member is deleted')
                target[ident] = graph.ways[ident]['nodes']
            elif (kind, role) in ignored:
                records = {'n': graph.nodes, 'w': graph.ways, 'r': graph.relations}[kind]
                if ident not in records or records[ident]['deleted']:
                    raise ValueError('selected OSM metadata member is missing')
            else:
                raise ValueError('unsupported OSM geometric or metadata member role')
    rings = assemble_rings(outer)
    holes = assemble_rings(inner) if inner else []
    chosen = None
    if anchors := selected.get('ring_anchors'):
        chosen = []
        for anchor in sorted(anchors, key=lambda a: int(a['node_id'])):
            node, way = int(anchor['node_id']), int(anchor['way_id'])
            selected_object(graph.nodes, node, anchor['node_version'], anchor['expected_tags'])
            if ([ident for ident, refs in outer.items() if node in refs] != [way]
                    or outer[way].count(node) != 1):
                raise ValueError('OSM anchor must belong to exactly its selected outer way')
            matches = [ring for ring in rings if ring.count(node) == 1]
            if len(matches) != 1 or matches[0] in chosen:
                raise ValueError('OSM anchor does not select one distinct ring')
            chosen.append(matches[0])

    def coordinates(ring):
        if any(n not in graph.nodes or graph.nodes[n]['deleted'] for n in ring):
            raise ValueError('OSM ring has missing nodes')
        points = [list(graph.nodes[n]['coordinates']) for n in ring]
        if any(abs(a[0] - b[0]) > 180 for a, b in zip(points, points[1:])):
            raise ValueError('OSM ring crosses the longitude seam; an explicit wrapped construction is needed')
        return points

    polygons = [[coordinates(ring)] for ring in rings]
    for hole in holes:
        points = coordinates(hole)
        owners = [polygon for polygon in polygons if Polygon(polygon[0]).contains(Polygon(points))]
        if len(owners) != 1:
            raise ValueError('OSM inner ring needs exactly one containing outer ring')
        owners[0].append(points)
    complete = {'type': 'MultiPolygon', 'coordinates': polygons}
    validate_geometry(complete)
    if chosen is not None:
        polygons = [polygons[rings.index(ring)] for ring in chosen]
    treatment = selected.get('holes', 'preserve')
    if treatment == 'outer_envelope':
        polygons = [[polygon[0]] for polygon in polygons]
    elif treatment != 'preserve':
        raise ValueError('unsupported OSM hole treatment')
    kind = selected.get('geometry_type', 'MultiPolygon')
    if kind == 'Polygon' and len(polygons) == 1:
        return {'type': kind, 'coordinates': polygons[0]}
    if kind != 'MultiPolygon':
        raise ValueError('polygon output needs one polygon or a multipolygon')
    return {'type': kind, 'coordinates': polygons}


def read_features(path, settings):
    graph = read_graph(path)
    result = []
    for selection in settings['selections']:
        kind = selection['object_type']
        objects = {'node': graph.nodes, 'way': graph.ways, 'relation': graph.relations}
        if kind not in objects:
            raise ValueError('unsupported selected OSM object type')
        record = selected_object(objects[kind], selection['source_feature_id'],
                                 selection['object_version'], selection.get('expected_tags', {}))
        if parent := selection.get('parent_relation'):
            relation = selected_object(graph.relations, parent['id'], parent['version'],
                                       parent.get('expected_tags', {}))
            member = ({'node': 'n', 'way': 'w', 'relation': 'r'}[kind],
                      int(selection['source_feature_id']), parent['role'])
            if relation['members'].count(member) != 1:
                raise ValueError('selected OSM object must be one member of its selected parent')
        geometry = ({'type': 'Point', 'coordinates': list(record['coordinates'])}
                    if kind == 'node' else polygon_geometry(graph, selection, record))
        validate_geometry(geometry)
        if selection.get('expected_geometry_sha256', geometry_hash(geometry)) != geometry_hash(geometry):
            raise ValueError('selected OSM geometry checksum differs')
        result.append(dict(feature_id=selection['feature_id'], source_feature_id=selection['source_feature_id'],
                           geometry=geometry, evidence={'provider_tags': record['tags'],
                           'provider_object_type': kind, 'provider_object_version': record['version']}))
    return result

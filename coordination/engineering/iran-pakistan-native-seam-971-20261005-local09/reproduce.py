"""Offline, pinned source comparison for one retained seam; never repairs geometry."""
import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import shapely
from shapely.geometry import Point, Polygon, MultiPolygon, shape, mapping
from shapely import union_all
from evidence.immutable import Baseline, canonical_json, sha256
from evidence.geometry import METHOD, land_area_m2, point

VERSION = 'worldatlas-saravan-panjgur-native-comparison-v1'
COMPONENT_ID = 'gap:10c95e9f3b4b8d93b3ce3145916de2de656527cc706a5f64b323aa680406cefb'
SUBJECTS = {'IRN': 'gb:IRN:ADM2:26516999B17111396986996',
            'PAK': 'gb:PAK:ADM2:60131773B78019453337506'}
ANCHOR = (63.207727681, 26.8032)


def valid_polygon(geometry):
    if geometry.is_empty or geometry.geom_type not in ('Polygon', 'MultiPolygon') or not geometry.is_valid:
        raise ValueError('Invalid/empty/nonpolygon source; no repair permitted')
    return geometry


def assemble_osm_boundary(response, relation_id):
    """Join complete outer/inner ways by original node identity, without snapping."""
    elements = {}
    for element in response['elements']:
        key = (element['type'], element['id'])
        if key in elements:
            raise ValueError('Duplicate OSM element')
        elements[key] = element
    relation = elements[('relation', relation_id)]
    if relation.get('tags', {}).get('boundary') != 'administrative':
        raise ValueError('Expected administrative boundary relation')
    groups = {'outer': {}, 'inner': {}}
    ignored = []
    used = set()
    for member in relation['members']:
        role = member.get('role', '')
        if role in groups:
            if member['type'] != 'way' or member['ref'] in used:
                raise ValueError('Unsupported recursive/duplicate geometry member')
            used.add(member['ref'])
            way = elements[('way', member['ref'])]
            ids = way['nodes']
            if len(ids) < 2:
                raise ValueError('Incomplete boundary way')
            groups[role][member['ref']] = ids
        elif (member['type'], role) in [('node', 'admin_centre'), ('node', 'label'), ('relation', 'subarea')]:
            ignored.append(member)
        else:
            raise ValueError('Unknown boundary member role')

    def rings(ways):
        ends = {}
        for ref, ids in ways.items():
            for endpoint in (ids[0], ids[-1]):
                ends.setdefault(endpoint, []).append(ref)
        if any(len(refs) != 2 for refs in ends.values()):
            raise ValueError('Open or ambiguous boundary node graph')
        remaining = dict(ways)
        result = []
        while remaining:
            ref = min(remaining)
            nodes = list(remaining.pop(ref))
            while nodes[-1] != nodes[0]:
                candidates = [r for r in ends[nodes[-1]] if r in remaining]
                if len(candidates) != 1:
                    raise ValueError('Cannot close exact boundary ring')
                ids = remaining.pop(candidates[0])
                if ids[-1] == nodes[-1]:
                    ids = list(reversed(ids))
                if ids[0] != nodes[-1]:
                    raise ValueError('Boundary node identity mismatch')
                nodes.extend(ids[1:])
            if len(nodes) < 4:
                raise ValueError('Boundary ring has too few nodes')
            coordinates = []
            for identity in nodes:
                node = elements[('node', identity)]
                coordinates.append(point(node['lon'], node['lat']))
            valid_polygon(Polygon(coordinates))
            result.append(coordinates)
        return result

    outers, inners = rings(groups['outer']), rings(groups['inner'])
    if not outers:
        raise ValueError('No complete outer boundary')
    holes = [[] for _ in outers]
    for inner in inners:
        candidates = [i for i, outer in enumerate(outers) if Polygon(outer).contains(Polygon(inner))]
        if len(candidates) != 1:
            raise ValueError('Ambiguous or uncontained inner ring')
        holes[candidates[0]].append(inner)
    polygons = [Polygon(outer, holes[i]) for i, outer in enumerate(outers)]
    geometry = valid_polygon(polygons[0] if len(polygons) == 1 else MultiPolygon(polygons))
    members = [('relation', relation_id)] + [('way', ref) for ref in sorted(used)]
    node_ids = sorted({node for role in groups.values() for ids in role.values() for node in ids})
    members.extend(('node', identity) for identity in node_ids)
    return geometry, {'relation_id': relation_id, 'boundary_way_count': len(used),
                      'boundary_node_count': len(node_ids), 'outer_ring_count': len(outers),
                      'inner_ring_count': len(inners), 'ignored_non_geometry_members': ignored,
                      'element_versions': [{'type': kind, 'id': identity,
                                            'version': elements[(kind, identity)].get('version'),
                                            'timestamp': elements[(kind, identity)].get('timestamp')}
                                           for kind, identity in members]}


def measured_geometry(geometry):
    """Retain exact topology even when it cannot be measured by the shared helper."""
    raw_geometry = mapping(geometry)
    polygons = []

    def collect(g):
        if g.is_empty:
            return
        if g.geom_type == 'Polygon':
            polygons.append(g)
        elif g.geom_type in ('MultiPolygon', 'GeometryCollection'):
            for child in g.geoms:
                collect(child)

    collect(geometry)
    result = {'geometry': raw_geometry, 'geometry_sha256': sha256(canonical_json(raw_geometry)),
              'empty': geometry.is_empty, 'valid': geometry.is_valid,
              'positive_native_coordinate_area_flag': geometry.area > 0,
              'area_m2': None, 'area_error': None}
    try:
        result['area_m2'] = sum(land_area_m2(p) for p in polygons)
    except Exception as error:
        result['area_error'] = str(error)
    return result


def partition(component, left, right):
    return {name: measured_geometry(g) for name, g in {
        'IRN_native_only': component.intersection(left).difference(right),
        'PAK_native_only': component.intersection(right).difference(left),
        'both_native_overlap': component.intersection(left).intersection(right),
        'neither_native': component.difference(union_all([left, right]))}.items()}


def intersecting_bounds(a, b):
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def compare(repo, commit, registry):
    base = Baseline(repo, registry['baseline_commit'], registry['baseline_files'])
    sources = Baseline(repo, commit, registry['source_files'])
    component_features = json.loads(gzip.decompress(base.read(registry['component_path'])))['features']
    matches = [f for f in component_features if f.get('id') == COMPONENT_ID]
    if len(matches) != 1 or sha256(canonical_json(matches[0])) != registry['component_feature_sha256']:
        raise ValueError('Original full component identity/hash mismatch')
    component_feature = matches[0]
    component = valid_polygon(shape(component_feature['geometry']))
    anchor = Point(*point(*ANCHOR))
    current, native, countries = {}, {}, {}
    for country, subject in SUBJECTS.items():
        values = json.loads(base.read(registry['current_subject_files'][country]))['features']
        matches = [f for f in values if f.get('id', f.get('properties', {}).get('id')) == subject]
        if len(matches) != 1:
            raise ValueError('Current subject absent or duplicated')
        current[country] = valid_polygon(shape(matches[0]['geometry']))
        raw = json.loads(sources.read(registry['native_files'][country]))
        values = raw['features']
        native_id = subject.split(':', 3)[-1]
        matches = [f for f in values if f.get('properties', {}).get('shapeID') == native_id]
        if len(matches) != 1:
            raise ValueError('Native member identity absent or duplicated')
        native[country] = valid_polygon(shape(matches[0]['geometry']))
        candidates, unknown = [], []
        for f in values:
            identity = f.get('properties', {}).get('shapeID')
            if f.get('geometry') is None:
                unknown.append({'shapeID': identity, 'reason': 'null native geometry'})
                continue
            g = shape(f['geometry'])
            if not g.is_empty and intersecting_bounds(g.bounds, component.bounds):
                if not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon'):
                    unknown.append({'shapeID': identity, 'reason': 'invalid/nonpolygon bbox candidate'})
                    continue
                candidates.append({'shapeID': identity, 'shapeName': f['properties'].get('shapeName'),
                                   'feature_sha256': sha256(canonical_json(f)), 'anchor_covers': g.covers(anchor),
                                   'intersects_component': g.intersects(component),
                                   'positive_native_coordinate_area_intersection_flag': g.intersection(component).area > 0})
        countries[country] = {'feature_count': len(values), 'full_component_bbox_candidates': candidates,
                              'unknown_candidates': unknown, 'exact_native_feature_sha256': sha256(canonical_json(matches[0])),
                              'native_anchor_covers': native[country].covers(anchor),
                              'current_anchor_covers': current[country].covers(anchor),
                              'current_component_intersection': measured_geometry(component.intersection(current[country])),
                              'native_vs_current_component_difference': measured_geometry(component.intersection(native[country].difference(current[country])))}
    osm, osm_info = assemble_osm_boundary(json.loads(sources.read(registry['osm_file'])), 3229274)
    parts = partition(component, native['IRN'], native['PAK'])
    partition_union = union_all([shape(p['geometry']) for p in parts.values()])
    osm_joint = union_all([native['IRN'], osm])
    area = measured_geometry(component)
    measured = [p['area_m2'] for p in parts.values()]
    return {'version': VERSION, 'baseline_commit': registry['baseline_commit'], 'evaluation_commit': commit,
            'component_id': COMPONENT_ID, 'original_component_feature_sha256': registry['component_feature_sha256'],
            'original_component_properties': component_feature['properties'], 'component': area,
            'anchor': list(ANCHOR), 'countries': countries, 'native_source_partition': parts,
            'partition_area_sum_m2': sum(measured) if all(a is not None for a in measured) else None,
            'partition_union_equals_component': partition_union.equals(component),
            'partition_coverage_residual': measured_geometry(component.difference(partition_union)),
            'partition_excess_residual': measured_geometry(partition_union.difference(component)),
            'osm_candidate': {'assembly': osm_info, 'geometry_sha256': sha256(canonical_json(mapping(osm))),
                              'anchor_covers': osm.covers(anchor), 'covers_full_component': osm.covers(component),
                              'component_intersection': measured_geometry(component.intersection(osm)),
                              'component_not_covered': measured_geometry(component.difference(osm)),
                              'joint_with_IRN_native_uncovered': measured_geometry(component.difference(osm_joint)),
                              'joint_with_IRN_native_overlap': measured_geometry(component.intersection(native['IRN']).intersection(osm)),
                              'joint_vintages_approved': False},
            'method': METHOD, 'software': {'shapely': shapely.__version__},
            'physical_classification': 'unknown', 'administrative_assignment': None,
            'limits': registry['limits']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--registry', required=True)
    parser.add_argument('--registry-sha256', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists() or out.is_symlink():
        raise ValueError('Refuse to overwrite an existing output')
    baseline = Baseline(args.repo, args.commit, [json.loads(args.registry)])
    descriptor = json.loads(args.registry)
    if descriptor['sha256'] != args.registry_sha256:
        raise ValueError('Registry SHA disagrees with command pin')
    registry = json.loads(baseline.read(descriptor['path']))
    result = compare(args.repo, args.commit, registry)
    with out.open('xb') as stream:
        stream.write(canonical_json(result))


if __name__ == '__main__':
    main()

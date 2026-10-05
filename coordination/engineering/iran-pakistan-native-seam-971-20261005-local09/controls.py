"""Source assembly and exact full-component accounting controls, offline."""
import copy
import json
from pathlib import Path
from shapely.geometry import Point, Polygon, box, shape
from shapely import union_all
from reproduce import assemble_osm_boundary, partition, valid_polygon, measured_geometry


def source():
    return {'elements': [
        {'type': 'node', 'id': i, 'lon': x, 'lat': y}
        for i, (x, y) in enumerate([(0, 0), (2, 0), (2, 2), (0, 2)], 1)] + [
        {'type': 'way', 'id': 10, 'nodes': [1, 2, 3]},
        {'type': 'way', 'id': 11, 'nodes': [1, 4, 3]},
        {'type': 'relation', 'id': 1, 'tags': {'boundary': 'administrative'}, 'members': [
            {'type': 'way', 'ref': 10, 'role': 'outer'},
            {'type': 'way', 'ref': 11, 'role': 'outer'}]}]}


def rejected(callback):
    try:
        callback()
    except (ValueError, KeyError):
        return
    raise AssertionError('Malformed source was accepted')


def main():
    checks = []
    g, receipt = assemble_osm_boundary(source(), 1)
    assert g.equals(box(0, 0, 2, 2)) and receipt['boundary_way_count'] == 2
    checks.append('oppositely oriented exact node chains close without snapping')
    data = source(); data['elements'][4]['nodes'] = [1, 2]
    rejected(lambda: assemble_osm_boundary(data, 1))
    checks.append('open node graph rejected')
    data = source(); data['elements'].append(copy.deepcopy(data['elements'][0]))
    rejected(lambda: assemble_osm_boundary(data, 1))
    checks.append('duplicate source elements rejected')
    data = source(); data['elements'][-1]['members'].append(copy.deepcopy(data['elements'][-1]['members'][0]))
    rejected(lambda: assemble_osm_boundary(data, 1))
    checks.append('duplicate geometry membership rejected')
    data = source(); data['elements'][0]['lon'] = 181
    rejected(lambda: assemble_osm_boundary(data, 1))
    checks.append('invalid longitude rejected')
    data = source(); data['elements'][-1]['members'][0]['type'] = 'relation'
    rejected(lambda: assemble_osm_boundary(data, 1))
    checks.append('recursive geometry member rejected rather than inferred complete')
    rejected(lambda: valid_polygon(Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])))
    checks.append('invalid polygon rejected without MakeValid')
    data = source()
    data['elements'][-1]['members'].append({'type': 'node', 'ref': 999, 'role': 'admin_centre'})
    data['elements'][-1]['members'].append({'type': 'relation', 'ref': 999, 'role': 'subarea'})
    g, receipt = assemble_osm_boundary(data, 1)
    assert g.equals(box(0, 0, 2, 2)) and len(receipt['ignored_non_geometry_members']) == 2
    checks.append('nongeometry subareas recorded without expanding boundary scope')
    data = source()
    for i, (x, y) in enumerate([(0.5, 0.5), (1.5, 0.5), (1.5, 1.5), (0.5, 1.5)], 5):
        data['elements'].insert(0, {'type': 'node', 'id': i, 'lon': x, 'lat': y})
    data['elements'].insert(0, {'type': 'way', 'id': 12, 'nodes': [5, 6, 7, 8, 5]})
    data['elements'][-1]['members'].append({'type': 'way', 'ref': 12, 'role': 'inner'})
    g, receipt = assemble_osm_boundary(data, 1)
    assert not g.covers(Point(1, 1)) and receipt['inner_ring_count'] == 1
    checks.append('source inner hole retained')
    component = box(0, 0, 3, 1)
    parts = partition(component, box(0, 0, 1, 1), box(2, 0, 3, 1))
    assert shape(parts['neither_native']['geometry']).equals(box(1, 0, 2, 1))
    assert union_all([shape(p['geometry']) for p in parts.values()]).equals(component)
    checks.append('known bilateral source gap retained with whole-component accounting')
    parts = partition(component, box(0, 0, 2, 1), box(1, 0, 3, 1))
    assert shape(parts['both_native_overlap']['geometry']).equals(box(1, 0, 2, 1))
    assert parts['neither_native']['empty']
    checks.append('overlap explicitly partitioned rather than assigned to one neighbor')
    tiny = box(0, 0, 1e-8, 1e-8)
    result = measured_geometry(tiny)
    assert not result['empty'] and result['positive_native_coordinate_area_flag'] and result['area_m2'] > 0
    checks.append('positive tiny polygons retained without area cutoff')
    result = {'method_id': 'native-border-comparison', 'kind': 'positive-control',
              'outcome': 'passed', 'checks': checks, 'check_count': len(checks)}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()

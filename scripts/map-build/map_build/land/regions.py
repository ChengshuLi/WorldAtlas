"""Assemble selected region polygons and check closures against physical water."""
import hashlib
import json

from shapely.geometry import Point, shape

from map_build.core.grid_paths import grid_points, touched_segment
from map_build.core.rle import row
from map_build.inputs.features import feature_geometry


def verify_closure(record, coordinates, records, components):
    """Check the complete route; only selected endpoint cells may touch land."""
    points = grid_points(coordinates, components.grid)
    terminal = record['closure_method'] == 'physical_terminal_closure_v1'
    if record['closure_method'] not in ('physical_water_closure_v1', 'physical_terminal_closure_v1'):
        raise ValueError('unsupported physical closure rule')
    cells = []
    if terminal:
        for side, actual in [('start', coordinates[0]), ('end', coordinates[-1])]:
            reference = record[side+'_terminal']
            boundary = feature_geometry(records['boundary', reference['boundary_id']], ('LineString',))
            expected = boundary['coordinates'][{'start': 0, 'end': -1}[reference['endpoint']]]
            if actual != expected:
                raise ValueError('closure does not join its selected boundary endpoint')
        for point in (points[0], points[-1]):
            if any(v.denominator == 1 for v in point):
                raise ValueError('closure terminal lies on an ambiguous grid edge')
            cells.append(tuple(int(v//1) for v in point))
        if cells[0] == cells[1]:
            raise ValueError('closure terminals share one cell')
    physical, visits, land = {}, 0, set()
    for i, (a, b) in enumerate(zip(points, points[1:])):
        touched_land = set()
        for x, y in touched_segment(*a, *b):
            if not 0 <= y < components.grid.height:
                raise ValueError('closure leaves the physical grid')
            x %= components.grid.width
            if y not in physical:
                physical[y] = row(components.physical, y, components.grid.width)
            ends, codes = physical[y]
            code = int(codes[ends.searchsorted(x, side='right')])
            visits += 1
            if code == 1:
                continue
            allowed = terminal and ((i == 0 and (x,y) == cells[0])
                                    or (i == len(points)-2 and (x,y) == cells[1]))
            if code != 17 or not allowed:
                raise ValueError(f'closure touches nonterminal land at {x},{y}')
            touched_land.add((x,y))
        if len(touched_land) > 1:
            raise ValueError('closure segment joins two land cells')
        land.update(touched_land)
    return dict(cell_visits=visits, terminal_land_cells=[list(cell) for cell in sorted(land)])


def assemble_regions(domain, components):
    """Build the selected ordered rings from current geometry, with no repairs."""
    records = {('boundary', item['boundary_id']): item for item in domain['mainland_boundaries']}
    records.update({('route', item['route_id']): item for item in domain['routes']})
    selected = domain['land_baseline_policy']['region_ids']
    regions = {item['region_id']: item for item in domain['seed_regions']}
    result, checked_routes = {}, {}
    for ident in selected:
        region, coordinates = regions[ident], []
        for segment in region['segments']:
            key = segment['kind'], segment['id']
            record = records[key]
            line = feature_geometry(record, ('LineString',))['coordinates']
            first, last = segment['start'], segment['end']
            if type(first) is not int or type(last) is not int or not 0 <= first < last <= len(line) or last-first < 2:
                raise ValueError('invalid selected region vertex slice')
            if key[0] == 'route' and key not in checked_routes:
                if first != 0 or last != len(line):
                    raise ValueError('physical closure must use its complete selected route')
                checked_routes[key] = verify_closure(record, line, records, components)
            part = line[first:last]
            if segment['reverse']:
                part = list(reversed(part))
            if coordinates and coordinates[-1] != part[0]:
                raise ValueError('selected region segments do not join exactly')
            coordinates.extend(part if not coordinates else part[1:])
        if len(coordinates) < 4 or coordinates[0] != coordinates[-1]:
            raise ValueError('selected region does not close')
        geometry = dict(type='Polygon', coordinates=[coordinates])
        polygon = shape(geometry)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError('selected region is not a valid polygon')
        for witness in region['witnesses']:
            point = Point(float(witness['lon']), float(witness['lat']))
            if polygon.boundary.intersects(point) or polygon.contains(point) != witness['inside']:
                raise ValueError('selected region side witness fails')
        checksum = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':'),
                                             allow_nan=False).encode()).hexdigest()
        result[ident] = dict(geometry=geometry, geometry_sha256=checksum)
    return result, {key[1]: value for key, value in checked_routes.items()}

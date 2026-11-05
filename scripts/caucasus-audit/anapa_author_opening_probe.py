"""Screen the author's coastal approach joined at the first selected-line intersection.

Research geometry only: does not establish flow direction or select a boundary.
The OSM extracts are spatially incomplete; missing ways are reported.
"""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from pyproj import Geod
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import substring


def length(line):
    return Geod(ellps='WGS84').line_length(*zip(*line.coords))


def main(selected_path, author_path, *extracts):
    selected = LineString(json.loads(Path(selected_path).read_bytes())['coordinates'])
    author = LineString(json.loads(Path(author_path).read_bytes())['features'][462]['geometry']['coordinates'])
    # Intersection with the archived OSM coastline; see CAUCASUS-AUDIT-SYNTHESIS.md.
    coast = Point(37.36792175894848, 44.7996329213336)
    if author.distance(coast) > 1e-12:
        raise ValueError('coastal point does not lie on author feature')
    intersection = author.intersection(selected)
    points = [intersection] if intersection.geom_type == 'Point' else list(intersection.geoms)
    points = [p for p in points if p.geom_type == 'Point' and author.project(p) < author.project(coast)]
    if not points:
        raise ValueError('no intersection')
    join = min(points, key=selected.project)
    candidate = substring(author, author.project(join), author.project(coast))
    candidate = LineString(list(candidate.coords)[::-1])
    old = substring(selected, 0, selected.project(join))
    retained = substring(selected, selected.project(join), selected.length)
    candidate_coords = list(candidate.coords)
    retained_coords = list(retained.coords)
    candidate_coords[-1] = (join.x, join.y)
    retained_coords[0] = (join.x, join.y)
    full = LineString(candidate_coords + retained_coords[1:])
    found, missing, observed, coast_ways = {}, set(), set(), set()
    for name in extracts:
        root = ET.parse(name).getroot()
        nodes = {n.get('id'): (float(n.get('lon')), float(n.get('lat'))) for n in root.findall('node')}
        for way in root.findall('way'):
            tags = {t.get('k'): t.get('v') for t in way.findall('tag')}
            refs = [n.get('ref') for n in way.findall('nd')]
            if tags.get('natural') == 'coastline' and len(refs) >= 2 and all(n in nodes for n in refs):
                if LineString([nodes[n] for n in refs]).distance(coast) < 1e-10:
                    coast_ways.add((way.get('id'), way.get('version')))
            if not (tags.get('waterway') in {'river', 'stream', 'riverbank', 'canal', 'ditch', 'drain'} or
                    tags.get('natural') in {'water', 'wetland'}):
                continue
            ident = (way.get('id'), way.get('version'))
            if len(refs) < 2 or any(n not in nodes for n in refs):
                if ident not in observed:
                    missing.add(ident)
                continue
            observed.add(ident)
            missing.discard(ident)
            coords = [nodes[n] for n in refs]
            line = LineString(coords)
            if refs[0] == refs[-1] and len(refs) >= 4 and (tags.get('natural') in {'water', 'wetland'} or tags.get('waterway') == 'riverbank'):
                polygon = Polygon(coords)
                if polygon.is_valid:
                    line = polygon
            ch, oh = candidate.intersection(line), old.intersection(line)
            if not ch.is_empty or not oh.is_empty:
                found['/'.join(ident)] = {'tags': tags, 'candidate': ch.wkt[:400], 'selected': oh.wkt[:400]}
    if not coast_ways:
        raise ValueError('the supplied extracts do not contain the coastal intersection')
    inputs = [{'name': Path(p).name, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()}
              for p in (selected_path, author_path, *extracts)]
    print(json.dumps({'selected_opening_m': length(old), 'candidate_opening_m': length(candidate),
                      'join': [join.x, join.y], 'coast': [coast.x, coast.y],
                      'source_sha256': inputs, 'mapped_coast_ways': sorted('/'.join(x) for x in coast_ways),
                      'candidate_simple': candidate.is_simple, 'full_line_simple': full.is_simple,
                      'candidate_other_retained_intersection': candidate.intersection(retained).wkt[:500],
                      'complete_water_way_versions': len(observed), 'incomplete_water_way_versions': len(missing),
                      'mapped_hits': found,
                      'limits': 'Partial dated OSM extracts; relations are not checked. Polygon membership and sampled channels do not prove a drainage divide.'},
                     ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])

"""Exact original/new diagnostic correspondence, never owner assignment.

Every input identity has a ledger row, even with only point contacts or unknown
operations. Complete original intersections and difference remnants survive;
no proximity, area cutoff, snapping, buffering or geometry repair is used.
"""
from collections import defaultdict

from shapely import STRtree, union_all
from shapely.errors import GEOSException
from shapely.geometry import mapping, shape
from shapely.affinity import translate

from evidence.immutable import canonical_json, sha256
from physical_gap_audit import atoms

VERSION = 'worldatlas-physical-gap-crosswalk-v1'


def membership(features, records):
    by_id = {row['id']: row for row in features}
    if len(by_id) != len(features):
        raise ValueError('Duplicate original fragment identity')
    members = {}
    seen_components = set()
    for record in records:
        if record['id'] in seen_components:
            raise ValueError('Duplicate original component identity')
        seen_components.add(record['id'])
        for binding in record['properties']['fragment_bindings']:
            identity = binding['id']
            if identity in members or identity not in by_id:
                raise ValueError('Duplicate or unknown original component membership')
            if sha256(canonical_json(by_id[identity])) != binding['feature_sha256']:
                raise ValueError('Original full-feature binding changed')
            members[identity] = record['id']
    if set(members) != set(by_id):
        raise ValueError('Incomplete original component/fragment membership')
    return members


def residual(original, counterparts):
    """Retain each observed nonempty atom, including numerical lines/points."""
    try:
        result = original.difference(union_all(counterparts))
        return {'status': 'checked', 'atoms': [mapping(g) for g in atoms(result)],
                'original_planar_area': original.area,
                'remaining_planar_area': result.area}
    except GEOSException as error:
        return {'status': 'unknown-original-operation-failed', 'error': str(error),
                'original_geometry': mapping(original)}


def crosswalk(old_features, new_features, old_components, new_components):
    old = sorted(old_features, key=lambda f: f['id'])
    new = sorted(new_features, key=lambda f: f['id'])
    old_members, new_members = membership(old, old_components), membership(new, new_components)
    old_geometries = [shape(f['geometry']) for f in old]
    new_geometries = [shape(f['geometry']) for f in new]
    for g in old_geometries + new_geometries:
        if g.geom_type != 'Polygon' or g.is_empty or not g.is_valid or g.area <= 0:
            raise ValueError('Require original positive valid polygon atoms')
    tree = STRtree(new_geometries)
    west = [(j, translate(g, xoff=360)) for j, g in enumerate(new_geometries) if g.bounds[0] == -180]
    east = [(j, translate(g, xoff=-360)) for j, g in enumerate(new_geometries) if g.bounds[2] == 180]
    west_tree, east_tree = STRtree([g for _, g in west]), STRtree([g for _, g in east])
    pairs, old_pairs, new_pairs = [], defaultdict(list), defaultdict(list)
    old_indexes, new_indexes = defaultdict(list), defaultdict(list)
    for i, geometry in enumerate(old_geometries):
        # Bbox query followed by an explicit exact operation retains failures;
        # an exact-predicate tree query must not silently omit an unknown pair.
        candidates = [(int(k), 0, new_geometries[int(k)]) for k in tree.query(geometry)]
        if geometry.bounds[2] == 180:
            candidates += [(west[int(k)][0], 360, west[int(k)][1]) for k in west_tree.query(geometry)]
        if geometry.bounds[0] == -180:
            candidates += [(east[int(k)][0], -360, east[int(k)][1]) for k in east_tree.query(geometry)]
        for j, shift, other in sorted(candidates, key=lambda r: (r[0], r[1])):
            row = {'old_fragment': old[i]['id'], 'new_fragment': new[j]['id'],
                   'old_component': old_members[old[i]['id']],
                   'new_component': new_members[new[j]['id']],
                   'dateline': shift != 0, 'new_shift_degrees': shift}
            try:
                intersection = geometry.intersection(other)
                if intersection.is_empty:
                    continue
                row.update({'original_intersection': mapping(intersection),
                            'intersection_planar_area': intersection.area})
                same_coordinates = shift == 0 and old[i]['geometry'] == new[j]['geometry']
                same_set = geometry.equals(other)
                kind = ('identical-coordinates' if same_coordinates else
                        'equal-point-set' if same_set else
                        'positive-area-overlap' if intersection.area > 0 else
                        'positive-length-contact' if intersection.length > 0 else
                        'point-only-contact')
                row.update({'status': 'checked', 'kind': kind,
                            'original_intersection': mapping(intersection),
                            'intersection_planar_area': intersection.area,
                            'old_covers_new': geometry.covers(other),
                            'new_covers_old': other.covers(geometry),
                            'equality_overlay_disagreement': (same_coordinates or same_set) and
                                                              intersection.area <= 0})
            except GEOSException as error:
                row.update({'status': 'unknown-original-operation-failed', 'error': str(error),
                            'kind': 'unknown-overlay'})
            pair_number = len(pairs)
            pairs.append(row)
            old_pairs[i].append(pair_number)
            new_pairs[j].append(pair_number)
            old_indexes[i].append((j, shift))
            new_indexes[j].append((i, -shift))

    def ledgers(features, geometries, pair_ids, opposite_indexes, opposite_geometries, members, side):
        result = []
        for i, feature in enumerate(features):
            refs = pair_ids[i]
            uncertain = any(pairs[p]['status'] != 'checked' for p in refs)
            difference = residual(geometries[i], [translate(opposite_geometries[j], xoff=shift) if shift else opposite_geometries[j]
                                                   for j, shift in opposite_indexes[i]])
            if uncertain:
                difference['status'] = 'unknown-related-overlay-failed'
            result.append({'fragment': feature['id'], 'component': members[feature['id']],
                           'feature_sha256': sha256(canonical_json(feature)),
                           'geometry_sha256': sha256(canonical_json(feature['geometry'])),
                           'original_area_m2': feature['properties'].get('area_m2'),
                           'unmeasured_original': feature['properties'].get('area_m2') is None,
                           'pair_numbers': refs, 'side': side, 'difference': difference})
        return result

    old_ledger = ledgers(old, old_geometries, old_pairs, old_indexes, new_geometries, old_members, 'old')
    new_ledger = ledgers(new, new_geometries, new_pairs, new_indexes, old_geometries, new_members, 'new')
    component_pairs = defaultdict(list)
    for i, pair in enumerate(pairs):
        component_pairs[(pair['old_component'], pair['new_component'])].append(i)
    component_links = [{'old_component': a, 'new_component': b, 'pair_numbers': indexes,
                        'kinds': sorted({pairs[i]['kind'] for i in indexes})}
                       for (a, b), indexes in sorted(component_pairs.items())]
    by_old, by_new = defaultdict(list), defaultdict(list)
    for i, row in enumerate(component_links):
        by_old[row['old_component']].append(i)
        by_new[row['new_component']].append(i)
    component_ledger = []
    for side, records, links in [('old', old_components, by_old), ('new', new_components, by_new)]:
        for record in sorted(records, key=lambda r: r['id']):
            component_ledger.append({'side': side, 'component': record['id'],
                                     'original_feature_sha256': sha256(canonical_json(record)),
                                     'fragment_ids': [r['id'] for r in record['properties']['fragment_bindings']],
                                     'component_link_numbers': links[record['id']],
                                     'unmeasured_fragment_ids': record['properties']['unmeasured_fragment_ids']})
    return {'fragment_pairs': pairs, 'old_fragments': old_ledger, 'new_fragments': new_ledger,
            'component_links': component_links, 'components': component_ledger}

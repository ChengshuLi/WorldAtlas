#!/usr/bin/env python3
"""Independently check genuinely new reference land; never manufacture history."""
import hashlib, json, pathlib, sys
sys.dont_write_bytecode = True
from shapely import STRtree, normalize
from shapely.geometry import shape
from majority import canonical
from ellipsoidal_area import area

TIERS = ['province', 'area', 'region', 'subcontinent', 'continent']


def validate(payload):
    before, after = payload['before'], payload['after']
    old = {f['id']: f for f in before}
    new = {f['id']: f for f in after}
    groups = {u['id']: u for u in payload['units']}
    if len(old) != len(before) or len(new) != len(after) or len(groups) != len(payload['units']):
        raise ValueError('Duplicate creation inventory identity')
    proofs = payload['proofs']
    if len({p['location_id'] for p in proofs}) != len(proofs):
        raise ValueError('Duplicate creation proof')
    geoms = [canonical(shape(f['geometry'])) for f in after]
    tree = STRtree(geoms)
    indices = {f['id']: i for i, f in enumerate(after)}
    results = []
    for proof in proofs:
        identifier = proof['location_id']
        if identifier in old or identifier not in new:
            raise ValueError('Creation requires a genuinely absent identity')
        feature = new[identifier]
        if feature['properties']['id'] != identifier:
            raise ValueError('Conflicting location identity')
        source = proof['source']
        if not source.get('license') or not source.get('attribution') or not source.get('identity') or not source.get('url', '').startswith(('https://', 'http://')):
            raise ValueError('Creation requires source identity, URL, license and attribution')
        start, end = source.get('supported_from'), source.get('supported_to')
        if type(start) is not int or type(end) is not int or start == 0 or end == 0 or start >= end or start < -3000 or end > 2027:
            raise ValueError('Invalid source support interval')
        base = pathlib.Path(payload['base']).resolve()
        source_path = (base / source['path']).resolve()
        if not source_path.is_relative_to(base) or not source_path.is_file():
            raise ValueError('Creation source escapes evidence archive')
        raw = source_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source['sha256']:
            raise ValueError('Creation source bytes changed')
        document = json.loads(raw)
        rows = document.get('features', [document])
        matches = [f for f in rows if f.get('id') == source['identity']]
        if len(matches) != 1:
            raise ValueError('Ambiguous source feature identity')
        raw_geometry = shape(matches[0]['geometry'])
        if not raw_geometry.is_valid:
            raise ValueError('Invalid raw source geometry must not be silently repaired')
        def coordinates(rows):
            if rows and isinstance(rows[0], (int, float)):
                if len(rows) != 2 or not -180 <= rows[0] <= 180 or not -90 <= rows[1] <= 90:
                    raise ValueError('Invalid longitude/latitude source coordinates')
            else:
                for row in rows:
                    coordinates(row)
        coordinates(matches[0]['geometry']['coordinates'])
        coordinates(feature['geometry']['coordinates'])
        def rings(rows):
            if rows and rows[0] and isinstance(rows[0][0], (int, float)):
                if len(rows) < 4 or rows[0] != rows[-1]:
                    raise ValueError('Source polygon rings must be explicitly closed')
            else:
                for row in rows:
                    rings(row)
        rings(matches[0]['geometry']['coordinates'])
        rings(feature['geometry']['coordinates'])
        if not shape(feature['geometry']).is_valid:
            raise ValueError('Invalid created geometry must not be silently repaired')
        # Antimeridian normalization is allowed, invalid source repair is not.
        geometry = geoms[indices[identifier]]
        original = canonical(raw_geometry)
        if geometry.is_empty or not geometry.is_valid or original.is_empty or not original.is_valid or geometry.geom_type not in ['Polygon', 'MultiPolygon']:
            raise ValueError('Invalid source-backed polygon')
        if normalize(geometry).wkb != normalize(original).wkb:
            raise ValueError('Created land differs from the exact source geometry')
        if not area(geometry) > 0:
            raise ValueError('Created footprint has no dry-land area')
        review = proof.get('identity_review', {})
        if review.get('status') != 'distinct-new-territory' or not review.get('evidence_url', '').startswith(('https://', 'http://')) or not review.get('rationale'):
            raise ValueError('Source identity rename must not masquerade as new land')
        if any(source['identity'] in [f['id'], f['properties'].get('metadata', {}).get('source_identity')] for f in before):
            raise ValueError('Existing source identity cannot be created again')
        same_name = sorted(f['id'] for f in before if f['properties'].get('name', '').casefold() == feature['properties'].get('name', '').casefold())
        if sorted(review.get('same_name_existing_ids', [])) != same_name:
            raise ValueError('Ambiguous existing name requires explicit identity review')
        parent = feature['properties']['parent_id']
        chain = []
        for tier in TIERS:
            unit = groups.get(parent)
            if not unit or unit['level'] != tier:
                raise ValueError('Creation has an incomplete adjacent-tier parent chain')
            chain.append(parent)
            parent = unit['parent_id']
        if parent is not None or chain != proof['parent_chain']:
            raise ValueError('Creation parent chain differs from reviewed proof')
        for j in tree.query(geometry, predicate='intersects'):
            other = after[int(j)]['id']
            if other == identifier:
                continue
            overlap = area(geometry.intersection(geoms[int(j)]))
            if overlap > .001:
                raise ValueError('Creation overlaps existing or competing land: ' + other)
        results.append({'location_id': identifier, 'land_area_m2': area(geometry), 'source_sha256': source['sha256'], 'parent_chain': chain})
    return {'verified': True, 'historical_claims_transferred': False, 'creations': results, 'area_tolerance_m2': .001}


if __name__ == '__main__':
    print(json.dumps(validate(json.load(sys.stdin)), separators=(',', ':')))

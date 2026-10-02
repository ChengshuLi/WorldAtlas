"""Audit source identities and propose geography repairs without changing the atlas.

Input source identity, not political ownership, determines a merge candidate.
All areas use the pinned WGS84 integral; proposals and evidence stay in .cache.
"""
from __future__ import annotations
import argparse, collections, functools, gzip, hashlib, json, pathlib, re, sqlite3, sys
from shapely import STRtree, make_valid, normalize, union_all, polygonize
from shapely.geometry import shape, mapping, Polygon, LineString
from majority import canonical
from ellipsoidal_area import area
ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
CACHE = ROOT / '.cache'


def read(path):
    return json.load(gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def geometry(g):
    return canonical(g) if any(p.bounds[2] - p.bounds[0] > 180 or p.bounds[0] < -180 or p.bounds[2] > 180 for p in pieces(g)) else make_valid(g)


def pieces(g):
    if g.geom_type == 'Polygon':
        return [g]
    return [p for q in getattr(g, 'geoms', ()) for p in pieces(q)]


def digest(g):
    return hashlib.sha256(normalize(g).wkb).hexdigest()


def raw_identity(identifier, prop):
    meta = prop.get('metadata', {})
    source = meta.get('source_id', '')
    if identifier.startswith('gb:'):
        return identifier
    if source.startswith('gb:') and re.fullmatch(r'atlas:district:[A-Z]{3}\+00\?:\d+B\d+', identifier):
        return source + ':' + identifier.rsplit(':', 1)[1]
    return None


def record_counts():
    result = collections.defaultdict(collections.Counter)
    path = DATA / 'atlas.sqlite'
    if not path.exists():
        return result, {'sqlite': 'unavailable; hosted evidence still requires review'}
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    for table, key in [('states', 'location_id'), ('attribute_records', 'location_id'), ('entity_history', 'entity_id')]:
        for identifier, example, count in conn.execute(f'SELECT {key},is_example,COUNT(*) FROM {table} GROUP BY {key},is_example'):
            result[identifier][table + ('_example' if example else '_sourced')] += count
    conn.close()
    return result, {'sqlite': 'read-only source snapshot', 'hosted': 'not inspected; publication must independently check imported hosted claims'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', default='data/source-territory-splits.json.gz')
    parser.add_argument('--proposal-directory', default='.cache/source-splits/proposals')
    args = parser.parse_args()
    paths = read(DATA / 'world-index.json')['parts']
    stamps = {p: sha(DATA / p) for p in paths}
    features = [f for p in paths for f in read(DATA / p)['features']]
    props = {f['properties']['id']: f['properties'] for f in features}
    by_id = {f['properties']['id']: f for f in features}
    assert len(props) == len(features), 'Duplicate current location IDs'
    geoms = [geometry(shape(f['geometry'])) for f in features]
    index = {f['properties']['id']: i for i, f in enumerate(features)}
    tree = STRtree(geoms)
    changes = {r['id']: r.get('replaces', []) for r in read(DATA / 'semantic-report.json')['changes']}
    unresolved = collections.Counter()

    @functools.lru_cache(None)
    def atoms(identifier, stack=()):
        if identifier in stack:
            unresolved['cycle'] += 1
            return ('unresolved:cycle:' + identifier,)
        prop = props.get(identifier, {})
        meta = prop.get('metadata', {})
        direct = raw_identity(identifier, prop)
        if direct:
            return (direct,)
        members = meta.get('source_member_ids') or changes.get(identifier)
        if members:
            return tuple(sorted({a for member in members for a in atoms(meta['source_id'] + ':' + member if meta.get('source_id', '').startswith('gb:') and re.fullmatch(r'\d+B\d+', member) else member, stack + (identifier,))}))
        if meta.get('source_id', '').startswith('gb:') and meta.get('original_id'):
            return (meta['source_id'] + ':' + meta['original_id'],)
        if meta.get('source_id', '').startswith('ISTAT:SLL2011-2018:'):
            return (meta['source_id'],)
        if identifier.startswith('country-'):
            return ('natural-earth:adm0:' + identifier.split('-', 1)[1],)
        if identifier.startswith('atlas:coverage:'):
            return ('natural-earth:adm1:' + identifier.split(':', 2)[2],)
        if re.fullmatch(r'[A-Z]{3}(?:-\d+|\+\d+\?)', identifier):
            return ('natural-earth:adm1:' + identifier,)
        if identifier.startswith(('atlas:district:BRA-', 'atlas:district:ESP-')):
            # Stable documented named functional region, not guessed municipality membership.
            return (identifier,)
        unresolved['leaf_without_registry'] += 1
        return ('unresolved:' + identifier,)

    membership = collections.defaultdict(list)
    by_location = {}
    for identifier in props:
        leaf = atoms(identifier)
        by_location[identifier] = leaf
        for atom in leaf:
            membership[atom].append(identifier)
    duplicates = {k: v for k, v in membership.items() if len(v) > 1}
    print(f'Identity scan: {len(features)} locations; {len(membership)} source identities; {len(duplicates)} repeated identities', flush=True)
    metadata = read(DATA / 'administrative-sources.json')
    sources = {}
    source_receipts = {}

    def source_atom(atom):
        if not atom.startswith('gb:'):
            return None
        source, sid = atom.rsplit(':', 1)
        if source not in sources:
            _, iso, level = source.split(':')
            path = CACHE / 'geoboundaries' / f'{iso}-{level}.json'
            if not path.exists():
                path = DATA / 'global-sources' / f'{iso}-{level}.geojson.gz'
            if path.exists():
                values = read(path)['features']
                sources[source] = {f['properties']['shapeID']: f for f in values}
                source_receipts[source] = {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'feature_count': len(values), 'declared_metadata': metadata.get(source), 'geometry_load': 'actual pinned cache inspected'}
            else:
                sources[source] = {}
                source_receipts[source] = {'status': 'original source geometry missing; no restoration approved'}
        return sources[source].get(sid)

    ne0_path = CACHE / 'ne_10m_admin_0_countries.json'
    ne1_path = CACHE / 'ne_10m_admin_1_states_provinces.json'
    ne0 = read(ne0_path)['features']
    ne1 = {f['properties']['adm1_code']: f for f in read(ne1_path)['features']}
    ref_name = {}
    for f in ne0:
        for key in ['ADMIN', 'NAME', 'NAME_LONG']:
            ref_name[f['properties'][key]] = f['properties']
    ref_masks = [geometry(shape(f['geometry'])) for f in ne0]
    ref_tree = STRtree(ref_masks)

    def reference_majority(g):
        total = area(g)
        territory = []
        polity_masks = collections.defaultdict(list)
        labels = {}
        for j in ref_tree.query(g, predicate='intersects'):
            j = int(j)
            q = ne0[j]['properties']
            cut = g.intersection(ref_masks[j])
            coverage = area(cut)
            if coverage <= max(1e-5, total * 1e-12):
                continue
            territory.append({'territory': q['ADMIN'], 'code': q['ADM0_A3'], 'share': coverage / total, 'classification': q['TYPE'], 'note': q.get('NOTE_BRK')})
            name = None if q['TYPE'] == 'Indeterminate' else q['SOVEREIGNT'] if q['TYPE'] in ['Country', 'Dependency', 'Lease'] and q['SOVEREIGNT'] in ref_name else q['ADMIN']
            if name is None:
                continue
            owner = ref_name.get(name, q)
            identifier = 'owner:' + owner['WIKIDATAID'] if owner.get('WIKIDATAID') and owner['WIKIDATAID'] != '-99' else 'owner:reference:' + owner['ADM0_A3']
            polity_masks[identifier].append(cut)
            labels[identifier] = name
        combined = {key: union_all(gs) for key, gs in polity_masks.items()}
        candidates = sorted([{'owner_id': key, 'name': labels[key], 'share': area(q) / total} for key, q in combined.items()], key=lambda x: (-x['share'], x['owner_id']))
        keys = list(combined)
        conflicts = [{'owner_ids': [a, b], 'area_km2': area(combined[a].intersection(combined[b])) / 1e6} for i, a in enumerate(keys) for b in keys[i+1:] if area(combined[a].intersection(combined[b])) > total * 1e-6]
        winning = candidates[0] if candidates and candidates[0]['share'] > .5 and not conflicts else None
        return {'method': 'strict >50% of entire proposed footprint; pinned ADM0 reference masks unioned by stable reference polity', 'status': 'reference-majority' if winning else 'disputed' if conflicts else 'no-majority', 'winner': winning, 'candidates': candidates, 'territory_coverage': sorted(territory, key=lambda x: (-x['share'], x['code'])), 'conflicts': conflicts, 'supported_interval': 'modern reference only; source dates vary, not verified 2026 or historical evidence', 'source_sha256': sha(ne0_path)}

    counts, evidence_scope = record_counts()
    proposal_dir = ROOT / args.proposal_directory
    proposal_dir.mkdir(parents=True, exist_ok=True)
    proposals = []

    def neighbors(g, member_ids):
        result = []
        for j in tree.query(g, predicate='intersects'):
            j = int(j)
            identifier = features[j]['properties']['id']
            if identifier in member_ids:
                continue
            overlap = area(g.intersection(geoms[j]))
            if overlap > 1e-5:
                result.append({'id': identifier, 'name': props[identifier]['name'], 'area_km2': overlap / 1e6})
        return sorted(result, key=lambda x: (-x['area_km2'], x['id']))

    def original_comparison(g, original, ids):
        if original is None:
            return {'status': 'source geometry unavailable'}
        source = geometry(shape(original['geometry']))
        total = area(source)
        intersection = area(g.intersection(source))
        return {'source_name': original['properties'].get('shapeName') or original['properties'].get('name') or original['properties'].get('ADMIN'), 'source_identity': original['properties'].get('shapeID') or original['properties'].get('adm1_code') or original['properties'].get('ADM0_A3'), 'source_geometry_sha256': digest(source), 'source_area_km2': total / 1e6, 'current_union_area_km2': area(g) / 1e6, 'current_union_intersection_source_km2': intersection / 1e6, 'source_coverage_share': intersection / total if total else None, 'current_union_outside_source_km2': area(g.difference(source)) / 1e6, 'whole_source_overlap_with_other_locations': neighbors(source, ids), 'restoration_policy': 'Measurements do not approve whole-source growth; only explicit union proposals preserve current coverage.'}

    def before(identifier):
        p = props[identifier]
        return {'id': identifier, 'name': p['name'], 'parent_id': p['parent_id'], 'reference_owner': p['reference_owner'], 'reference_polity_id': p['metadata'].get('reference_owner_id'), 'geometry_sha256': digest(geoms[index[identifier]]), 'area_km2': area(geoms[index[identifier]]) / 1e6, 'direct_records': dict(counts[identifier])}

    def propose(ids, retained, classification, originals, source_identity, rationale):
        g = union_all([geoms[index[i]] for i in ids])
        token = hashlib.sha256(('\n'.join(sorted(ids)) + '\n' + digest(g)).encode()).hexdigest()[:24]
        path = proposal_dir / (token + '.geojson.gz')
        after = {'type': 'Feature', 'properties': {'id': retained, 'name': props[retained]['name'], 'parent_id': props[retained]['parent_id']}, 'geometry': mapping(g)}
        with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as stream:
            stream.write(json.dumps(after, separators=(',', ':')).encode())
        collisions = neighbors(g, set(ids))
        recorded_owners = collections.defaultdict(list)
        for identifier in ids:
            owner = props[identifier]['metadata'].get('reference_owner_id')
            if owner:
                recorded_owners[owner].append(geoms[index[identifier]])
        reference_shares = sorted([{'owner_id': owner, 'share': area(union_all(gs)) / area(g)} for owner, gs in recorded_owners.items()], key=lambda x: (-x['share'], x['owner_id']))
        source_majority = {'method': 'Whole current source-record footprints unioned by their existing stable reference polity; independent polygon-majority evidence retained separately.', 'candidates': reference_shares, 'winner': reference_shares[0] if reference_shares and reference_shares[0]['share'] > .5 else None, 'status': 'reference-source-record-majority' if reference_shares and reference_shares[0]['share'] > .5 else 'no-majority', 'historical_transfer': False}
        proposal = {'proposal_id': 'source-union:' + token, 'classification': classification, 'status': 'exact-union-ready' if not collisions else 'blocked-neighbor-overlap', 'source_identity': source_identity, 'rationale': rationale, 'before': [before(i) for i in sorted(ids)], 'after': {'retained_id': retained, 'name': props[retained]['name'], 'parent_id': props[retained]['parent_id'], 'geometry_sha256': digest(g), 'area_km2': area(g) / 1e6, 'geometry_file': str(path.relative_to(ROOT)), 'geometry_file_sha256': sha(path)}, 'added_ids': [], 'removed_ids': sorted(i for i in ids if i != retained), 'changed_ids': [retained], 'source_comparisons': [original_comparison(g, original, set(ids)) for original in originals], 'other_location_overlaps': collisions, 'modern_reference_owner': reference_majority(g), 'reference_source_record_majority': source_majority, 'history_policy': 'Retain all original IDs, footprints, parent chains and direct claims in the archive. No retired-ID evidence is copied to the retained ID. Recompute geometry-derived ownership/environmental records only for changed/removed footprints; direct evidence requires scope review, including hosted imports.'}
        proposals.append(proposal)
        return proposal

    rows = []
    political = []
    for n, (atom, ids) in enumerate(sorted(duplicates.items())):
        g = union_all([geoms[index[i]] for i in ids])
        local = [props[i] for i in ids]
        clipped = [i for i in ids if props[i]['metadata'].get('location_basis') == 'Named district clipped to reference territorial envelope']
        physical = [i for i in ids if props[i]['metadata'].get('source_id', '').startswith(('ibra:', 'resolve:', 'aafc:')) or 'ecoregion' in props[i]['metadata'].get('location_basis', '').lower() or 'inland-water portion' in props[i]['metadata'].get('location_basis', '')]
        if clipped:
            classification = 'mixed-physical-and-political-partition' if physical else 'artificial-reference-owner-partition'
        elif atom.startswith('gb:TKM:'):
            classification = 'unnamed-source-defect-replaced-with-named-OSM-geography'
        elif physical or any('Disconnected components' in p['metadata'].get('location_basis', '') for p in local):
            classification = 'intentional-source-geographic-subdivision'
        else:
            classification = 'unresolved-repeated-source-identity'
        original = source_atom(atom)
        row = {'source_identity': atom, 'classification': classification, 'current_ids': sorted(ids), 'current_names': [props[i]['name'] for i in sorted(ids)], 'reference_owners': sorted({p['reference_owner'] for p in local}), 'source_roles': sorted({p['metadata'].get('location_basis') or p['metadata'].get('source_role') or p['metadata'].get('administrative_level', 'unspecified') for p in local}), 'member_union_sha256': digest(g), 'all_members_have_single_source_atom': all(len(by_location[i]) == 1 for i in ids), 'comparison': original_comparison(g, original, set(ids)), 'decision': 'Keep independently sourced ecological/geographic subdivisions; duplicate provenance is not duplicate territory.' if classification == 'intentional-source-geographic-subdivision' else 'Keep named OSM source corrections separate; an unnamed/bad-coordinate parent cannot define one coherent location.' if atom.startswith('gb:TKM:') else 'Open: inspect complete sourced ecological partition before removing the political cut.' if physical and clipped else 'Safe union proposal; no added land, one retained source identity.'}
        if classification == 'artificial-reference-owner-partition':
            retained = atom if atom in props else max(ids, key=lambda i: area(geoms[index[i]]))
            proposal = propose(ids, retained, classification, [original], atom, 'One exact named source shape was partitioned solely by independent political reference masks. Geographic identity must remain whole; determine one modern-reference polity separately by whole-footprint majority.')
            row['proposal_id'] = proposal['proposal_id']
            political.append(row)
        rows.append(row)
        if n % 100 == 0:
            print(f'Measured source identity {n}/{len(duplicates)}; union proposals {len(proposals)}', flush=True)

    # Cross-collection duplicates have distinct source IDs, so source-identity tracing alone cannot find them.
    collection_audit = []
    for territory, code, dedicated_prefix in [('American Samoa', 'ASM', 'ASM-'), ('Northern Mariana Islands', 'MNP', 'gb:MNP:')]:
        dedicated = [i for i, p in props.items() if p['reference_owner'] == territory and i.startswith(dedicated_prefix)]
        envelope = geometry(shape(next(f for f in ne0 if f['properties']['ADM0_A3'] == code)['geometry']))
        candidates = [i for i, p in props.items() if p['metadata'].get('source_id') == 'gb:USA:ADM2' and (p['metadata'].get('geographic_area_code') in ['SAM' if code == 'ASM' else 'MRN'] or geoms[index[i]].intersects(envelope))]
        for us in candidates:
            original = source_atom(us)
            if not original:
                collection_audit.append({'id': us, 'status': 'open-original-missing'})
                continue
            source_g = geometry(shape(original['geometry']))
            options = []
            for target in dedicated:
                other = source_atom(target) if target.startswith('gb:') else ne1.get(target)
                if not other:
                    continue
                q = geometry(shape(other['geometry']))
                intersection = area(q.intersection(source_g))
                score = intersection / min(area(q), area(source_g))
                options.append((score, target, other))
            options.sort(key=lambda r: (-r[0], r[1]))
            name_match = None
            if code == 'ASM':
                legal_counterparts = {'Western': 'ASM-5002', "Manu'a": 'ASM-4999', 'Rose Island': 'ASM-5000'}
                name_match = legal_counterparts.get(original['properties']['shapeName'])
                if name_match not in dedicated:
                    name_match = None
            if name_match:
                # Exact named county-equivalent/district/atoll identity with source-vintage
                # differences, not a nearest centroid or source-ADM integer selection.
                options = [q for q in options if q[1] == name_match]
            if not options or (not name_match and (options[0][0] < .9 or len(options) > 1 and options[1][0] >= .5)):
                collection_audit.append({'id': us, 'status': 'open-nonunique-source-footprint', 'options': [{'id': t, 'smaller_source_overlap': v} for v, t, _ in options]})
                continue
            score, target, other = options[0]
            proposal = propose([us, target], target, 'duplicate-parent-country-and-dedicated-territory-collections', [original, other], 'USA county-equivalent / ' + target, 'Original named county-equivalent and dedicated island/district/municipality source footprints identify the same local territory. Existing topology divided their shared coverage instead of selecting one source collection. Reunite existing covered land under the dedicated identity; preserve both original source vintages and original records.')
            collection_audit.append({'id': us, 'dedicated_id': target, 'original_smaller_source_overlap': score, 'source_identity_method': 'Named American Samoa district/island counterpart; full source-vintage geometry discrepancies remain explicit' if name_match else 'Unique original source footprint overlap above 90%', 'proposal_id': proposal['proposal_id'], 'status': proposal['status']})

    # The NE microstate footprint is a placeholder in BOTH source layers.
    # Reconstruct a licensed full-territory relation from exact ways, not an area target.
    vatican = None
    if 'VAT+00?' in props:
        identifier = 'VAT+00?'
        placeholder = next(f for f in ne0 if f['properties']['ADM0_A3'] == 'VAT')
        osm_path = CACHE / 'source-splits/evidence/vatican-osm-relation.json'
        if osm_path.exists():
            osm = read(osm_path)
            relation = next(r for r in osm['elements'] if r['type'] == 'relation' and r['id'] == 36989)
            assert relation['tags']['ISO3166-1:alpha3'] == 'VAT' and relation['tags']['wikidata'] == 'Q237'
            nodes = {r['id']: (r['lon'], r['lat']) for r in osm['elements'] if r['type'] == 'node'}
            ways = {r['id']: r for r in osm['elements'] if r['type'] == 'way'}
            lines = {'outer': [], 'inner': []}
            for member in relation['members']:
                if member['type'] == 'way' and member['role'] in lines:
                    lines[member['role']].append(LineString([nodes[i] for i in ways[member['ref']]['nodes']]))
            correct = union_all(list(polygonize(lines['outer']).geoms))
            if lines['inner']:
                correct = correct.difference(union_all(list(polygonize(lines['inner']).geoms)))
            assert correct.is_valid and not correct.is_empty
            affected = [features[int(j)]['properties']['id'] for j in tree.query(correct, predicate='intersects')]
            affected = sorted(set(affected + [identifier]))
            after_features = []
            for other in affected:
                g = correct if other == identifier else union_all(pieces(make_valid(geoms[index[other]].difference(correct))))
                assert not g.is_empty, ('Microstate restoration would retire whole neighbour; manual review required', other)
                after_features.append({'type': 'Feature', 'properties': {'id': other, 'name': props[other]['name'], 'parent_id': props[other]['parent_id']}, 'geometry': mapping(g)})
            token = hashlib.sha256(('VAT\n' + digest(correct)).encode()).hexdigest()[:24]
            path = proposal_dir / (token + '.geojson.gz')
            with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as stream:
                stream.write(json.dumps({'type': 'FeatureCollection', 'features': after_features}, separators=(',', ':')).encode())
            occupied = union_all([geoms[index[i]] for i in affected])
            source = {'path': str(osm_path.relative_to(ROOT)), 'file_sha256': sha(osm_path), 'url': 'https://www.openstreetmap.org/api/0.6/relation/36989/full.json', 'entity_id': 'osm:relation:36989', 'version': relation['version'], 'timestamp': relation['timestamp'], 'name': relation['tags']['name:en'], 'ISO3166-1:alpha3': 'VAT', 'wikidata': 'Q237', 'license': osm['license'], 'attribution': osm['copyright'], 'geometry_method': 'Exact nine outer ways joined by node IDs and polygonized; no buffer, rescale or equal-area target.', 'geometry_sha256': digest(correct), 'area_km2': area(correct) / 1e6}
            gb_path = CACHE / 'source-splits/evidence/vatican-gbOpen-ADM0.geojson'
            corroboration = None
            if gb_path.exists():
                gb = read(gb_path)['features'][0]
                corroboration = original_comparison(correct, gb, set(affected))
                corroboration.update({'url': 'https://www.geoboundaries.org/api/current/gbOpen/VAT/ADM0/', 'source_file_sha256': sha(gb_path), 'represented_year': 2017, 'license': 'Public Domain', 'note': 'Full footprint corroboration with 2017 Commons-derived source; does not overwrite newer OSM geometry.'})
            vatican = {'proposal_id': 'microstate-source-restoration:' + token, 'classification': 'cartographic-placeholder-replaced-with-full-named-territory-source', 'status': 'source-restoration-neighbour-adjustment-ready', 'source': source, 'source_corroboration': corroboration, 'before': [before(i) for i in affected], 'after': [{'id': f['properties']['id'], 'geometry_sha256': digest(shape(f['geometry'])), 'area_km2': area(shape(f['geometry'])) / 1e6} for f in after_features], 'added_ids': [], 'removed_ids': [], 'changed_ids': affected, 'geometry_file': str(path.relative_to(ROOT)), 'geometry_file_sha256': sha(path), 'NE_placeholder_comparison': original_comparison(geoms[index[identifier]], placeholder, {identifier}), 'missing_current_reference_land_km2': area(correct.difference(occupied)) / 1e6, 'modern_reference_owner': {'status': 'direct-source-reference', 'winner': {'owner_id': 'owner:Q237', 'name': 'Vatican', 'share': 1}, 'method': 'Exact named full-territory boundary tagged ISO VAT, Q237 and official_name Vatican City State; source direct reference supersedes the incomplete NE country glyph.', 'supported_interval': 'Modern reference at source version timestamp only; does not establish ancient attributes.', 'superseded_placeholder_majority': reference_majority(correct)}, 'history_policy': 'Retain before footprints and claims, no automatic transfer; recompute only affected source-approved footprints and attributes.', 'diagnosis': 'Actual pinned NE ADM0 and ADM1 both contain the same 0.0122058 km2 placeholder, not a 0.44 km2 territory. Topology further reduced it to 0.0105656 km2. Exact licensed full-territory source is 0.491621 km2; no arbitrary area target is used. Subtract its existing occupied land from named Roma neighbour while retaining IDs.', 'official_vatican_page': 'Blocked 403; no claim that the official page was inspected.'}
        else:
            vatican = {'status': 'blocked-full-territory-source-not-present', 'changed_ids': [], 'diagnosis': 'Both pinned NE source layers contain the same 0.0122058 km2 placeholder; switching layers cannot repair it.'}

    # Bad-source coordinates must not be expanded merely to obtain a visible cell.
    namibia = []
    missing = read(DATA / 'region-semantic-review.json').get('pixel_missing_source_comparison', [])
    for row in missing:
        identifier = row.get('location_id') or row.get('id')
        if identifier in props and (props[identifier]['metadata'].get('source_id', '').startswith('gb:NAM:') or props[identifier]['reference_owner'] == 'Namibia'):
            namibia.append({'id': identifier, 'name': props[identifier]['name'], 'before': before(identifier), 'source_metadata': metadata.get(props[identifier]['metadata'].get('source_id')), 'existing_source_comparison': row, 'decision': 'Blocked: independently replace bad 2007 source coordinates with a verified licensed source; no source-growth/cell reassignment proposal.'})

    namibia_profile = {'ids': sorted(i for i, p in props.items() if p['reference_owner'] == 'Namibia'), 'known_flag_ids': sorted(r['id'] for r in namibia), 'decision': 'No 2007 source polygon is grown to obtain grid representation; all remaining role/coordinate review is independent of these five known flags.', 'source_path': '.cache/geoboundaries/NAM-ADM2.json', 'source_sha256': sha(CACHE / 'geoboundaries/NAM-ADM2.json'), 'source_metadata': metadata.get('gb:NAM:ADM2')}

    affected = set(i for p in proposals for i in p['changed_ids'] + p['removed_ids']) | set(vatican['changed_ids'] if vatican else [])
    prepared = collections.defaultdict(collections.Counter)
    for folder, label in [('ownership-history', 'ownership_intervals'), ('reference-attributes', 'reference_attribute_records')]:
        manifest = read(DATA / folder / 'index.json')
        for entry in manifest['parts']:
            part = entry['path'] if isinstance(entry, dict) else entry
            for identifier, records in read(DATA / folder / part):
                if identifier in affected:
                    prepared[identifier][label] += len(records)
    end_stamps = {p: sha(DATA / p) for p in paths}
    if stamps != end_stamps:
        raise RuntimeError('Geography changed during audit; rerun before using proposals')
    report = {'version': 1, 'scope': 'Every current location source identity, all repeated provenance, dedicated territory collections and explicit microstate/source defects; dry-run only.', 'locations': len(features), 'inventory': {'location_ids': sorted(props), 'atoms_by_location': {i: list(by_location[i]) for i in sorted(props)}}, 'input_hashes': {'world-index': sha(DATA / 'world-index.json'), 'geography_parts': stamps, 'ellipsoidal_area.py': sha(ROOT / 'scripts/ellipsoidal_area.py'), 'majority.py': sha(ROOT / 'scripts/majority.py'), 'semantic-report': sha(DATA / 'semantic-report.json'), 'NaturalEarth_ADM0': sha(ne0_path), 'NaturalEarth_ADM1': sha(ne1_path)}, 'area_method': 'Pinned WGS84 ellipsoid latitude-strip integral with 16-point Gauss-Legendre quadrature; antimeridian canonicalization when source rings require it.', 'source_receipts': source_receipts, 'repeated_source_identities': rows, 'union_proposals': proposals, 'cross_collection_audit': collection_audit, 'vatican_restoration': vatican, 'namibia_source_defects': namibia, 'namibia_source_profile': namibia_profile, 'affected_prepared_record_counts': {i: dict(prepared[i]) for i in sorted(affected)}, 'history_preservation': {'scope': evidence_scope, 'direct_claims': {i: dict(counts[i]) for i in sorted(affected)}, 'original_archive_sha256': sha(DATA / 'geographic-migration-archive.json.gz'), 'required': ['Archive all before footprints, original names/parents and retired IDs.', 'Never copy retired-ID direct/history records to another ID solely because geometry is merged.', 'Preserve old ownership/attribute export dictionaries and unchanged tuples; recompute only changed/source-approved after footprints.', 'Record a geographic publication/version interval rather than overwrite geometry intended for a historical date.', 'Check independently imported hosted claims before publishing a migration.']}, 'summary': {'source_identity_count': len(membership), 'repeated_source_identities': len(rows), 'classifications': dict(collections.Counter(r['classification'] for r in rows)), 'union_proposals': len(proposals), 'proposal_statuses': dict(collections.Counter(p['status'] for p in proposals)), 'cross_collection_candidates': len(collection_audit), 'source_resolution': dict(unresolved), 'affected_ids': len(affected), 'new_land_added_by_unions_km2': 0, 'world_features_modified': False}}
    output = ROOT / args.report
    with gzip.GzipFile(filename=str(output), mode='wb', mtime=0) as stream:
        stream.write(json.dumps(report, ensure_ascii=False, separators=(',', ':')).encode())
    print(json.dumps(report['summary'], indent=2), flush=True)
    print(f'Report: {output}; all world features unchanged', flush=True)


if __name__ == '__main__':
    main()

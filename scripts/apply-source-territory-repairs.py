#!/usr/bin/env python3
"""Stage inspected source-identity repairs, leaving live geography and claims intact."""
import argparse, collections, copy, gzip, hashlib, importlib.util, json, pathlib
import sqlite3, subprocess
import numpy as np
from shapely import STRtree, intersection, make_valid, normalize, union_all
from shapely.geometry import shape, mapping
from majority import canonical
from ellipsoidal_area import area
ROOT = pathlib.Path(__file__).resolve().parents[1]
TIERS = ['location', 'province', 'area', 'region', 'subcontinent', 'continent']
NUMERICAL_AREA_TOLERANCE_M2 = .001  # Explicit floating-precision guard, never a land-growth policy.


def read(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as stream:
        return json.load(stream)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()
    if str(path).endswith('.gz'):
        with gzip.GzipFile(filename=str(path), mode='wb', mtime=0) as stream:
            stream.write(encoded)
    else:
        path.write_bytes(encoded)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(g):
    return hashlib.sha256(normalize(g).wkb).hexdigest()


def geometry(raw):
    g = shape(raw)
    # Preserve normal polygons exactly; canonical handles seam-spanning source rings.
    parts = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    return canonical(g) if any(p.bounds[2] - p.bounds[0] > 180 or p.bounds[0] < -180 or p.bounds[2] > 180 for p in parts) else g


def footprint_hash(features):
    code = "const fs=require('node:fs'),c=require('node:crypto');let f=JSON.parse(fs.readFileSync(0,'utf8'));f.sort((a,b)=>a[0].localeCompare(b[0]));process.stdout.write(c.createHash('sha256').update(JSON.stringify(f)).digest('hex'));"
    values = [[f['properties']['id'], f['geometry']] for f in features]
    return subprocess.check_output(['node', '-e', code], input=json.dumps(values, separators=(',', ':')).encode(), cwd=ROOT).decode()


def chains(features, units):
    result = {}
    for f in features:
        p = f['properties']; parent = p['parent_id']; chain = []
        for level in TIERS[1:]:
            if parent not in units or units[parent]['level'] != level:
                raise ValueError('Incomplete adjacent-tier chain: ' + p['id'])
            chain.append(parent); parent = units[parent]['parent_id']
        if parent is not None:
            raise ValueError('Continent must have no parent')
        result[p['id']] = chain
    return result


def prune(features, units):
    used = {u for chain in chains(features, units).values() for u in chain}
    retired = [copy.deepcopy(u) for id, u in units.items() if id not in used]
    active = {id: u for id, u in units.items() if id in used}
    counts = collections.Counter(f['properties']['parent_id'] for f in features)
    for u in active.values():
        if u['parent_id']: counts[u['parent_id']] += 1
    for id, u in active.items():
        if not counts[id]: raise ValueError('Empty surviving geographic group: ' + id)
        u.setdefault('metadata', {})['child_count'] = counts[id]
    return active, retired


def resolve_seams(g, proposal, by_id):
    receipts = []
    for neighbor in proposal.get('other_location_overlaps', []):
        if proposal['status'] != 'blocked-neighbor-overlap':
            raise ValueError('Unexpected neighbor overlap')
        other = geometry(by_id[neighbor['id']]['geometry'])
        cut = g.intersection(other); measured = area(cut)
        expected = neighbor['area_km2'] * 1e6
        if expected >= 1 or abs(measured - expected) > NUMERICAL_AREA_TOLERANCE_M2:
            raise ValueError('Only the pinned sub-square-metre numerical seams may be reconciled')
        revised = g.difference(other)
        if area(revised.difference(g)) > NUMERICAL_AREA_TOLERANCE_M2:
            raise ValueError('Numerical repair unexpectedly adds land')
        receipts.append({'neighbor_id': neighbor['id'], 'neighbor_name': by_id[neighbor['id']]['properties']['name'], 'neighbor_geometry_sha256': digest(other), 'removed_overlap_m2': measured, 'method': 'Exact difference against unchanged existing named neighbor footprint; removed land remains in neighbor, no buffering or cell reassignment.', 'before_geometry_sha256': digest(g), 'after_geometry_sha256': digest(revised)})
        g = revised
    return g, receipts


def stage_repairs(features, units, report, root=ROOT):
    before = copy.deepcopy(features); after = copy.deepcopy(features)
    by_id = {f['properties']['id']: f for f in after}
    before_by_id = {f['properties']['id']: f for f in before}
    if len(by_id) != len(after): raise ValueError('Duplicate current IDs')
    old_chains = chains(before, units)
    removed = set(); changed = set(); relationships = []; archives = []; coverage = []
    owner_labels = {f['properties'].get('metadata', {}).get('reference_owner_id'): f['properties'].get('reference_owner') for f in before}
    proposals = report['union_proposals'] + [report['vatican_restoration']]
    occupied = set()
    for proposal in proposals:
        before_ids = [p['id'] for p in proposal['before']]
        if occupied & set(before_ids): raise ValueError('Repair proposals share a current location')
        occupied.update(before_ids)
        for p in proposal['before']:
            if p['id'] not in by_id or digest(geometry(by_id[p['id']]['geometry'])) != p['geometry_sha256']:
                raise ValueError('Stale repair footprint: ' + p['id'])
        file_key = proposal.get('after', {}) if isinstance(proposal.get('after'), dict) else proposal
        path = root / file_key['geometry_file']
        if sha(path) != file_key['geometry_file_sha256']: raise ValueError('Pinned proposal file hash changed')
        if proposal['classification'] == 'cartographic-placeholder-replaced-with-full-named-territory-source':
            source = root / proposal['source']['path']
            if sha(source) != proposal['source']['file_sha256']: raise ValueError('Pinned OSM source changed')
            proposed = {f['properties']['id']: geometry(f['geometry']) for f in read(path)['features']}
            if set(proposed) != set(before_ids): raise ValueError('Vatican replacement ID set differs')
            if digest(proposed['VAT+00?']) != proposal['source']['geometry_sha256']: raise ValueError('Full Vatican source geometry differs')
            role = 'source-backed-footprint-replacement'; retained = None; seam_receipts = []
            for p in proposal['after']:
                if digest(proposed[p['id']]) != p['geometry_sha256']: raise ValueError('Replacement geometry changed')
        else:
            if proposal['status'] not in ['exact-union-ready', 'blocked-neighbor-overlap']: raise ValueError('Unapproved union proposal')
            retained = proposal['after']['retained_id']; g = geometry(read(path)['geometry'])
            expected = union_all([geometry(by_id[id]['geometry']) for id in before_ids])
            if digest(g) != proposal['after']['geometry_sha256'] or area(g.symmetric_difference(expected)) > NUMERICAL_AREA_TOLERANCE_M2:
                raise ValueError('Union does not preserve inspected member footprint')
            g, seam_receipts = resolve_seams(g, proposal, by_id)
            proposed = {retained: g}; removed.update(set(before_ids) - {retained}); role = 'source-backed-merge'
        before_union = union_all([geometry(by_id[id]['geometry']) for id in before_ids])
        after_union = union_all(list(proposed.values()))
        added_land = area(after_union.difference(before_union))
        lost = before_union.difference(after_union)
        neighbors = [geometry(by_id[r['neighbor_id']]['geometry']) for r in seam_receipts]
        uncovered_loss = area(lost.difference(union_all(neighbors))) if neighbors else area(lost)
        if max(added_land, uncovered_loss) > NUMERICAL_AREA_TOLERANCE_M2:
            raise ValueError('Repair changes world land coverage')
        coverage.append({'proposal_id': proposal['proposal_id'], 'added_land_m2': added_land, 'removed_member_coverage_m2': area(lost), 'removed_land_covered_by_unchanged_neighbors_m2': area(lost)-uncovered_loss, 'uncovered_loss_m2': uncovered_loss, 'numerical_seam_receipts': seam_receipts})
        for id in before_ids:
            original = before_by_id[id]
            archives.append({'id': id, 'feature': original, 'parent_chain': old_chains[id], 'geometry_sha256': digest(geometry(original['geometry'])), 'direct_records_at_audit': next(p for p in proposal['before'] if p['id'] == id).get('direct_records', {}), 'claims_policy': 'Original direct claims and historical intervals stay on original identity and footprint; no automatic transfer.'})
        for id, g in proposed.items():
            if g.is_empty or not g.is_valid: raise ValueError('Invalid repaired geometry')
            by_id[id]['geometry'] = mapping(g); changed.add(id)
            meta = by_id[id]['properties'].setdefault('metadata', {})
            meta['footprint_repair'] = {'proposal_id': proposal['proposal_id'], 'source_identity': proposal.get('source_identity') or proposal['source']['entity_id'], 'method': role, 'reference_only': True, 'history_transfer': False, 'rationale': proposal.get('rationale') or proposal['diagnosis'], 'remaining_boundary_review': 'Source vintages, coastlines and granularity require independent review.'}
            if id == 'VAT+00?':
                meta['footprint_repair']['original_source'] = {key: meta.get(key) for key in ['source_id', 'source_url', 'license', 'reference_year']}
                meta['geometry_source'] = proposal['source']
                meta['source_id'] = proposal['source']['entity_id']
                meta['source_url'] = proposal['source']['url']
                meta['license'] = proposal['source']['license']
                meta['reference_year'] = 2026
            if retained or id == 'VAT+00?':
                reference = proposal.get('modern_reference_owner', {})
                if not reference.get('winner') and reference.get('status') != 'disputed': reference = proposal.get('reference_source_record_majority', {})
                winner = reference.get('winner')
                meta['reference_owner_evidence'] = reference
                meta['reference_owner_id'] = winner['owner_id'] if winner else None
                by_id[id]['properties']['reference_owner'] = winner.get('name') or owner_labels.get(winner['owner_id']) if winner else None
        relationships.append({'before_ids': before_ids, 'after_ids': list(proposed), 'kind': role, 'proposal_id': proposal['proposal_id'], 'history_transfer': False, 'canonical_parent_policy': 'Retained stable source ID keeps its current geographically audited source parent; political winner never chooses a geographic parent.'})
    after = [f for f in after if f['properties']['id'] not in removed]
    active_units, retired_units = prune(after, copy.deepcopy(units))
    after_ids = {f['properties']['id'] for f in after}
    reused = set(by_id) - changed - removed
    for f in after:
        if f['properties']['id'] in reused:
            original = before_by_id[f['properties']['id']]
            if f != original: raise ValueError('Unchanged location properties or geometry modified')
    return before, after, active_units, {'changed_ids': sorted(changed), 'removed_ids': sorted(removed), 'added_ids': [], 'reused_ids': sorted(reused), 'relationships': relationships, 'archives': archives, 'retired_units': retired_units, 'coverage_checks': coverage, 'counts': {'before_locations': len(before), 'after_locations': len(after), 'changed_locations': len(changed), 'removed_locations': len(removed), 'reused_locations': len(reused), 'retired_groups': len(retired_units)}, 'source_evidence': [{'url': 'https://www.geoboundaries.org/', 'source_sha256': sha(root / 'data/source-territory-splits.json.gz'), 'inspected_receipt': 'data/source-territory-splits.json.gz'}, {'url': report['vatican_restoration']['source']['url'], 'source_sha256': report['vatican_restoration']['source']['file_sha256'], 'license': report['vatican_restoration']['source']['license'], 'attribution': report['vatican_restoration']['source']['attribution']}]}


def overlap_audit(features):
    geoms = [geometry(f['geometry']) for f in features]; tree = STRtree(geoms)
    result = []; candidates = 0
    for start in range(0, len(geoms), 2048):
        left, right = tree.query(geoms[start:start+2048], predicate='intersects'); left = left + start
        keep = left < right; left = left[keep]; right = right[keep]; candidates += len(left)
        cuts = intersection(np.asarray(geoms, dtype=object)[left], np.asarray(geoms, dtype=object)[right])
        for a, b, cut in zip(left, right, cuts):
            if cut.is_empty or cut.area <= 0: continue
            measured = area(cut)
            if measured <= 1e-5: continue
            result.append({'ids': sorted([features[int(a)]['properties']['id'], features[int(b)]['properties']['id']]), 'area_m2': measured})
        if start % 10240 == 0: print(f'Global overlap audit {start}/{len(geoms)}; {len(result)} positive pairs', flush=True)
    return {'locations_checked': len(geoms), 'candidate_pairs': candidates, 'positive_pairs': result, 'invalid_ids': [features[i]['properties']['id'] for i, g in enumerate(geoms) if not g.is_valid or g.is_empty]}


def original_source_archive(report):
    """Preserve the actual full source features, rather than only their hashes."""
    wanted = {}
    for proposal in report['union_proposals']:
        for row in proposal['source_comparisons']:
            wanted[row['source_identity']] = row['source_geometry_sha256']
    vat = report['vatican_restoration']
    wanted[vat['NE_placeholder_comparison']['source_identity']] = vat['NE_placeholder_comparison']['source_geometry_sha256']
    wanted[vat['source_corroboration']['source_identity']] = vat['source_corroboration']['source_geometry_sha256']
    found = {}
    paths = [ROOT / source['path'] for key, source in report['source_receipts'].items() if key in ['gb:SOM:ADM2', 'gb:MAR:ADM2', 'gb:USA:ADM2', 'gb:MNP:ADM2', 'gb:VAT:ADM0'] and source.get('path')]
    paths += [ROOT / '.cache/ne_10m_admin_0_countries.json', ROOT / '.cache/ne_10m_admin_1_states_provinces.json']
    vat_source = ROOT / '.cache/source-splits/evidence/vatican-gbOpen-ADM0.geojson'
    if sha(vat_source) != vat['source_corroboration']['source_file_sha256']: raise ValueError('Pinned Vatican corroborating source changed')
    if vat_source.exists() and vat_source not in paths: paths.append(vat_source)
    for path in paths:
        for feature in read(path)['features']:
            p = feature['properties']
            identifier = p.get('shapeID') or p.get('adm1_code') or p.get('ADM0_A3')
            if identifier not in wanted: continue
            fingerprint = digest(make_valid(geometry(feature['geometry'])))
            if fingerprint != wanted[identifier]: raise ValueError('Original raw source geometry differs: ' + identifier)
            found[identifier] = {'source_identity': identifier, 'source_path': str(path.relative_to(ROOT)), 'source_file_sha256': sha(path), 'geometry_sha256': fingerprint, 'feature': feature}
    if set(found) != set(wanted): raise ValueError('Missing original source features for archive: ' + str(set(wanted)-set(found)))
    return {'source_features': list(found.values()), 'osm_relation': read(ROOT / vat['source']['path']), 'osm_source': vat['source']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.cache/source-territory-repair-stage')
    parser.add_argument('--skip-global-audit', action='store_true', help='Prepare explicitly unvalidated staging only; never publication-ready.')
    args = parser.parse_args(); output = ROOT / args.output
    if output.exists(): raise ValueError('Output must be fresh')
    if output.resolve() == ROOT / 'data' or ROOT / 'data' in output.resolve().parents: raise ValueError('Stage must be outside live data')
    report_path = ROOT / 'data/source-territory-splits.json.gz'; report = read(report_path)
    checked_sources = {
        'world-index': ROOT / 'data/world-index.json',
        'ellipsoidal_area.py': ROOT / 'scripts/ellipsoidal_area.py',
        'majority.py': ROOT / 'scripts/majority.py',
        'semantic-report': ROOT / 'data/semantic-report.json',
        'NaturalEarth_ADM0': ROOT / '.cache/ne_10m_admin_0_countries.json',
        'NaturalEarth_ADM1': ROOT / '.cache/ne_10m_admin_1_states_provinces.json',
    }
    for key, path in checked_sources.items():
        if sha(path) != report['input_hashes'][key]: raise ValueError('Pinned audit input changed: ' + key)
    for key, source in report['source_receipts'].items():
        if source.get('path') and sha(ROOT / source['path']) != source['sha256']:
            raise ValueError('Pinned original source changed: ' + key)
    index = read(ROOT / 'data/world-index.json'); parts = index['parts']
    stamps = {p: sha(ROOT / 'data' / p) for p in parts}
    if stamps != report['input_hashes']['geography_parts']: raise ValueError('Global audit input parts have changed; rerun source audit')
    features = [f for p in parts for f in read(ROOT / 'data' / p)['features']]
    units_path = ROOT / 'data/hierarchy.json'; unit_stamp = sha(units_path)
    units = {u['id']: u for u in read(units_path)}
    before, after, active_units, receipt = stage_repairs(features, units, report)
    receipt.update(before_footprints_sha256=footprint_hash(before), after_footprints_sha256=footprint_hash(after), source_report_sha256=sha(report_path), preparation_script_sha256=sha(pathlib.Path(__file__)), before_hierarchy_sha256=unit_stamp, input_parts=stamps, numerical_area_tolerance_m2=NUMERICAL_AREA_TOLERANCE_M2, historical_claims_transferred=0, publication_ready=False)
    if receipt['before_footprints_sha256'] != read(ROOT / 'data/ownership-history/index.json')['footprints_sha256']:
        raise ValueError('Before snapshot does not match prepared ownership footprint hash')
    if not args.skip_global_audit:
        ba = overlap_audit(before); aa = overlap_audit(after)
        successors = {id: r['after_ids'][0] for r in receipt['relationships'] if r['kind'] == 'source-backed-merge' for id in r['before_ids']}
        baseline = collections.defaultdict(float)
        for pair in ba['positive_pairs']:
            ids = tuple(sorted(successors.get(id, id) for id in pair['ids']))
            if ids[0] != ids[1]: baseline[ids] += pair['area_m2']
        introduced = [p for p in aa['positive_pairs'] if p['area_m2'] > baseline[tuple(p['ids'])] + NUMERICAL_AREA_TOLERANCE_M2]
        receipt['global_geometry_audit'] = {'before': ba, 'after': aa, 'introduced_overlap_pairs': introduced, 'coverage_method': 'All changed proposal/member unions compared exactly, with lost numerical-seam land tested against named unchanged neighbor; every other location verified byte-identical.'}
        if aa['invalid_ids'] or introduced: raise ValueError('Global after geography introduces invalidity or positive overlaps')
        receipt['geometry_stage_validated'] = True
    if stamps != {p: sha(ROOT / 'data' / p) for p in parts} or unit_stamp != sha(units_path): raise ValueError('Live inputs changed during staging')
    originals = original_source_archive(report)
    output.mkdir(parents=True)
    for tag, values in [('before', before), ('after', after)]:
        directory = output / tag
        for n, start in enumerate(range(0, len(values), 1500)):
            write(directory / f'geography/part-{n}.json', {'type': 'FeatureCollection', 'features': values[start:start+1500]})
        write(directory / 'world-index.json', {'parts': [f'geography/part-{n}.json' for n in range((len(values)+1499)//1500)]})
    write(output / 'after/hierarchy.json', list(active_units.values()))
    write(output / 'before/hierarchy.json', list(units.values()))
    conn = sqlite3.connect(f'file:{ROOT / "data/atlas.sqlite"}?mode=ro', uri=True)
    boundaries = [list(r) for r in conn.execute('SELECT location_id,valid_from,valid_to,geometry FROM boundaries WHERE is_example=0')]
    affected = sorted(set(receipt['changed_ids']) | set(receipt['removed_ids']))
    preserved_records = {}
    for table, key in [('states', 'location_id'), ('attribute_records', 'location_id'), ('entity_history', 'entity_id'), ('boundaries', 'location_id')]:
        cursor = conn.execute(f'SELECT * FROM {table} WHERE {key} IN ({",".join("?" for _ in affected)}) ORDER BY id', affected)
        columns = [c[0] for c in cursor.description]
        preserved_records[table] = [dict(zip(columns, row)) for row in cursor]
    conn.close()
    receipt['local_record_preservation'] = {'affected_ids': affected, 'counts': {table: len(rows) for table, rows in preserved_records.items()}, 'sha256': hashlib.sha256(json.dumps(preserved_records, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'policy': 'Original local records remain on original IDs; full copies archived without transfer. Hosted imports must be independently checked before publication.'} 
    removed = set(receipt['removed_ids'])
    if any(row[0] in removed for row in boundaries): raise ValueError('Removed IDs have dated footprints requiring explicit scope decision')
    write(output / 'before-boundaries.json', boundaries); write(output / 'after-boundaries.json', boundaries)
    write(output / 'original-source-geometry.json.gz', originals)
    receipt['original_source_archive'] = {'path': 'original-source-geometry.json.gz', 'sha256': sha(output / 'original-source-geometry.json.gz'), 'source_features': len(originals['source_features']), 'osm_relation_version': report['vatican_restoration']['source']['version']}
    write(output / 'migration-receipt.json', receipt)
    write(output / 'archive.json.gz', {'locations': receipt['archives'], 'units': receipt['retired_units'], 'records': preserved_records, 'history_transfer': False})
    print(json.dumps({'stage': str(output), 'geometry_stage_validated': receipt.get('geometry_stage_validated', False), 'publication_ready': receipt['publication_ready'], **receipt['counts'], 'before_footprints_sha256': receipt['before_footprints_sha256'], 'after_footprints_sha256': receipt['after_footprints_sha256']}))


if __name__ == '__main__': main()

#!/usr/bin/env python3
"""Fail-closed integrity and scope checks for the #487 evidence packet."""
import gzip, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def check(condition, message):
    if not condition:
        raise SystemExit(f"FAIL: {message}")

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def verify_record(record, path_key, bytes_key, sha_key):
    p = ROOT / record[path_key]
    check(p.is_file(), f"missing retained source {p}")
    check(p.stat().st_size == record[bytes_key], f"byte count mismatch: {p}")
    check(digest(p) == record[sha_key], f"SHA-256 mismatch: {p}")

def main():
    scope = json.loads((ROOT/'scope.json').read_text())
    packet = json.loads((ROOT/'assessment.json').read_text())
    assigned = scope['member_location_ids']
    rows = packet['locations']
    row_ids = [r['location_id'] for r in rows]
    check(len(assigned) == 100 and len(set(assigned)) == 100, 'scope must contain 100 unique IDs')
    check(len(rows) == 100 and set(row_ids) == set(assigned), 'assessment must account for every assigned ID exactly once')
    check(packet['scope']['assigned_count'] == 100, 'packet scope count mismatch')
    check(packet['decision_counts'] == {'justified': 96, 'correction_needed': 4, 'insufficient_evidence': 0}, 'decision accounting changed')
    for row in rows:
        chain = row['full_parent_chain']
        check([n['level'] for n in chain] == ['location','province','area','region','subcontinent','continent'], f"incomplete parent chain: {row['location_id']}")
        check(chain[-1]['name'] == 'North America', f"wrong continent: {row['location_id']}")
        check(row.get('settlement_screen') is not None, f"missing settlement assessment: {row['location_id']}")
        check(row.get('remainders_islands_disconnected_review') is not None, f"missing remainder/island assessment: {row['location_id']}")
    check(sum(1 for r in rows if r['parent_state']=='California') == 61, 'California parent cohort mismatch')
    check(sum(1 for r in rows if r['parent_state']=='Washington') == 39, 'Washington parent cohort mismatch')
    check(packet['source_accounting']['assigned_2018_source_counties'] == 97, 'source county roster mismatch')
    check(packet['source_accounting']['direct_current_county_rows'] == 96, 'direct county row count mismatch')
    check(packet['source_accounting']['physical_fragments'] == 4, 'physical fragment count mismatch')
    check(packet['source_accounting']['unaccounted_source_counties_in_full_state_cohort'] == 0, 'unaccounted source counties')
    sources = json.loads((ROOT/'sources.json').read_text())
    for s in sources['sources']:
        for item in ('retained_data',):
            if item in s:
                d=s[item]; verify_record(d,'path','compressed_bytes','compressed_sha256')
                raw=gzip.open(ROOT/d['path'],'rb').read()
                check(len(raw)==d['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==d['uncompressed_sha256'], f"uncompressed source mismatch: {d['path']}")
        for item in ('retained_features','retained_scope_data'):
            if item in s:
                d=s[item]; verify_record(d,'path','compressed_bytes','compressed_sha256')
                raw=gzip.open(ROOT/d['path'],'rb').read()
                check(len(raw)==d['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==d['uncompressed_sha256'], f"uncompressed source mismatch: {d['path']}")
        if 'retained_feature' in s:
            d=s['retained_feature']; verify_record(d,'path','compressed_bytes','compressed_sha256')
            raw=gzip.open(ROOT/d['path'],'rb').read()
            check(len(raw)==d['uncompressed_bytes'] and hashlib.sha256(raw).hexdigest()==d['uncompressed_sha256'], 'Abbotsford feature checksum mismatch')
        for item in ('retained_metadata','retained_item_metadata','retained_service_metadata','retained_layer_metadata'):
            if item in s:
                d=s[item]; verify_record(d,'path','bytes','sha256')
        if 'retained' in s:
            d=s['retained']; verify_record(d,'path','bytes','sha256')
    for path, size, sha in [
        ('sources/tigerline-2024-ca-places.zip',9792773,'81b827124043164a93d442f6dc4c088fd56c319da14195e4a14ab0fb39656a42'),
        ('sources/tigerline-2024-wa-places.zip',2856695,'7da61ba276bfdd886ffeb36bf9af37a99a42f8c446e47c684ae48087d86657c6'),
        ('sources/gshhg-LGPL.txt',7651,'da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768'),
    ]:
        p=ROOT/path; check(p.stat().st_size==size and digest(p)==sha, f"retained source integrity mismatch: {path}")
    screen=json.loads((ROOT/'gshhg-pacific-screen.json').read_text())
    check(screen.get('scope_count',screen.get('current_scope_count'))==100 and sum(1 for r in screen['per_location'].values() if r.get('representative_point_in_level1_land'))==99, 'GSHHG screening totals changed')
    portions=json.loads((ROOT/'derived-portion-audit.json').read_text())
    check(portions['fragment_count']==4 and portions['parent_union']['intersection_over_predecessor_pct']>99.9, 'San Bernardino overlay evidence changed')
    canada=json.loads((ROOT/'neighbor-canada-screen.json').read_text())
    pair=canada['near_or_touching_pairs'][0]
    check(pair['assigned_name']=='Whatcom' and pair['neighbor_name']=='Abbotsford' and abs(pair['shared_line_m']-39105.384)<0.001, 'cross-border contact finding changed')
    nbr=json.loads((ROOT/'neighbor-screen.json').read_text())
    diffs=nbr['current_pair_graph_difference_metrics']
    check(len(diffs)==17 and all(x['current_atlas']['shared_boundary_m']==0 for x in diffs), '2024 vs current pair-lead count changed')
    ext=[x for x in diffs if {x['left']['name'],x['right']['name']}=={'Clatsop','Pacific'}]
    check(len(ext)==1 and abs(ext[0]['tigerline_2024']['shared_boundary_m']-41324.968)<0.01, 'Clatsop–Pacific edge missing')
    alameda=[x for x in diffs if {x['left']['name'],x['right']['name']}=={'Alameda','San Francisco'}]
    check(len(alameda)==1 and abs(alameda[0]['geoboundaries_2018']['shared_boundary_m']-357.251)<0.01, 'Alameda–San Francisco source edge missing')
    print('PASS: 100/100 IDs, complete parent chains, 96/4 decisions, source checksums, four physical overlays, 17 water-edge leads, and cross-border contact reproduced.')

if __name__=='__main__': main()

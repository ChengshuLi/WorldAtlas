#!/usr/bin/env python3
"""Validate issue 496 evidence accounting and retained source bytes."""
import gzip, hashlib, json, pathlib, sys
HERE=pathlib.Path(__file__).resolve().parent
scope=json.loads((HERE/'scope.json').read_text())
a=json.loads((HERE/'assessment.json').read_text())
sources=json.loads((HERE/'sources.json').read_text())
ids=scope['member_location_ids']
rows=a['locations']
assert len(ids)==228 and len(set(ids))==228
assert len(rows)==len(ids) and {r['location_id'] for r in rows}==set(ids)
assert all(r.get('full_parent_chain') and r.get('decision') and r.get('unresolved') for r in rows)
assert all(r.get('settlement_review','').startswith('unresolved:') for r in rows)
assert all(r.get('island_and_disconnected_land_review','').startswith('unresolved:') for r in rows)
assert sum(r['decision']=='correction_needed' for r in rows)==1
assert sum(r['decision']=='insufficient_evidence' for r in rows)==227
assert len(a['parents'])==33
assert a['decision_summary']['assessed']==228
assert a['decision_summary']['per_location_decision_recorded']==228
for src in sources['sources']:
    for key in ('original_file','retained_fact_extract','derived_roster'):
        part=src.get(key)
        if part and 'retained_path' in part:
            p=(HERE/part['retained_path']).resolve()
            if not p.exists():
                if src.get('id')=='inei-bulletin-26' and 'retained_in' in src: continue
                raise AssertionError(f'missing retained byte file {p}')
            raw=p.read_bytes()
            assert len(raw)==part['bytes'], (p,len(raw),part['bytes'])
            assert hashlib.sha256(raw).hexdigest()==part['sha256'], p
# The Peru source is a read-only peer artifact; validate it when present.
peer=HERE.parent/'regional-review-d2dae235991eaa49/sources/geoboundaries-PER-ADM2-2020.geojson.gz'
if peer.exists():
    item=next(s for s in sources['sources'] if s['id']=='geoboundaries-per-adm2-2020')
    compressed=peer.read_bytes()
    assert hashlib.sha256(compressed).hexdigest()==item['stored_compressed_sha256']
    assert hashlib.sha256(gzip.decompress(compressed)).hexdigest()==item['uncompressed_sha256']
# Verify selected GSHHG source records and their report.
g=json.loads((HERE/'gshhg-screen.json').read_text())
p=HERE/g['selection']['retained_file']; packed=p.read_bytes(); raw=gzip.decompress(packed)
assert hashlib.sha256(packed).hexdigest()==g['selection']['retained_compressed_sha256']
assert hashlib.sha256(raw).hexdigest()==g['selection']['retained_uncompressed_sha256']
assert len(raw)==g['selection']['retained_bytes']
assert len(g['source_land_candidates'])==g['selection']['record_count']
allg=json.loads((HERE/'gshhg-scope-screen.json').read_text())
assert allg['scope_count']==len(ids) and set(allg['per_location'])==set(ids)
for row in rows:
    assert row['physical_source_screen']['level1_centroid_hits']==allg['per_location'][row['location_id']]['level1_centroid_hits']
ret=allg['retained']; q=(HERE/ret['path']).read_bytes(); qr=gzip.decompress(q)
assert len(qr)==ret['uncompressed_bytes'] and hashlib.sha256(qr).hexdigest()==ret['uncompressed_sha256']
assert len(q)==ret['compressed_bytes'] and hashlib.sha256(q).hexdigest()==ret['compressed_sha256']
assert len(allg['matched_source_records'])==ret['record_count']
print(json.dumps({'verified':True,'assigned':len(ids),'assessed':len(rows),'parents':len(a['parents']),'source_register_entries':len(sources['sources']),'galapagos_gshhg_records':len(g['source_land_candidates']),'all_scope_gshhg_records':len(allg['matched_source_records']),'locations_with_land_centroid_hits':sum(x['level1_centroid_hits']>0 for x in allg['per_location'].values())},indent=2))

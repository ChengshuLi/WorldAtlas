#!/usr/bin/env python3
"""Verify exhaustive issue 491 accounting, pins and reproducible neighbor result."""
import gzip,hashlib,json,pathlib
H=pathlib.Path(__file__).resolve().parent
s=json.loads((H/'scope.json').read_text()); a=json.loads((H/'assessment.json').read_text()); n=json.loads((H/'neighbor-screen.json').read_text()); r=json.loads((H/'sources.json').read_text())
ids=s['member_location_ids']; rows=a['locations']
assert len(ids)==190 and len(set(ids))==190 and len(rows)==190
assert {x['location_id'] for x in rows}==set(ids)
assert all(x['decision']=='insufficient_evidence' and x['full_parent_chain'] for x in rows)
assert all(x['source_identity']['geoBoundaries_shape_id']==x['source_identity']['original_id'] for x in rows)
assert all(x['source_identity']['name_exact'] for x in rows)
assert a['counts']=={'assessed':190,'source_id_matches':190,'exact_name_matches':190,'justified':0,'correction_needed':0,'insufficient_evidence':190}
g=json.loads((H/'gshhg-colombia-screen.json').read_text())
assert g['scope_count']==190 and set(g['per_location'])==set(ids)
assert sum(1 for x in g['per_location'].values() if x['representative_point_in_level1_land'])==190
assert len(g['matched_source_records'])==30
ret=g['retained']; b=(H/ret['path']).read_bytes(); rawg=gzip.decompress(b)
assert len(b)==ret['compressed_bytes']==1764872 and hashlib.sha256(b).hexdigest()==ret['compressed_sha256']=='f75a44b00939519bc4822a4343023aafd9a81c606c7f46cc2c4cd1a9cf073580'
assert len(rawg)==ret['uncompressed_bytes']==2721616 and hashlib.sha256(rawg).hexdigest()==ret['uncompressed_sha256']=='bcc737fcc80322b50a69a6f58e5302db7c5686dee5ddb2ccb950e8f20b5cc402'
assert len(a['provinces'])==7 and sum(p['assigned_descendants'] for p in a['provinces'])==190
assert all(p['complete_province_cohort'] for p in a['provinces'])
assert n['assigned_count']==190 and len(n['per_location'])==190
pair=json.loads((H/'putumayo-pair-investigation.json').read_text())
assert pair['metrics']['source_common_edge_m']==8261.9311262635
assert pair['metrics']['current_exact_shared_edge_m']==0
assert 8180 < pair['metrics']['source_edge_within_5m_of_current_a_m'] < 8190
assert 8180 < pair['metrics']['source_edge_within_5m_of_current_b_m'] < 8190
assert n['source_assigned_internal_neighbor_pair_count']==459 and n['current_assigned_internal_neighbor_pair_count']==458
assert n['assigned_internal_pair_graph_differences']==1
assert n['source_pairs_missing_current']==[['gb:COL:ADM2:7082276B25468013916959','gb:COL:ADM2:7082276B42533804398270']]
source=H.parent/'regional-review-b2e551685bf2e064/sources/geoboundaries-COL-ADM2-2020.geojson.gz'; packed=source.read_bytes(); raw=gzip.decompress(packed)
assert len(packed)==74845471 and hashlib.sha256(packed).hexdigest()=='586b057e43ca97d608148d5f3b3067a25bb468a94a7cac6d3c1c2ffb8eb20e3d'
assert len(raw)==210605856 and hashlib.sha256(raw).hexdigest()=='fe715854fc3383d2fd39e8692f3df0c60bd12208cb2cd36ef1ec2220ea8972fe'
d=json.loads(raw); by={f['properties']['shapeID']:f for f in d['features']}; assert len(by)==1122
assert {x['source_identity']['original_id'] for x in rows} <= set(by)
print(json.dumps({'verified':True,'assessed':190,'province_cohorts':{x['name']:x['assigned_descendants'] for x in a['provinces']},'source_identity_matches':190,'source_exact_edge_pairs':459,'current_exact_edge_pairs':458,'candidate_pair':n['source_pairs_missing_current'][0]},ensure_ascii=False,indent=2))

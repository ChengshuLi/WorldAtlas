import json,gzip,hashlib,subprocess,sys,bisect
from pathlib import Path
R=sys.argv[1];OUT=Path(sys.argv[2]);OUT.mkdir(parents=True,exist_ok=True)
BASE='cd1886f20f34abdcafe7c327ae0ee768ce5d47ae'
inputs=[]
def raw(ref):
 b=subprocess.check_output(['git','--no-lazy-fetch','-C',R,'show',ref]);inputs.append({'git_ref':ref,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob_oid':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()});return b
def read(ref):return json.loads(raw(ref))
def sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
s=read(BASE+':data/ownership-selection.json');p=s['additive_release'];b=raw(BASE+':'+p['path']);assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];side=json.loads(b);p=side['logical_asset_map']['patch'];b=raw(p['commit']+':'+p['path']);assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'];patch=json.loads(b)
selected={r['y']:r['runs'] for r in patch['rows']};starts={y:[r[0] for r in rr] for y,rr in selected.items()}
def selected_owner(y,x):
 rr=selected.get(y,[]);i=bisect.bisect_right(starts.get(y,[]),x)-1
 return rr[i][2] if i>=0 and rr[i][0]<=x<rr[i][1] else None
cfg=[('SWE',BASE,'coordination/engineering/sweden-original-repair-20261017/', 'original-extraction-002/',range(14,21),'native-request-001/native-requested-patch.json',[(68544,141221,40710)],18381,18380),('SLV','32d819ddc9333ff025584665665c963822dfcead','coordination/engineering/americas-following-original-evaluations-20261018/','source-packets/SLV/original-intervals/',[29],'source-packets/SLV/original-native-requested-patch.json',[(121014,67180,39827),(121199,67200,39842),(121202,67198,39842)],1134,1131)]
roster={x['source_index']:x for x in json.loads(gzip.decompress(raw(BASE+':coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz')))}
reports=[]
for country,h,prefix,blocks,ns,requested,expected,no,na in cfg:
 cells={};segments=[]
 for n in ns:
  rows=json.loads(gzip.decompress(raw(h+':'+prefix+blocks+f'block-{n:03}.json.gz')));segments+=rows
  for y,a,b,owners,sids,physical in rows:
   assert len(owners)==1
   for x in range(a,b):
    k=(y,x,owners[0]);assert k not in cells;cells[k]={'source_feature_indices':sids,'physical_class':physical}
 requested_cells=set()
 for row in read(h+':'+prefix+requested)['rows']:
  for a,b,o in row['runs']:
   for x in range(a,b):requested_cells.add((row['y'],x,o))
 assert requested_cells==set(cells)
 accepted=[];unassigned=[];different=[]
 for k in sorted(cells):
  o=selected_owner(k[0],k[1])
  (accepted if o==k[2] else unassigned if o is None else different).append(k)
 assert len(cells)==no and len(accepted)==na and not different and unassigned==sorted(expected)
 records=[{'y':y,'x':x,'owner':o,**cells[(y,x,o)],'original_source_contacts':[roster[i] for i in cells[(y,x,o)]['source_feature_indices']]} for y,x,o in unassigned]
 evidence=read('e76a95f71e8fe9de4c4168b1763bee3d2e2e603d' if country=='SWE' else '02794b6a7ad0c369b38ec5714a81aef558a24752')
 for r in records:
  targets=[t for t in evidence['targets'] if t['pixelIndex']==r['owner']];assert len(targets)==1;t=targets[0]
  assert any(row['y']==r['y'] and any(a<=r['x']<b and c=='mapped_land_support' for a,b,c in row['runs']) for row in t['coverage_rows'])
  r['positive_original_target_id']=t['target_id'];r['positive_original_coverage_class']='mapped_land_support'
  r['proposed_disposition']='documented-unresolved-source-applicability-exception';r['scientific_territorial_hold_retained']=True;r['native_repair_credit']=0
 assert all(r['physical_class']=='land' for r in records)
 report={'package_id':f'gb-{country}-ADM2--repair-evaluation','original_interval_read_commit':h,'accepted_selection_commit':BASE,'original_cells':len(cells),'original_intervals':len(segments),'original_owners':len({k[2] for k in cells}),'accepted_original_owner_cells':len(accepted),'proposed_documented_exceptions':len(unassigned),'different_owner_intersections':different,'original_key_sha256':sha(sorted(cells)),'accepted_original_key_sha256':sha(accepted),'proposed_exception_key_sha256':sha(unassigned),'original_equals_requested_patch':True,'partition_exhaustive_disjoint':True,'exception_records':records,'new_native_repairs':0,'accepted_disposition_credit':0,'status':'proposed; independent substantive review and accepted integration required'}
 (OUT/(country.lower()+'-original-partition.json')).write_text(json.dumps(report,indent=2)+'\n');reports.append(report)
(OUT/'input-custody.json').write_text(json.dumps({'baseline':BASE,'inputs':inputs,'no_scientific_producer_executed':True},indent=2)+'\n')
print(json.dumps(reports,indent=2))

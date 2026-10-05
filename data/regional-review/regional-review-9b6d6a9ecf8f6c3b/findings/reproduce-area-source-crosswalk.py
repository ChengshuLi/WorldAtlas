#!/usr/bin/env python3
"""Reproduce the bounded WGSRPD level/name crosswalk; this is not a boundary test."""
import argparse, csv, hashlib, json, re, sys
from pathlib import Path

L3_SHA = '7eaf281dfbdca610c93938326c333d7c62d8e82ce3cba63b299d5a3a01d0003f'
L4_SHA = '6fa350a0bb5939df0c665ae6cf253ddb0aa85fef6daa684c87ba400faf93b1c2'
HIERARCHY_SHA = '568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b'
AREAS = {
 'framework:area:chile-central:4657b9c2c6bd': ('Chile Central', 'CLC', 31),
 'framework:area:chile-north:dae240b20a69': ('Chile North', 'CLN', 10),
 'framework:area:chile-south:f59e68fc819a': ('Chile South', 'CLS', 14),
 'framework:area:juan-fernandez-is:fba2727a951e': ('Juan Fernández Is.', 'JNF', 1),
 'framework:area:paraguay:b8f36a1a90ee': ('Paraguay', 'PAR', 18),
}

def checked_bytes(path, expected):
 data = Path(path).read_bytes()
 actual = hashlib.sha256(data).hexdigest()
 if actual != expected: raise ValueError(f'{path}: SHA-256 {actual}, expected {expected}')
 return data

def parse(lines, fields):
 result=[]
 for n,line in enumerate(lines[1:],2):
  parts=line.split('*')
  if len(parts)<fields: raise ValueError(f'invalid delimited source line {n}')
  result.append(parts)
 return result

def norm(s): return re.sub(r'[^a-z0-9]+','',s.casefold().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ñ','n'))

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--level3',required=True); ap.add_argument('--level4',required=True)
 ap.add_argument('--hierarchy',default='data/hierarchy.json')
 ap.add_argument('--parents',default='data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/province-review.csv')
 ap.add_argument('--areas',default='data/regional-review/regional-review-9b6d6a9ecf8f6c3b/findings/area-review.csv')
 ap.add_argument('--workload-scope',default='data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/embedded-workload-scope.json')
 ap.add_argument('--companion-scopes',default='data/regional-review/regional-review-9b6d6a9ecf8f6c3b/scope/companion-workload-scopes.json')
 ap.add_argument('--output',required=True)
 a=ap.parse_args()
 l3=parse(checked_bytes(a.level3,L3_SHA).decode('cp1252').splitlines(),6); l4=parse(checked_bytes(a.level4,L4_SHA).decode('cp1252').splitlines(),6)
 hierarchy=json.loads(checked_bytes(a.hierarchy,HIERARCHY_SHA).decode('utf-8'))
 areas={x['id']:x for x in hierarchy if x.get('level')=='area' and x.get('id') in AREAS}
 if len(areas)!=5: raise ValueError('expected exactly five issue areas in hierarchy')
 source3={x[0]:x for x in l3}
 source4={code:[x for x in l4 if x[2]==code] for _,code,_ in AREAS.values()}
 with open(a.areas,newline='',encoding='utf-8') as f: area_rows={x['area_id']:x for x in csv.DictReader(f)}
 if set(area_rows)!=set(AREAS): raise ValueError('area-review.csv does not contain exactly the five declared area IDs')
 rows=[]
 for aid,(name,code,expected_children) in AREAS.items():
  area=areas[aid]; s=source3.get(code)
  if area.get('metadata',{}).get('child_count') != expected_children: raise ValueError(f'Atlas hierarchy count mismatch for {name}')
  if not s or s[1]!=name or s[2]!='85,00' or s[3]!=('PY' if code=='PAR' else 'CL'):
   raise ValueError(f'WGSRPD L3 mismatch for {name}: {s}')
  units=source4[code]
  if len(units)!=({'CLC':7,'CLN':3,'CLS':3,'JNF':1,'PAR':1}[code]): raise ValueError(f'unexpected L4 count for {code}')
  area_scope=area_rows[aid]
  if area_scope['area_name']!=name: raise ValueError(f'Area review name mismatch for {aid}')
  rows.append({'record_type':'area','area_id':aid,'area_name':name,'area_owned_member_count':area_scope['owned_member_count'],'full_area_member_count':area_scope['full_area_member_count'],'scope_companion_issues':{'Chile Central':'#444','Paraguay':'#446'}.get(name,''),'parent_id':area.get('parent_id',''),
    'atlas_province_child_count':area['metadata']['child_count'],'wgsrpd_code':code,'wgsrpd_l2':'85,00',
    'wgsrpd_l4_count':len(units),'wgsrpd_l4_names':'; '.join(x[1] for x in units),
    'atlas_to_l4_name_match':'not_equivalent_tier','scope_note':'Source scale/name crosswalk only; no completeness, legal-parent or boundary finding.'})
 with open(a.parents,newline='',encoding='utf-8') as f: parents=list(csv.DictReader(f))
 scope=json.loads(Path(a.workload_scope).read_text())
 issue_ids=scope['member_location_ids']
 if len(issue_ids)!=215 or len(set(issue_ids))!=215 or hashlib.sha256('\n'.join(issue_ids).encode()).hexdigest()!=scope['member_location_ids_sha256']: raise ValueError('current issue workload scope/hash is not the exact unique 215-ID roster')
 companions=json.loads(Path(a.companion_scopes).read_text())['issues']
 if len(companions)!=2 or {x['issue'] for x in companions}!={444,446}: raise ValueError('expected exact companion scope snapshots for #444 and #446')
 companion_by_number={x['issue']:x for x in companions}
 for n,snapshot in companion_by_number.items():
  ids=snapshot['member_location_ids']
  if len(set(ids))!=len(ids) or hashlib.sha256('\n'.join(ids).encode()).hexdigest()!=snapshot['member_location_ids_sha256']:
   raise ValueError(f'companion #{n} roster/hash mismatch')
  if set(ids)&set(issue_ids): raise ValueError(f'companion #{n} overlaps issue #445 subject IDs')
 c444=next(x for x in companion_by_number[444]['area_scopes'] if x['name']=='Chile Central')
 c446=next(x for x in companion_by_number[446]['area_scopes'] if x['name']=='Paraguay')
 if (c444['owned_member_location_count'],c444['full_area_location_count'])!=(177,252): raise ValueError('companion #444 Chile Central scope changed')
 if (c446['owned_member_location_count'],c446['full_area_location_count'])!=(195,243): raise ValueError('companion #446 Paraguay scope changed')
 if (int(area_rows['framework:area:chile-central:4657b9c2c6bd']['owned_member_count']),int(area_rows['framework:area:chile-central:4657b9c2c6bd']['full_area_member_count']))!=(75,252): raise ValueError('issue #445 Chile Central partial scope changed')
 if (int(area_rows['framework:area:paraguay:b8f36a1a90ee']['owned_member_count']),int(area_rows['framework:area:paraguay:b8f36a1a90ee']['full_area_member_count']))!=(48,243): raise ValueError('issue #445 Paraguay partial scope changed')
 if 75+c444['owned_member_location_count']!=252 or 48+c446['owned_member_location_count']!=243: raise ValueError('companion partial areas do not partition full totals')
 if len(parents)!=39: raise ValueError(f'expected 39 scoped parent rows; found {len(parents)}')
 for p in parents:
  area_id=next((a_id for a_id in AREAS if any(x['id']==p['province_id'] and x.get('parent_id')==a_id for x in hierarchy)),None)
  if not area_id: raise ValueError('could not resolve parent area for '+p['province_id'])
  area_name,code,_=AREAS[area_id]; names=[x[1] for x in source4[code]]
  parent_name=p['province_name']
  stripped=re.sub(r'^(Provincia|Departamento) de\s+','',parent_name,flags=re.I)
  exact=[n for n in names if norm(n)==norm(stripped)]
  rows.append({'record_type':'parent','area_id':area_id,'area_name':area_name,'area_owned_member_count':'','full_area_member_count':'','scope_companion_issues':'','parent_id':p['province_id'],
   'atlas_province_child_count':p['full_scope_location_count'],'wgsrpd_code':code,'wgsrpd_l2':'85,00',
   'wgsrpd_l4_count':len(source4[code]),'wgsrpd_l4_names':'; '.join(names),
   'atlas_to_l4_name_match':'; '.join(exact) if exact else 'no_exact_name_match',
   'scope_note':'Atlas parent name vs historical botanical L4 label; match/nonmatch cannot establish administrative identity, parentage or boundaries.'})
 cols=['record_type','area_id','area_name','area_owned_member_count','full_area_member_count','scope_companion_issues','parent_id','atlas_province_child_count','wgsrpd_code','wgsrpd_l2','wgsrpd_l4_count','wgsrpd_l4_names','atlas_to_l4_name_match','scope_note']
 with open(a.output,'w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n'); w.writeheader(); w.writerows(rows)
 print(json.dumps({'areas':5,'parents':len(parents),'rows':len(rows),'wgsrpd_level3_l2':'85,00','level3_sha256':L3_SHA,'level4_sha256':L4_SHA,'hierarchy_sha256':HIERARCHY_SHA,'companion_scope_ids':sorted(companion_by_number),'companion_overlap_counts':{str(n):0 for n in companion_by_number},'output':a.output},indent=2))
if __name__=='__main__': main()

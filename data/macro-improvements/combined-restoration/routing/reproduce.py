#!/usr/bin/env python3
"""Validate/reproduce pinned source routing evidence. No network, geometry scan or live writes."""
import argparse,copy,gzip,hashlib,json,subprocess
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(data):return json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def prune(value):
 if isinstance(value,dict):return {k:prune(v) for k,v in value.items() if k not in ['coordinates','geometry','unchanged_location_ids','after_feature','before_feature']}
 if isinstance(value,list):return [prune(v) for v in value]
 return value
def read_pin(pin):
 path=pin['path'];assert not Path(path).is_absolute() and '..' not in Path(path).parts
 expected=pin['file_sha256'];file=ROOT/path;data=file.read_bytes() if file.exists() else b''
 if sha(data)!=expected:
  # Old published macro/hierarchy files may later change. Their immutable git blobs remain valid.
  data=subprocess.check_output(['git','show',pin['git_commit']+':'+path],cwd=ROOT)
 assert sha(data)==expected,'Pinned source file changed: '+path
 decoded=gzip.decompress(data) if path.endswith('.gz') else data
 if 'decoded_bytes_sha256' in pin:assert sha(decoded)==pin['decoded_bytes_sha256'],'Decoded source bytes changed: '+path
 return json.loads(decoded)
def validate(data):
 assert data['publication_status']['candidate_published'] is False
 assert data['publication_status']['currently_published_geographic_release_version']==3
 assert data['publication_status']['currently_published_site_version']==19
 sources={key:read_pin(pin) for key,pin in data['input_files'].items()}
 h={u['id']:u for u in sources['hierarchy']}
 def chain(parent):
  ids=[]
  while parent:assert parent in h;ids.append(parent);parent=h[parent].get('parent_id')
  return ids
 originals=sources['base']['named_land_routing'];assert len(originals)==135
 names=[row['name'] for row in originals];assert len(names)==len(set(names))
 route={row['name']:row for row in data['original_routes']};assert len(route)==135
 counts=Counter()
 rebuilt=copy.deepcopy(data)
 for row in rebuilt['original_routes']:
  original=next(x for x in originals if x['name']==row['name']);matches=[]
  for issue,key in [('41','entries'),('42','named_land_ledger'),('43','entries')]:
   matches.extend((int(issue),entry) for entry in sources[issue][key] if entry['name']==row['name'])
  assert len(matches)==1,'Missing/duplicate supplemental route '+row['name']
  issue,entry=matches[0];counts[issue]+=1
  assert row['supplemental_issue']==issue and entry['region_id']==original['region_id']
  assert row['original_routing']==original
  assert row['region_subcontinent_continent_chain']==chain(original['region_id'])
  assert row['supplemental_entry_canonical_sha256']==sha(canonical(entry))
  assert row['supplemental_entry']==prune(entry)
  assert row['completion']['whole_named_family_source_coverage_approved'] is False
  assert row['completion']['regional_interiors_approved'] is False
  row.update(original_routing=original,supplemental_entry=prune(entry),supplemental_entry_canonical_sha256=sha(canonical(entry)))
 assert counts==Counter({41:25,42:64,43:46})
 candidates=data['correction_candidates'];refs={c['ref']:c for c in candidates};assert len(refs)==44
 assert Counter(c['status']=='staged-addition' for c in candidates)[True]==34
 assert sum(c['status'].startswith('staged-retained-id') for c in candidates)==8
 holds=[c for c in candidates if c['status']=='held-no-source-land-cell']
 assert {c['name'] for c in holds}=={'Kingman Reef','Gardner Pinnacles'}
 additions=[c['location_id'] for c in candidates if c['status']=='staged-addition'];assert len(additions)==len(set(additions))==34
 for candidate in candidates:
  parents=candidate['parent_chain'];assert len(parents)==5 and parents[2:]==chain(parents[2])
  assert candidate['live_applied'] is False and candidate['historical_claims_transferred'] is False
  assert candidate['regional_interior_approved'] is False
  for name in candidate['linked_original_routes']:assert candidate['ref'] in route[name]['correction_refs']
  source=sources[str(candidate['issue'])]
  if candidate['issue']==501:
   original=next(c for c in source['candidates'] if c['id']==candidate['location_id'])
   assert candidate['source_and_operation_evidence']==prune(original)
  elif candidate['status']=='staged-addition':
   original=next(c for c in source['added_features'] if c['properties']['id']==candidate['location_id'])
   assert candidate['source_and_operation_evidence']['feature']==prune(original)
  else:
   original=next(c for c in source['operations'] if c['id']==candidate['location_id'])
   assert candidate['source_and_operation_evidence']['operation']==prune(original)
  for name in candidate['linked_original_routes']:assert name in route
 for row in route.values():
  for ref in row['correction_refs']:
   if ref!='501:PCN+00?:unapplied-present-day-label-proposal':assert ref in refs and row['name'] in refs[ref]['linked_original_routes']
 label=data['retained_reference_name_proposals'];assert len(label)==1
 original_label=sources['501']['retained_identity_crosswalks'][0]
 assert label[0]['location_id']==original_label['id']=='PCN+00?'
 assert label[0]['source_raw_sha256']==original_label['source_raw_sha256']
 assert label[0]['geometry_changed'] is False and original_label['applied'] is False
 assert label[0]['proposed_reference_name']=='Henderson Island'
 amendment=sources['506']['macro_amendment'];include=amendment['include'];exclude=amendment['reciprocal_exclusion']
 assert include['named_land']==exclude['named_land'] and include['region_id']!=exclude['region_id']
 assert h[exclude['region_id']]['name']=='Japan'
 assert include['region_id']=='framework:region:northwestern-pacific:2357073b3888'
 assert chain(include['region_id'])==[include['region_id'],include['subcontinent_id'],include['continent_id']]
 marcus=next(c for c in candidates if c['issue']==506)
 assert marcus['source_and_operation_evidence']['macro_amendment']==amendment
 assert marcus['parent_chain'][2:]==chain(include['region_id'])
 assert len(data['additional_named_route_candidates'])==1
 context={c['parent_chain'][2] for c in candidates}|{exclude['region_id']};assert len(context)==14
 changed_regions={c['parent_chain'][2] for c in candidates if c['status']!='held-no-source-land-cell'};assert len(changed_regions)==13
 for pin in data['source_inventory_pins']:
  expected=prune(read_pin(pin));assert pin['records']==expected
 for issue,pool in rebuilt['supplemental_source_pools'].items():
  for key in pool:assert pool[key]==prune(sources[issue][key]);pool[key]=prune(sources[issue][key])
 summary=data['summary'];assert summary['existing_location_footprint_corrections']==6
 assert summary['existing_location_present_day_name_changes_if_label_applied']==3
 assert summary['candidate_new_geographic_groups']==8
 return rebuilt,{'pass':True,'original_named_routes':135,'supplemental_routes':dict(counts),'candidate_new_locations':34,'existing_footprint_corrections':6,'present_day_location_name_changes':3,'proposed_province_name_changes':2,'representation_holds':2,'changed_regions':13,'neighbor_reciprocal_exclusions':1,'source_inventory_pins':len(data['source_inventory_pins']),'candidate_published':False,'regional_interiors_approved':False}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--crosswalk',type=Path,default=HERE/'routing-status-crosswalk.json.gz');ap.add_argument('--output',type=Path);args=ap.parse_args();raw=args.crosswalk.read_bytes();decoded=gzip.decompress(raw);receipt=json.loads((HERE/'validation.json').read_text())
 assert sha(raw)==receipt['crosswalk_archive_sha256'] and sha(decoded)==receipt['crosswalk_decoded_sha256'],'Crosswalk archive hash mismatch'
 data=json.loads(decoded);rebuilt,result=validate(data);output=(json.dumps(rebuilt,ensure_ascii=False,indent=2)+'\n').encode();assert output==decoded,'Reproduction differs from recorded pinned source evidence'
 if args.output:
  assert args.output.resolve()!=args.crosswalk.resolve(),'Use a separate reproduction output'
  args.output.write_bytes(output);result['reproduced_decoded_sha256']=sha(output)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()

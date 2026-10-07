#!/usr/bin/env python3
"""Exact stock tuple verifier plus every source interval's endpoint lookup proof."""
import argparse,bisect,hashlib,importlib.util,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[3]
def load_module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def verify(source,runtime,map_path,receipt):
 stock=load_module('exact_runtime_validator',ROOT/'scripts/validate-ownership-runtime.py')
 result=stock.validate(source,runtime)
 manifest=stock.read(runtime/'index.json');selector=json.loads(map_path.read_text())
 if selector['runtime_index_sha256']!=stock.sha(runtime/'index.json'):raise ValueError('Production selector map vintage differs')
 expected_years=[y for y in range(-3000,2027) if y!=0]
 if [r['year'] for r in selector['all_valid_years']]!=expected_years:raise ValueError('Incomplete production year lookup map')
 mapped={r['year']:r for r in selector['all_valid_years']};index=stock.read(source/'index.json')
 intervals=checks=active_checks=0;proof=hashlib.sha256();starts=[b['valid_from'] for b in manifest['buckets']]
 for part in index['parts']:
  for identifier,rows in stock.read(source/part['path']):
   for row in rows:
    a,b,owner,status,ei=row;intervals+=1
    # Every original interval is checked, not a representative or unique-date sample.
    for year in (a-1,a,a+1,b-1,b,b+1):
     if year==0 or year not in mapped:continue
     choice=mapped[year];expected=bisect.bisect_right(starts,year)-1
     if expected<0 or year>=manifest['buckets'][expected]['valid_to']:expected=None
     if choice['bucket_index']!=expected:raise ValueError('Production binary-search selection differs')
     if expected is not None and choice['path']!=manifest['buckets'][expected]['path']:raise ValueError('Production bucket path differs')
     if a<=year<b:
      if expected is None:raise ValueError('Original interval active outside runtime coverage')
      bucket=manifest['buckets'][expected]
      if not(a<bucket['valid_to'] and b>bucket['valid_from']):raise ValueError('Active interval excluded from selected bucket')
      # validate() above authenticates this exact complete source tuple/evidence in
      # EVERY intersecting bucket. Thus selection includes the unchanged row.
      active_checks+=1
     proof.update(json.dumps([identifier,row,year,expected],separators=(',',':')).encode()+b'\n');checks+=1
 if intervals!=index['intervals']:raise ValueError('Complete interval roster missing')
 result.update({'every_original_interval_endpoint_and_adjacent_date_checked':True,
  'endpoint_selector_checks':checks,'active_endpoint_checks':active_checks,
  'endpoint_complete_roster_sha256':proof.hexdigest(),
  'selector_map_sha256':stock.sha(map_path),'stock_validator_sha256':stock.sha(ROOT/'scripts/validate-ownership-runtime.py'),
  'interval_dates_owner_status_and_full_evidence_preserved':True})
 receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='buckets'}),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--selector-map',type=pathlib.Path,required=True);p.add_argument('--receipt',type=pathlib.Path,required=True);a=p.parse_args();verify(a.source,a.runtime,a.selector_map,a.receipt)

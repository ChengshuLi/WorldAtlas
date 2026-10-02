#!/usr/bin/env python3
"""Restore exact baseline/source/macro stages from final geography and Git receipts."""
import argparse, copy, gzip, hashlib, importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('_repair_helpers',ROOT/'scripts/apply-source-territory-repairs.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def encoded(value,newline=False):return (json.dumps(value,ensure_ascii=False,separators=(',',':'))+('\n' if newline else '')).encode()
def hashbytes(value):return hashlib.sha256(value).hexdigest()


def reverse_macro(features,units,macro):
 if digest([units,features])!=macro['after_sha256']:raise ValueError('Final macro geography content differs from immutable receipt')
 result=copy.deepcopy(features);by_id={f['properties']['id']:f for f in result}
 if len(by_id)!=len(result) or set(by_id)!=set(macro['unchanged_geometry_ids']):raise ValueError('Macro identity coverage differs')
 if digest([[i,by_id[i]['geometry']] for i in sorted(by_id)])!=macro['unchanged_geometry_sha256']:raise ValueError('Macro unchanged geometry proof differs')
 for row in macro['changed_location_properties']:
  f=by_id.get(row['location_id'])
  if f is None or f['properties']!=row['after_properties'] or digest(f['geometry'])!=row['geometry_sha256']:raise ValueError('Changed macro location evidence differs')
  f['properties']=copy.deepcopy(row['before_properties'])
 prior={u['id']:copy.deepcopy(u) for u in macro['before_units']}
 if digest([prior,result])!=macro['before_sha256']:raise ValueError('Reversed macro content differs from original source stage')
 helper.chains(result,prior)
 return result,prior


def snapshot(directory,features,units,index,collections,newline=False,pins=None):
 by_id={f['properties']['id']:f for f in features};nl=lambda name:newline.get(name,False) if isinstance(newline,dict) else newline
 raws={'world-index.json':encoded(index,nl('world-index.json')),'hierarchy.json':encoded(list(units.values()),nl('hierarchy.json'))}
 for part in collections:
  raws[part['path']]=encoded({**part['collection_fields'],'features':[by_id[i] for i in part['ids']]},nl(part['path']))
 if pins:
  for path,pin in pins.items():
   if path not in raws or hashbytes(raws[path])!=pin:raise ValueError('Reconstructed raw snapshot differs: '+path)
 for name,raw in raws.items():
  path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
 return {name:hashbytes(raw) for name,raw in raws.items()}


def restore(final_index,evidence,manifest_path,output,root=ROOT):
 if output.exists():raise ValueError('Output must be fresh')
 if output.resolve()==root/'data' or root/'data' in output.resolve().parents:raise ValueError('Never restore over live data')
 manifest=helper.read(manifest_path)
 for key in ['original_layout','macro_receipt','macro_decisions']:
  path=root/manifest[key+'_path']
  if helper.sha(path)!=manifest[key+'_sha256']:raise ValueError('Pinned restoration input differs: '+key)
 if helper.sha(evidence/'index.json')!=manifest['source_evidence_index_sha256']:raise ValueError('Source evidence manifest differs')
 archive_index=helper.read(evidence/'index.json')
 for entry in archive_index['files'].values():
  path=(evidence/entry['archive_path']).resolve()
  if not path.is_relative_to(evidence.resolve()) or helper.sha(path)!=entry['sha256']:raise ValueError('Archived source evidence differs')
 source_raw=gzip.decompress((evidence/'migration-receipt.json.gz').read_bytes());source=json.loads(source_raw)
 macro=helper.read(root/manifest['macro_receipt_path']);decisions=helper.read(root/manifest['macro_decisions_path'])
 if hashbytes(source_raw)!=macro['source_repair_receipt_sha256']:raise ValueError('Source/macro receipt linkage differs')
 if helper.sha(root/manifest['macro_decisions_path'])!=macro['decisions_file_sha256']:raise ValueError('Macro decision linkage differs')
 index=helper.read(final_index);collections=[helper.read(final_index.parent/p) for p in index['parts']];features=[f for c in collections for f in c['features']]
 units={u['id']:u for u in helper.read(final_index.parent/'hierarchy.json')}
 if helper.footprint_hash(features)!=source['after_footprints_sha256']:raise ValueError('Final repaired footprint differs')
 helper.chains(features,units)
 prior_features,prior_units=reverse_macro(features,units,macro)
 # Preserve original ordered part layout. Macro never removed/reordered a source-stage ID.
 current_parts=[{'path':path,'ids':[f['properties']['id'] for f in c['features']],'collection_fields':{k:v for k,v in c.items() if k!='features'}} for path,c in zip(index['parts'],collections)]
 source_after=snapshot(output/'source-stage/after',prior_features,prior_units,index,current_parts,pins=macro['source_stage_after_input_sha256'])
 archive=helper.read(evidence/'archive.json.gz');by_id={f['properties']['id']:copy.deepcopy(f) for f in prior_features}
 for original in archive['locations']:by_id[original['id']]=copy.deepcopy(original['feature'])
 layout=helper.read(root/manifest['original_layout_path']);original_ids=[i for part in layout['parts'] for i in part['ids']]
 if len(original_ids)!=len(set(original_ids)) or set(original_ids)!=set(by_id):raise ValueError('Original location ordering does not account for every identity')
 original_features=[by_id[i] for i in original_ids];original_units={u['id']:u for u in json.loads(gzip.decompress((evidence/'before-hierarchy.json.gz').read_bytes()))}
 if helper.footprint_hash(original_features)!=source['before_footprints_sha256']:raise ValueError('Original footprint reconstruction differs')
 helper.chains(original_features,original_units)
 for part in layout['parts']:
  value={**part['collection_fields'],'features':[by_id[i] for i in part['ids']]}
  if digest(value)!=decisions['input_content_sha256']['data/'+part['path']]:raise ValueError('Original part content guard differs')
 if digest(list(original_units.values()))!=decisions['input_content_sha256']['data/hierarchy.json']:raise ValueError('Original hierarchy content guard differs')
 baseline_pins={**source['input_parts'],'hierarchy.json':source['before_hierarchy_sha256'],'world-index.json':decisions['input_sha256']['data/world-index.json']}
 baseline=snapshot(output/'baseline',original_features,original_units,layout['world_index'],layout['parts'],newline={part['path']:True for part in layout['parts']},pins=baseline_pins)
 snapshot(output/'source-stage/before',original_features,original_units,layout['world_index'],layout['parts'])
 snapshot(output/'macro-stage/before',prior_features,prior_units,index,current_parts,newline=True)
 snapshot(output/'macro-stage/after',features,units,index,current_parts,newline=True)
 # Exact immutable archives accompany the reconstructed stage; claims never move.
 for name,entry in archive_index['files'].items():
  raw=(evidence/entry['archive_path']).read_bytes()
  if entry.get('uncompressed_sha256'):raw=gzip.decompress(raw)
  if entry.get('uncompressed_sha256') and hashbytes(raw)!=entry['uncompressed_sha256']:raise ValueError('Archive decompression differs')
  destination=output/'source-stage'/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
 result={'version':1,'baseline_locations':len(original_features),'source_and_final_locations':len(features),'macro_properties_restored':len(macro['changed_location_properties']),'macro_chains_restored':len(macro['location_chain_crosswalk']),'source_original_features_restored':len(archive['locations']),'before_footprints_sha256':source['before_footprints_sha256'],'after_footprints_sha256':source['after_footprints_sha256'],'raw_baseline_hashes':baseline,'raw_source_after_hashes':source_after,'archives_preserved':True,'historical_claims_transferred':0,'all_chains_complete':True,'manifest_sha256':helper.sha(manifest_path),'macro_receipt_sha256':helper.sha(root/manifest['macro_receipt_path'])}
 helper.write(output/'restoration-proof.json',result);return result


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--final',type=pathlib.Path,default=ROOT/'data/world-index.json');p.add_argument('--evidence',type=pathlib.Path,default=ROOT/'data/geographic-repair-evidence');p.add_argument('--manifest',type=pathlib.Path,default=ROOT/'data/geographic-restoration-manifest.json');p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();r=restore(a.final,a.evidence,a.manifest,a.output);print(json.dumps({k:v for k,v in r.items() if not k.startswith('raw_')}))
if __name__=='__main__':main()

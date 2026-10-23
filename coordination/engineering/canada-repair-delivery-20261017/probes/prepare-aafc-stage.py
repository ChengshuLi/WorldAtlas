"""Prepare whole AAFC feature measurements, without asserting provider adoption.
Run from a repository with all immutable inputs retained:
  python PATH/prepare-aafc-stage.py --repo REPOSITORY --output NEW_DIRECTORY
The two phases keep every source OBJECTID unique while covering repeated
regional portions. The complete 218-feature product remains the source operand.
"""
import argparse,collections,gzip,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--output',required=True);a=p.parse_args();W=pathlib.Path(a.repo).resolve();O=pathlib.Path(a.output);O.mkdir(parents=True,exist_ok=False)
H='c4ffca9ba743f68c877fd8542698b28804cf07cf';P='coordination/engineering/canada-repair-delivery-20261017';source_path='data/regional-review/regional-review-a9f03b364bdefa4a/sources/aafc-baseline-arcgis-layer0.geojson'
def raw(path,commit=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',commit+':'+path])
def sha(b):return hashlib.sha256(b).hexdigest()
def write(name,value):
 b=(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode()
 with (O/name).open('xb') as f:f.write(b)
 return {'path':name,'bytes':len(b),'sha256':sha(b)}
screen=json.loads(raw(P+'/source-review/source-target-screening.json','30eec83d99e54cd41fd12278b9260d66ed86c83e'));b=raw(source_path);assert len(b)==12241679 and sha(b)=='30e5e2fc80df6624ecc10d2a6714cf88339fad88e5a8577e41f9fb26e2c4a992';product=json.loads(b);assert len(product['features'])==218;assert len({f['properties']['OBJECTID'] for f in product['features']})==218
byeco=collections.defaultdict(list)
for i,f in enumerate(product['features']):byeco[f['properties']['ECOREGION_ID']].append((i,f))
selection=json.loads(raw('data/ownership-selection.json'));pin=selection['selected_geography'];b=raw(pin['path']);assert sha(b)==pin['sha256'] and len(b)==pin['bytes'];bank=json.loads(b);features={}
for commit,path in sorted({(o['target_pin']['commit'],o['target_pin']['path']) for o in screen['owners']}):
 pin=next(x for x in bank['unchanged_files']+bank['overrides'] if x['commit']==commit and x['path']==path);b=raw(path,commit);assert len(b)==pin['bytes'] and sha(b)==pin['sha256']
 if pin.get('encoding')=='gzip':b=gzip.decompress(b);assert len(b)==pin['decoded_bytes'] and sha(b)==pin['decoded_sha256']
 for f in json.loads(b)['features']:assert f['id'] not in features;features[f['id']]=f
phases=[[],[]];bindings=[[],[]];counts=collections.Counter()
for owner in screen['owners']:
 selected=features[owner['id']];assert selected['properties']==owner['target_properties'];meta=selected['properties']['metadata']
 if not meta.get('source_id','').startswith('aafc:'):continue
 eco=meta['ecoregion_id'];phase=counts[eco];counts[eco]+=1;assert phase<2
 for ordinal,feature in byeco[eco]:
  source_id='aafc:ecoregions:baseline-layer0:'+str(feature['properties']['OBJECTID']);phases[phase].append({'target':source_id,'family':'aafc','consumed':feature,'selected':selected});bindings[phase].append({'source_id':source_id,'feature_ordinal':ordinal,'OBJECTID':feature['properties']['OBJECTID'],'ECOREGION_ID':eco,'target_id':owner['id'],'pixelIndex':owner['index']})
outputs=[]
for i,rows in enumerate(phases,1):
 assert len({r['target'] for r in rows})==len(rows);outputs.append(write(f'aafc-{i:03d}-original-stage-inputs.json',rows));outputs.append(write(f'aafc-{i:03d}-measurement-bindings.json',bindings[i-1]))
assert sum(len({r['target_id'] for r in v}) for v in bindings)==72
write('aafc-stage-preparation.json',{'kind':'whole-AAFC-physical-measurement-inputs-only','source':{'commit':H,'path':source_path,'bytes':12241679,'sha256':'30e5e2fc80df6624ecc10d2a6714cf88339fad88e5a8577e41f9fb26e2c4a992','features':218},'outputs':outputs,'limits':['Whole unchanged source features and selected target geometries are retained. This measurement stage does not adopt a source-to-owner mapping or relax remainder, territorial, native or physical vetoes.','Repeated ecoregions are measured in two phases to avoid duplicate whole-source identities. All original physical repair candidates remain accounted separately.']})
print(json.dumps(outputs))

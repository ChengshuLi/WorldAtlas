"""Independently verify full-negative identity, every proof row and exact operative geometry.
Usage: python verify-native-preparation.py READ_ONLY_REPO INPUT_COMMIT FRESH_OUTPUT
"""
import collections,gzip,hashlib,json,math,os,pathlib,subprocess,sys,time
import numpy as np,shapely
from shapely.geometry import shape,box
W=pathlib.Path(sys.argv[1]).absolute();C=sys.argv[2];O=pathlib.Path(sys.argv[3]).absolute();H='3b3e9e675cfb37999d5665438f9fbf25bbd4238b';P='coordination/engineering/estonia-native-repair-20261017';started=time.monotonic()
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
assert len(C)==40 and all(c in '0123456789abcdef' for c in C)
inputs={};env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'};sha=lambda b:hashlib.sha256(b).hexdigest();encode=lambda x:(json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def raw(p,c=C):
 assert p and not p.startswith('/') and all(x not in ['', '.', '..'] for x in p.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',c,'--',p],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==p
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
 d={'path':p,'commit':c,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
 if p.endswith('.gz'):q=gzip.decompress(b);d.update(decoded_bytes=len(q),decoded_sha256=sha(q))
 inputs[(c,p)]=d;return b
def js(p,c=C):
 b=raw(p,c);return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
def pin(p,c=C):raw(p,c);return inputs[(c,p)]

config=js(P+'/native-config-001/source-config.json');proof=js(P+'/native-config-001/negative-equivalence.json');prep=js(P+'/native-config-001/preparation.json');evidence=js(P+'/native-inputs-001/source-evidence.json');a=js(P+'/source-stage/source-scope-assessment.json');context=js(P+'/context-001/complete-context.json');stages=js(P+'/source-stage/original-stage-inputs.json')
for name,expected in prep['outputs'].items():b=raw(P+'/native-config-001/'+name);assert len(b)==expected['bytes'] and sha(b)==expected['sha256']
assert evidence['targets']==config['source_evidence']['targets'];targets=evidence['targets'];assert len(targets)==len(stages)==len(proof['targets'])==len({t['id'] for t in targets})==90
registry=js('data/sources.json',H);whole=[];negative=[]
for path,idkey,hashkey,derived,contactids in [('data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz','ADM0_A3','ne_10m_admin_0_countries',P+'/source-stage/foreign-country-features.geojson',{r['code'] for r in a['country_reference_hits'] if r['code']!='EST'}),('data/regional-review/regional-review-0c300e5f6ecdc793/sources/natural-earth-ca96624/ne_10m_admin_1_states_provinces.geojson.gz','adm1_code','ne_10m_admin_1_states_provinces',P+'/context-001/foreign-adm1-features.geojson',{r['id'] for r in context['foreign_natural_earth_hits']})]:
 b=raw(path,H);q=gzip.decompress(b);assert sha(q)==registry['hashes'][hashkey];full=json.loads(q)['features'];byid={f['properties'][idkey]:f for f in full};assert len(full)==len(byid);subset=js(derived)['features'];assert len(subset)==len({f['properties'][idkey] for f in subset}) and {f['properties'][idkey] for f in subset}==contactids
 for f in subset:assert f==byid[f['properties'][idkey]]
 negative.extend(subset);whole.append({'source':inputs[(H,path)],'complete_features':len(full),'retained_full_features':len(subset)})
assert js(P+'/source-stage/foreign-original-source-features.geojson')['features']==[] and a['foreign_original_source_hits']==[]
assert proof['original_operands']==len(negative)*len(targets) and len(proof['whole_negative_records'])==len(negative)
for n,f in zip(proof['whole_negative_records'],negative):assert n['geometry_sha256']==sha(encode(f['geometry']))
latpin=next(x for x in a['inputs'] if 'native-row-latitudes' in x['path']);lb=raw(latpin['path'],latpin['commit']);assert len(lb)==latpin['bytes'] and sha(lb)==latpin['sha256'];lb=gzip.decompress(lb) if latpin['path'].endswith('.gz') else lb;assert len(lb)==latpin.get('decoded_bytes',latpin['bytes']) and sha(lb)==latpin.get('decoded_sha256',latpin['sha256']);lat=np.frombuffer(lb,dtype='<f8')
keys=set();byowner=collections.defaultdict(list)
for block in range(18,20):
 for y,start,end,owners,sources,kind in js(P+f'/frozen-queue/block-{block:03}.json.gz'):
  for x in range(start,end):
   k=(x,y,owners[0]);assert k not in keys;keys.add(k);byowner[owners[0]].append(k)
checks={t['source_atoms'][0]:t for t in a['target_checks']};retained=0;omitted=0;rows=[]
for target,stage,row in zip(targets,stages,proof['targets']):
 ident=stage['target'];owner=checks[ident]['pixelIndex'];assert target['id']==row['source_id']==ident and target['target_id']==row['target_id']==stage['selected']['id'] and target['pixelIndex']==row['pixelIndex']==owner and target['base_geometry']==stage['selected']['geometry']
 actual={(x,r['y'],owner) for r in target['coverage_rows'] for start,end,kind in r['runs'] for x in range(start,end)};assert actual==set(byowner[owner]);coords=[((x+.5)/262166*360-180,float(lat[y])) for x,y,o in actual];sg=shape(stage['consumed']['geometry']);bg=shape(stage['selected']['geometry']);bounds=[min(sg.bounds[0],bg.bounds[0],min(x for x,y in coords)),min(sg.bounds[1],bg.bounds[1],min(y for x,y in coords)),max(sg.bounds[2],bg.bounds[2],max(x for x,y in coords)),max(sg.bounds[3],bg.bounds[3],max(y for x,y in coords))];assert bounds==row['closed_support_envelope'];envelope=box(*bounds);assert envelope.covers(sg) and envelope.covers(bg) and shapely.covers(envelope,shapely.points(coords)).all()
 keep=[];omit=[]
 for ordinal,f in enumerate(negative):
  (omit if shape(f['geometry']).disjoint(envelope) else keep).append(ordinal)
 assert keep==row['retained_whole_negative_ordinals'] and omit==row['geometry_disjoint_whole_negative_ordinals'] and target['territorial_exclusions']==[negative[i]['geometry'] for i in keep];retained+=len(keep);omitted+=len(omit);rows.append({'source_id':ident,'owner':owner,'original_cells':len(actual),'retained_negative_ordinals':keep,'disjoint_negative_ordinals':omit})
assert retained==proof['retained_operands'] and omitted==proof['disjoint_operands'] and retained+omitted==proof['original_operands']
result={'version':1,'complete_original_native_cells':len(keys),'complete_targets_verified':len(rows),'complete_foreign_products':whole,'complete_negative_records':len(negative),'original_operands':retained+omitted,'retained_operands':retained,'disjoint_operands':omitted,'stock_source_targets_exactly_equal_prepared_targets':True,'whole_negative_features_exactly_equal_originals':True,'all_closed_envelopes_and_every_mask_centre_independently_verified':True,'target_checks':rows,'inputs':list(inputs.values()),'elapsed_seconds':time.monotonic()-started}
b=encode(result);assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'verification.json').open('xb') as f:f.write(b)
with (O/'preparation.json').open('xb') as f:f.write(encode({'complete':True,'bytes':len(b),'sha256':sha(b)}))
print(json.dumps({k:result[k] for k in ['complete_original_native_cells','complete_targets_verified','complete_negative_records','original_operands','retained_operands','disjoint_operands','elapsed_seconds']}))

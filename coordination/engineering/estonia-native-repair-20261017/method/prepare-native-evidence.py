"""Prepare full original evidence with whole-negative envelope disjointness proof.
Usage: python prepare-native-evidence.py READ_ONLY_REPO INPUT_COMMIT FRESH_OUTPUT
All negative records remain pinned whole; geometry-disjoint envelopes conservatively
contain complete source, selected geometry and every requested mask centre.
"""
import collections,gzip,hashlib,io,json,math,os,pathlib,subprocess,sys,time
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
s=js(P+'/source-stage/original-stage-inputs.json');a=js(P+'/source-stage/source-scope-assessment.json');checks={t['source_atoms'][0]:t for t in a['target_checks']};assert len(s)==len(checks)==90 and all(len(t['source_atoms'])==1 for t in a['target_checks'])
catp='coordination/engineering/original-geography-source-corpus-20261006/catalogue.json';cat=js(catp,H);record=next(c for c in cat['products'] if c['key']=='gb:EST:ADM2');pieces=[]
for part in record['parts']:
 b=raw(part['path'],H);q=gzip.decompress(b);assert len(b)==part['bytes'] and sha(b)==part['sha256'] and len(q)==part['uncompressed_bytes'] and sha(q)==part['uncompressed_sha256'];pieces.append(q)
b=b''.join(pieces);assert len(b)==record['original_bytes'] and sha(b)==record['original_sha256'];features=json.loads(b)['features'];assert len(features)==record['feature_count']==214;originals={'gb:EST:ADM2:'+f['properties']['shapeID']:f for f in features};assert len(originals)==len(features)
negative_paths=[P+'/source-stage/foreign-country-features.geojson',P+'/context-001/foreign-adm1-features.geojson',P+'/source-stage/foreign-original-source-features.geojson'];negative=[]
for p in negative_paths:
 for ordinal,f in enumerate(js(p)['features']):negative.append({'input':inputs[(C,p)],'feature_ordinal':ordinal,'geometry_sha256':sha(encode(f['geometry'])),'feature':f})
ng=[shape(n['feature']['geometry']) for n in negative];assert all(g.is_valid and not g.is_empty for g in ng)
latpin=next(x for x in a['inputs'] if 'native-row-latitudes' in x['path']);lb=raw(latpin['path'],latpin['commit']);assert len(lb)==latpin['bytes'] and sha(lb)==latpin['sha256'];lat=np.frombuffer(lb,dtype='<f8');ys=collections.defaultdict(lambda:collections.defaultdict(list));keys=set()
for block in range(18,20):
 for y,start,end,owners,sources,kind in js(P+f'/frozen-queue/block-{block:03}.json.gz'):
  assert len(owners)==1 and kind in ['land','inland-water'];owner=owners[0];ys[owner][y].append([start,end,{'land':'mapped_land_support','inland-water':'mapped_inland_water_support'}[kind]])
  for x in range(start,end):assert (x,y,owner) not in keys;keys.add((x,y,owner))
assert len(keys)==a['original_cells']==34461
coverage={}
for owner,rs in ys.items():
 rows=[]
 for y,runs in sorted(rs.items()):
  merged=[]
  for r in sorted(runs):
   if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
   else:merged.append(r.copy())
  rows.append({'y':y,'runs':merged})
 coverage[owner]=rows
physical=pin(P+'/physical-001/whole-target-support.json');targets=[];proof=[];retained=0
for stage in s:
 ident=stage['target'];check=checks[ident];owner=check['pixelIndex'];assert stage['consumed']==originals[ident];base=stage['selected']['geometry'];sg=shape(stage['consumed']['geometry']);bg=shape(base);assert sg.is_valid and bg.is_valid
 coords=[((x+.5)/262166*360-180,float(lat[y])) for x,y,o in keys if o==owner];assert coords and all(math.isfinite(x) and math.isfinite(y) for x,y in coords)
 bounds=[min(sg.bounds[0],bg.bounds[0],min(x for x,y in coords)),min(sg.bounds[1],bg.bounds[1],min(y for x,y in coords)),max(sg.bounds[2],bg.bounds[2],max(x for x,y in coords)),max(sg.bounds[3],bg.bounds[3],max(y for x,y in coords))];envbox=box(*bounds)
 assert bounds[2]-bounds[0]<180 and envbox.covers(sg) and envbox.covers(bg) and shapely.covers(envbox,shapely.points(coords)).all()
 keep=[];omit=[]
 for ordinal,g in enumerate(ng):
  (omit if g.disjoint(envbox) else keep).append(ordinal)
 assert sorted(keep+omit)==list(range(len(negative))) and not set(keep)&set(omit);retained+=len(keep)
 targets.append({'id':ident,'target_id':stage['selected']['id'],'pixelIndex':owner,'base_geometry':base,'source_family':'gb:EST:ADM2','source_receipt_sha256':physical['sha256'],'coverage_classes':sorted({r[2] for row in coverage[owner] for r in row['runs']}),'coverage_rows':coverage[owner],'territorial_exclusions':[negative[i]['feature']['geometry'] for i in keep]})
 proof.append({'source_id':ident,'target_id':stage['selected']['id'],'pixelIndex':owner,'closed_support_envelope':bounds,'complete_source_covered':True,'complete_selected_covered':True,'all_requested_centres_covered':True,'requested_cells':len(coords),'retained_whole_negative_ordinals':keep,'geometry_disjoint_whole_negative_ordinals':omit})
assert len({t['pixelIndex'] for t in targets})==len(targets)==90
projection='data/macro-foundation/world-review-projection.json';proj=js(projection,H)
evidence={'version':1,'kind':'source-target-native-evidence-v1','catalogue':pin(catp,H),'families':[{'source_id':'gb:EST:ADM2','parts':[pin(p['path'],H) for p in record['parts']]}],'physical_evidence':physical,'physical_input':pin(P+'/source-stage/original-stage-inputs.json'),'physical_reproduction':pin('scripts/qualify-source-cohort.py',H),'source_membership':{'index':pin('data/world-index.json',H),'lineage':pin('data/semantic-report.json',H),'parts':[pin('data/geography/part-8.json',H)],'cohort_inventory':{'index':pin(projection,H),'parts':[pin('data/'+p,H) for p in proj['location_parts']]}},'targets':targets}
config={'version':1,'selector':{'commit':H,'path':'data/ownership-selection.json'},'preparation_allowance':{'phaseBytes':1073741824,'rssBytes':1610612736},'source_evidence':evidence}
proof={'version':1,'original_cells':len(keys),'original_owners':90,'original_operands':len(negative)*90,'retained_operands':retained,'disjoint_operands':len(negative)*90-retained,'whole_negative_records':[{k:v for k,v in n.items() if k!='feature'} for n in negative],'targets':proof,'inputs':list(inputs.values()),'method':'GEOS whole-geometry disjointness against a closed envelope containing every complete source coordinate, complete selected coordinate, and all requested native centres; no clipping, repair, simplification, positive substitution or coverage removal. All admitted negative operands are byte-equivalent JSON whole geometries.','runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string},'limits':['Envelope proof applies only to the authenticated original source/selected geometry and full requested mask; any changed source or mask requires a new proof.','Compaction cannot certify sovereignty, source role, current land status, or clear pre-existing source-fitness holds.']}
encoded={'source-config.json':encode(config),'negative-equivalence.json':encode(proof)};prep={'complete':True,'inputs':list(inputs.values()),'outputs':{n:{'bytes':len(b),'sha256':sha(b)} for n,b in encoded.items()},'elapsed_seconds':time.monotonic()-started};encoded['preparation.json']=encode(prep)
assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb') as f:f.write(b)
print(json.dumps({'original_cells':len(keys),'original_targets':len(targets),'complete_negatives':len(negative),'original_operands':proof['original_operands'],'retained_operands':retained,'config_bytes':len(encoded['source-config.json']),'elapsed_seconds':prep['elapsed_seconds']}))

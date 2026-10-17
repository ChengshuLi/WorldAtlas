"""Authenticate full earlier island source families and exact original-centre applicability.
Usage: python check-prior-islands.py READ_ONLY_REPO FRESH_OUTPUT
No earlier source-fitness or current coastline finding is released by this screen.
"""
import ast,collections,gzip,hashlib,io,json,os,pathlib,resource,struct,subprocess,sys,time,xml.etree.ElementTree as ET
import numpy as np,shapely
from shapely.geometry import Polygon,shape
from shapely.ops import unary_union
W,O=map(lambda v:pathlib.Path(v).absolute(),sys.argv[1:]);H='d4968ddc37aa3aa6105e9610c9e6fadbb368ba14';F='9e3c3d8169526c4283699d80dbf7b66fc6cfc044';P='coordination/engineering/new-zealand-native-repair-20261017/'
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for p in (O,*O.parents))
pins={};total=0;MAX=64*1024*1024;PHASE=256*1024*1024;started=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
def read(path,commit=H,expected=None,decode=True):
 global total
 assert time.monotonic()-started<180 and path and not path.startswith('/') and all(x not in ['', '.', '..'] for x in path.split('/'))
 cmd=['git','-c','protocol.allow=never','-C',str(W)];meta,name=subprocess.check_output(cmd+['ls-tree','-z',commit,'--',path],env=env).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert mode=='100644' and kind=='blob' and name.decode()==path
 size=int(subprocess.check_output(cmd+['cat-file','-s',oid],env=env));assert 0<size<=MAX
 b=subprocess.check_output(cmd+['cat-file','blob',oid],env=env);assert len(b)==size and hashlib.sha1(b'blob '+str(size).encode()+b'\0'+b).hexdigest()==oid
 pin={'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':size,'sha256':sha(b)}
 if expected:assert size==expected['bytes'] and sha(b)==expected['sha256']
 if decode and path.endswith('.gz'):
  with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:d=f.read(MAX+1)
  assert len(d)<=MAX;pin.update(decoded_bytes=len(d),decoded_sha256=sha(d));b=d
  if expected:assert len(b)==expected['decoded_bytes'] and sha(b)==expected['decoded_sha256']
 if (commit,path) not in pins:total+=size+pin.get('decoded_bytes',0)
 assert total<=PHASE;pins[(commit,path)]=pin;return b
js=lambda p,h=H:json.loads(read(p,h))

def require(condition,message):
 if not condition:raise AssertionError(message)
program_path='data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/reproduce_current_coverage.py';program=read(program_path).decode();tree=ast.parse(program);scope={'gzip':gzip,'ET':ET,'Polygon':Polygon,'struct':struct,'require':require,'digest':sha,'unary_union':unary_union};function_pins={}
for name in ['parse_osm','parse_gshhg','gshhg_land']:
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name);text=ast.get_source_segment(program,node)+'\n';function_pins[name]=sha(text.encode());exec(compile(text,program_path+':'+name,'exec'),scope)
subjects=[];wanted=set();source_sets={}
for label,prefix in [('Bounty Islands','data/regional-review/regional-supplement-b5299df90ec984cc/bounty-islands/'),('Nukunonu','data/regional-review/regional-supplement-e5d72b7004238f80/nukunonu/')]:
 assessment=js(prefix+'assessment.json');coverage=js(prefix+'current-coverage.json');subject=next(r for r in coverage['subjects'] if r['name']==label);sp=coverage['source_pins']['osm'][label];encoded=read(sp['path'],decode=False);assert sha(encoded)==sp['compressed_sha256'];raw,rings=scope['parse_osm'](encoded);assert len(raw)<=MAX and sha(raw)==sp['decompressed_sha256'] and len(rings)==sp['coastline_ring_count'];pins[(H,sp['path'])].update(decoded_bytes=len(raw),decoded_sha256=sha(raw));audit=assessment['audit'];gids={int(r['gshhg_id']) for r in audit['gshhg_components']};wanted|=gids;source_sets[label]={'osm':rings,'gshhg_ids':gids};subjects.append({'name':label,'complete_original_assessment':assessment,'retained_current_coverage':coverage,'subject':subject})
gp=coverage['source_pins']['gshhg'];encoded=read(gp['path'],decode=False);assert sha(encoded)==gp['selected_records_compressed_sha256'];native,records=scope['parse_gshhg'](encoded,wanted);extraction=js('data/macro-improvements/macro-coverage-oceania/gshhg-extraction.json');assert len(native)==extraction['selected_native_bytes'] and sha(native)==extraction['selected_native_sha256']==gp['selected_records_native_sha256'] and len(records)==extraction['selected_record_count'];pins[(H,gp['path'])].update(decoded_bytes=len(native),decoded_sha256=sha(native))
segments=[]
for b in range(38,42):segments+=js(P+f'frozen-queue/block-{b:03}.json.gz',F)
cells=[(x,y,o[0]) for y,a,z,o,s,k in segments for x in range(a,z)];assert len(cells)==56626
binding=js('coordination/engineering/global-current-cell-work-queue-20261014/ownership-binding.json');lp=binding['native_latitudes'];lat=np.frombuffer(read(lp['path'],lp['commit']),dtype='<f8');assert pins[(lp['commit'],lp['path'])]['decoded_sha256']==lp['decoded_sha256'];pts=shapely.points([[(x+.5)/262166*360-180,lat[y]] for x,y,o in cells]);index=shapely.STRtree(pts);keys=set();rows=[]
for subject in subjects:
 name=subject['name'];families={'osm':source_sets[name]['osm'],'gshhg':{lid:scope['gshhg_land'](lid,records) for lid in source_sets[name]['gshhg_ids']}};out=[]
 for family,geometries in families.items():
  for ident,g in geometries.items():
   ix=index.query(g);found=[int(i) for i in ix[shapely.covers(g,pts[ix])]];keys.update(cells[i] for i in found);out.append({'family':family,'source_component_id':str(ident),'whole_geometry_sha256':sha(json.dumps(shapely.geometry.mapping(g),sort_keys=True,separators=(',',':')).encode()),'native_cells':[cells[i] for i in sorted(found)]})
 subject['full_original_source_component_contacts']=out;rows.extend(out)
result={'version':1,'original_cells':len(cells),'prior_subjects':subjects,'complete_gshhg_selected_records':len(records),'complete_gshhg_selected_native_bytes':len(native),'complete_original_source_components_screened':len(rows),'source_fitness_hold_keys':[list(k) for k in sorted(keys)],'source_fitness_hold_cells':len(keys),'parser_source':program_path,'parser_function_sha256':function_pins,'original_source_extraction':extraction,'inputs':list(pins.values()),'limits':['Complete original OSM rings and full original GSHHG records for both prior island subjects are retained and screened; no clipping, area recomputation or current coastline truth claim.','Archived pre-restoration absence and separately measured current indexed overlap remain distinct. Old source area/registration/vintage/DOC crosswalk disagreements and parent/semantic questions remain unresolved.','Exact original keys intersecting these unresolved prior physical-source families are held conservatively; a same-source native geometric diagnostic does not release the findings.','The complete retained selected GSHHG stream has 906 records; it is not represented as the complete worldwide GSHHG archive. Original selected-record extraction custody is preserved.']}
body=(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n').encode();assert len(body)<=MAX and total+len(native)+sum(len(json.dumps(s)) for s in subjects)+len(body)<=PHASE;assert not O.exists() and all(not p.is_symlink() for p in (O,*O.parents));O.mkdir()
with (O/'prior-island-applicability.json').open('xb') as f:f.write(body)
with (O/'preparation.json').open('x') as f:json.dump({'complete':True,'bytes':len(body),'sha256':sha(body)},f);f.write('\n')
print(json.dumps({'prior_subjects':len(subjects),'source_components':len(rows),'source_fitness_hold_cells':len(keys),'keys':sorted(keys),'processing_bytes':total,'elapsed_seconds':time.monotonic()-started}))

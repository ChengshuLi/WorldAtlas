import json,gzip,subprocess,hashlib,time,resource,sys
from pathlib import Path
import shapely
from shapely.geometry import shape,mapping
from shapely.affinity import translate
import comparison
root=Path('.cache/full-census');out=root/'gshhg-direct';start=time.monotonic();sha=lambda b:hashlib.sha256(b).hexdigest();read=lambda p:subprocess.check_output(['git','show','HEAD:'+p]);prefix='coordination/engineering/global-physical-comparison-20261006/results/'
stages=json.load(open(root/'all-stage-inputs.json'));candidates=[shape(s['consumed']['geometry']) for s in stages];bounds=[g.bounds for g in candidates];transport=json.loads(read(prefix+'transport-map.json'));metas={};selected=set();receipts=[]
def intersects(a,b):return not(a[2]<b[0]or a[0]>b[2]or a[3]<b[1]or a[1]>b[3])
for entry in transport['entries']:
 if entry['kind']!='sources':continue
 p=entry['delivered'];b=read(prefix+p['path']);assert len(b)==p['bytes'] and sha(b)==p['sha256'];raw=gzip.decompress(b);assert len(raw)==p['uncompressed_bytes'] and sha(raw)==p['uncompressed_sha256'];receipts.append(p)
 for line in raw.splitlines():
  m=json.loads(line);metas[m['id']]=m;a=m.get('decoded_pointset_bounds')
  if a and any(intersects([a[0]+shift,a[1],a[2]+shift,a[3]],box) for shift in [-360,0,360] for box in bounds):selected.add(m['id'])
 print('metadata',p['path'],len(metas),len(selected),flush=True)
assert len(metas)==188612
for ident in list(selected):
 seen=set()
 while metas[ident]['level'] in [2,3,4]:
  assert ident not in seen;seen.add(ident);parent=metas[ident]['container']
  if parent not in metas:break
  selected.add(parent);ident=parent
index=json.loads(read('coordination/engineering/gshhg-native-member-custody-20261007/results/member-index.json'));pieces=[]
for p in index['parts']:
 b=read('coordination/engineering/gshhg-native-member-custody-20261007/results/'+p['path']);assert len(b)==p['bytes'] and sha(b)==p['sha256'];raw=gzip.decompress(b);assert len(raw)==p['uncompressed_bytes'] and sha(raw)==p['uncompressed_sha256'];pieces.append(raw)
native=b''.join(pieces);del pieces;assert len(native)==index['member_bytes'] and sha(native)==index['member_sha256'];print('native verified',len(native),len(selected),flush=True)
validity=comparison.ValidityCache();geometries={};actual={}
for ident in sorted(selected):
 m=metas[ident];a=m['native_offset'];n=m['native_record_bytes'];meta,g=comparison.decode_record(native[a:a+44],native[a+44:a+n],m['ordinal'],a,validity);assert meta['decoded_pointset_binary64_sha256']==m['decoded_pointset_binary64_sha256'];actual[ident]=meta;geometries[ident]=g
 del meta
print('decoded',len(geometries),flush=True);del native
chains={}
for ident,m in actual.items():
 if m['level'] in [2,3,4]:
  parent=m['container'];chains[ident]=comparison.full_container_relation(geometries[ident],geometries.get(parent),validity)
results=[]
for stage,candidate in zip(stages,candidates):
 issues=[];levels={i:[] for i in [1,2,3,4]};queries=[]
 for ident,m in actual.items():
  a=m.get('decoded_pointset_bounds');g=geometries[ident]
  if not a:continue
  for shift in [-360,0,360]:
   if not intersects([a[0]+shift,a[1],a[2]+shift,a[3]],candidate.bounds):continue
   if m['level'] not in levels:issues.append({'source':ident,'reason':'unsupported-level'});continue
   if g is None or m['geometry_issues']:issues.append({'source':ident,'reason':m['geometry_issues']});continue
   ancestry=ident;seen=set();ok=True
   while actual[ancestry]['level'] in [2,3,4]:
    if ancestry in seen or chains[ancestry]['status']!='supported':issues.append({'source':ident,'reason':'container-chain','detail':chains.get(ancestry)});ok=False;break
    seen.add(ancestry);ancestry=actual[ancestry]['container']
   if not ok:continue
   gg=translate(g,xoff=shift) if shift else g;relation,piece=comparison.relation(candidate,gg,ident,shift,validity);queries.append(relation)
   if relation['status']!='checked':issues.append({'source':ident,'reason':relation});continue
   if piece is not None and not piece.is_empty:
    def polygons(g):
     if g.geom_type=='Polygon':return [g]
     if g.geom_type in ['MultiPolygon','GeometryCollection']:return [p for sub in g.geoms for p in polygons(sub)]
     return []
    levels[m['level']]+=polygons(piece)
 support=comparison.alternating_support(candidate,levels)
 for key in ['missing_reconstruction','extra_reconstruction','contradictory_land_water_support']:
  if not support[key].is_empty:issues.append({'reason':key,'geometry':mapping(support[key])})
 for key,g in support['hierarchy_disagreements'].items():
  if not g.is_empty:issues.append({'reason':key,'geometry':mapping(g)})
 results.append({'target':stage['target'],'source_id_queries':sorted(set(q['source_id'] for q in queries)),'query_relations':queries,'issues':issues,'support':{k:({kk:mapping(vv) for kk,vv in v.items()} if isinstance(v,dict) else mapping(v)) for k,v in support.items()}})
 print('target',stage['target'],'issues',len(issues),flush=True)
(out/'whole-target-support.json').write_text(json.dumps({'results':results,'source_member':index,'source_metadata_receipts':receipts,'runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string},'elapsed_seconds':time.monotonic()-start,'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'Diagnostic original GSHHG source-relative support for whole consumed targets; heterogeneous observation dates and physical authority limits retained.'})+'\n')

import os,sys,json,gzip,hashlib,subprocess,pathlib,struct,collections
import numpy as np,shapely
from shapely.geometry import shape,Polygon,GeometryCollection
from shapely.affinity import translate
W=pathlib.Path(__file__).resolve().parents[1]; HEAD='19858cf7aa887efad5d0c6ba0736d5672bf0aef5'; PREFIX='coordination/engineering/greenland-repair-delivery-20261017/'
consumed={}
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(commit,path):
 cmd=['git','-c','protocol.allow=never','-C',str(W)];env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1'}
 def git(*a):return subprocess.check_output(cmd+list(a),env=env)
 meta,name=git('ls-tree','-z',commit,'--',path).rstrip(b'\0').split(b'\t');mode,kind,oid=meta.decode().split();assert name.decode()==path and kind=='blob' and mode in ['100644','100755'];size=int(git('cat-file','-s',oid));assert size<=33554432;b=git('cat-file','blob',oid);assert len(b)==size
 consumed[(commit,path)]={'commit':commit,'path':path,'bytes':len(b),'sha256':sha(b),'git_blob_oid':oid};return b

def read(d,decode=False):
 b=blob(d['commit'],d['path']);r=consumed[(d['commit'],d['path'])]
 for k in ['bytes','sha256','git_blob_oid']:assert k not in d or r[k]==d[k]
 if decode:
  b=gzip.decompress(b);assert len(b)<=33554432 and len(b)==d['decoded_bytes'] and sha(b)==d['decoded_sha256'];r.update(decoded_bytes=len(b),decoded_sha256=sha(b))
 return b

def local(p):return json.loads(blob(HEAD,PREFIX+p))
cfg=local('config/physical.json')['physical'];pins={p['path']:p for p in cfg['inputs']};index=json.loads(read(pins[cfg['roles']['native_index']]));stages=json.loads(read(pins[cfg['roles']['stages']]));report=local('physical-001/whole-target-support.json');assert index==report['source_member'];expected={r['target']:r for r in report['results']};candidates={s['target']:shape(s['consumed']['geometry']) for s in stages};assert all(g.is_valid for g in candidates.values())
body=bytearray(index['member_bytes']);pos=0
for ordinal,p in enumerate(index['parts']):
 assert ordinal==p['ordinal'] and pos==p['offset'];d=pins[cfg['native_prefix']+'/'+p['path']];part=read(d,True);assert sha(part)==p['uncompressed_sha256'] and len(part)==p['uncompressed_bytes'];body[pos:pos+len(part)]=part;pos+=len(part);del part
assert pos==len(body) and sha(body)==index['member_sha256'];print('Authenticated full GSHHG member',len(body),flush=True)
header=struct.Struct('>3I4i2I2i');records={};selected={};pairs=collections.defaultdict(set);pos=ordinal=0

def intersects(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
def decode(offset,ordinal,make=False):
 ident,n,flag,west,east,south,north,area,full,container,ancestor=header.unpack_from(body,offset);end=offset+44+n*8;assert end<=len(body);native=np.frombuffer(body,dtype='>i4',count=n*2,offset=offset+44).reshape(n,2);coords=native.astype(np.float64)*1e-6;seam=(flag>>16)&3
 coords[(((native[:,0]>(270000000 if ordinal==0 else 180000000)) & bool(seam)) | (west>180000000)),0]-=360.0
 if ident not in (0,4) and seam&2:coords[coords[:,0]<0,0]+=360.0
 bounds=(float(coords[:,0].min()),float(coords[:,1].min()),float(coords[:,0].max()),float(coords[:,1].max()))
 return ident,end,flag&255,container,bounds,coords, bool(np.array_equal(native[0],native[-1]))
while pos<len(body):
 ident,end,level,parent,bounds,coords,closed=decode(pos,ordinal);assert ident not in records;records[ident]=(pos,ordinal,level,parent)
 matched=[]
 for tid,candidate in candidates.items():
  for shift in [-360,0,360]:
   if intersects((bounds[0]+shift,bounds[1],bounds[2]+shift,bounds[3]),candidate.bounds):matched.append((tid,shift))
 if matched:
  g=Polygon(coords);assert level in [1,2,3,4] and closed and g.is_valid and not g.is_empty,(ident,level,closed)
  selected[ident]=g
  for tid,shift in matched:pairs[tid].add((ident,shift))
 pos=end;ordinal+=1
assert ordinal==index['record_count']==188612
print('Scanned records',ordinal,'selected',len(selected),'query pairs',{k:len(v) for k,v in pairs.items()},flush=True)
# Authenticate entire source-parent ancestry for every query, reconstructing missing parent polygons if needed.
chain_count=0
for ident in list(selected):
 seen=set();current=ident
 while records[current][2]>1:
  assert current not in seen;seen.add(current);parent=records[current][3];assert parent in records
  for key in (current,parent):
   if key not in selected:
    offset,ord_,lv,par=records[key];ii,en,l,p,b,coords,closed=decode(offset,ord_);g=Polygon(coords);assert closed and g.is_valid;selected[key]=g
  assert records[parent][2]==records[current][2]-1
  assert any(selected[parent].covers(translate(selected[current],xoff=shift)) for shift in [-360,0,360]),(current,parent)
  chain_count+=1;current=parent
result={'head':HEAD,'reviewer':os.environ.get('CODEX_THREAD_ID'),'method':'Independent complete original GSHHG binary record scan, GMT source-range coordinate decoding, all bounding query frames and predicates, exact witness and alternating-level geometry reconstruction. No stock comparison/qualification module executed.','member_bytes':len(body),'member_sha256':sha(body),'scanned_records':ordinal,'selected_records':len(selected),'container_steps_checked':chain_count,'targets':[]}
del body

def polygons(g):
 if g.geom_type=='Polygon':return [g]
 if g.geom_type in ['MultiPolygon','GeometryCollection']:return [p for sub in g.geoms for p in polygons(sub)]
 return []
for tid,candidate in candidates.items():
 r=expected[tid];qs={(q['source_id'],q['periodic_offset']):q for q in r['query_relations']};assert len(qs)==len(r['query_relations']);assert set(qs)==pairs[tid];assert sorted(set(i for i,s in pairs[tid]))==r['source_id_queries'];levels={i:[] for i in [1,2,3,4]};wc=collections.Counter();witnesses=0
 for (ident,shift),q in qs.items():
  g=selected[ident] if shift==0 else translate(selected[ident],xoff=shift)
  actual={'source_covers_candidate':bool(g.covers(candidate)),'candidate_covers_source':bool(candidate.covers(g)),'intersects':bool(g.intersects(candidate)),'disjoint':bool(g.disjoint(candidate))};assert all(actual[k]==q[k] for k in actual) and q['status']=='checked',(tid,ident,actual,q)
  if actual['source_covers_candidate']:expected_w='complete-candidate-reconstruction';piece=candidate
  elif actual['candidate_covers_source']:expected_w='complete-source-record-reconstruction';piece=g
  elif not actual['intersects']:expected_w='disjoint-after-explicit-predicate';piece=GeometryCollection()
  else:expected_w='complete-operation-pointset';piece=candidate.intersection(g);witnesses+=1;assert shape(q['witness_geometry']).equals_exact(piece,0),(tid,ident,'witness')
  assert q['witness']==expected_w;wc[expected_w]+=1;levels[records[ident][2]]+=polygons(piece)
 unions={l:shapely.union_all(geoms) for l,geoms in levels.items()}
 land=shapely.union_all([unions[1].difference(unions[2]),unions[3].difference(unions[4])]);water=shapely.union_all([unions[2].difference(unions[3]),unions[4]]);outside=candidate.difference(unions[1]);all_=shapely.union_all([land,water,outside]);support={'mapped_land_support':land,'mapped_inland_water_support':water,'outside_mapped_L1_context':outside,'missing_reconstruction':candidate.difference(all_),'extra_reconstruction':all_.difference(candidate),'contradictory_land_water_support':land.intersection(water),'hierarchy_disagreements':{f'L{l}-outside-L{l-1}':unions[l].difference(unions[l-1]) for l in [2,3,4]}}
 counts={}
 for k,g in support.items():
  if isinstance(g,dict):
   for sub,value in g.items():assert shape(r['support'][k][sub]).equals_exact(value,0),(tid,k,sub)
  else:assert shape(r['support'][k]).equals_exact(g,0),(tid,k)
 for issue in r['issues']:assert issue['reason']=='contradictory_land_water_support' and shape(issue['geometry']).equals_exact(support[issue['reason']],0)
 assert len(r['issues'])==1 and shapely.get_dimensions(support['contradictory_land_water_support'])==1
 row={'id':tid,'queries':len(qs),'witness_types':dict(wc),'explicit_witness_geometries_exact':witnesses,'all_support_geometry_exact':True,'all_issue_geometry_exact':True,'contradiction_dimension':1,'contradiction_components':int(shapely.get_num_geometries(support['contradictory_land_water_support']))};result['targets'].append(row);print('PASS',row,flush=True)
result['consumed']=list(consumed.values());result['unique_raw_plus_decoded_input_bytes']=sum(d['bytes']+d.get('decoded_bytes',0) for d in consumed.values());assert result['unique_raw_plus_decoded_input_bytes']<=268435456
(W/'.review-greenland/physical-probe-result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS all physical originals and query/support/issue geometries',flush=True)

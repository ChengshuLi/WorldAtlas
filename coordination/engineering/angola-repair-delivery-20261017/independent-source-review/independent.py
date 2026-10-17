import pathlib,json,subprocess,gzip,hashlib,collections,time
import numpy as np
import shapely
from shapely.geometry import shape
D=pathlib.Path(__file__).resolve().parent;W=(D/'workspace.txt').read_text();H='ffb3b4595367baa8dab5f16a0880410b2cb21532';B='579c2850ab0eb4bbcc1a6f41f8eb0563791208fe';P='coordination/engineering/angola-repair-delivery-20261017/';pins=[];start=time.monotonic()
def raw(p,h=B):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',h+':'+p]);pins.append(dict(path=p,commit=h,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()));return b
def j(p,h=B):
 b=raw(p,h);return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
def auth(d):
 b=raw(d['path'],d.get('commit',B));assert len(b)==d['bytes'] and hashlib.sha256(b).hexdigest()==d['sha256'];return b
rows=[r for i in range(32,36) for r in j(P+f'frozen-queue/block-{i:03d}.json.gz',H)]
assert len(rows)==15252;cells={};klass={};stated={}
for y,a,z,owner,src,cl in rows:
 assert len(owner)==1
 for x in range(a,z):
  assert (y,x) not in cells;cells[y,x]=owner[0];klass[y,x]=cl;stated[y,x]=set(src)
assert len(cells)==170526
keys=sorted(cells);owners=np.array([cells[k] for k in keys]);selection=j('data/ownership-selection.json');manifest=j(selection['manifest_path']);lp=manifest['native_latitudes'];lat=np.frombuffer(gzip.decompress(auth(lp)),dtype='<f8');points=shapely.points([((x+.5)/262166*360-180,lat[y]) for y,x in keys]);
roster={r['source_id']:r for r in j('coordination/engineering/global-current-cell-work-queue-20261014/source-feature-roster.json.gz')};lineage=j('coordination/engineering/global-current-cell-work-queue-20261014/lineage.json.gz');owner_info={r['index']:r for r in lineage['locations']};cat=j('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');actual=[set() for _ in keys];sources={};family_hits={};validity={};families=['gb:AGO:ADM1','gb:AGO:ADM2','gb:COD:ADM1','gb:COG:ADM1','gb:NAM:ADM1','gb:ZMB:ADM1','gb:NAM:ADM2','gb:COD:ADM2']
for family in families:
 rec=next(r for r in cat['products'] if r['key']==family);bb=[]
 for part in rec['parts']:
  d=gzip.decompress(auth(part));assert len(d)==part['uncompressed_bytes'] and hashlib.sha256(d).hexdigest()==part['uncompressed_sha256'];bb.append(d)
 b=b''.join(bb);assert len(b)==rec['original_bytes'] and hashlib.sha256(b).hexdigest()==rec['original_sha256'];g=json.loads(b);assert len(g['features'])==rec['feature_count'];assert g['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84';sources[family]={};hits=[];validity[family]=0
 for f in g['features']:
  fid=family+':'+f['properties']['shapeID'];geom=shape(f['geometry']);assert geom.is_valid;validity[family]+=1;sources[family][fid]=f;indices=np.flatnonzero(shapely.covers(geom,points));
  if family in families[:6]:
   for i in indices:actual[i].add(roster[fid]['source_index'])
  if len(indices):hits.append(dict(id=fid,name=f['properties']['shapeName'],cells=len(indices),owners=dict(collections.Counter(int(owners[i]) for i in indices)),examples=[dict(y=keys[i][0],x=keys[i][1],lon=points[i].x,lat=points[i].y) for i in indices[:3]]))
 family_hits[family]=hits
assert all(actual[i]==stated[k] for i,k in enumerate(keys));assert sum(len(x) for x in sources.values())==539
for i,k in enumerate(keys):
 fid=owner_info[cells[k]]['id'];assert fid in sources['gb:AGO:ADM2'];assert roster[fid]['source_index'] in actual[i];assert owner_info[cells[k]]['source_atoms']==[fid];assert lineage['reverse'][fid]==[cells[k]]
physical=j(P+'physical-001/whole-target-support.json',H);physical_issues=[];coverage=collections.Counter();supported={}
for row in physical['results']:
 own=next(i for i in set(owners) if owner_info[i]['id']==row['target']);ix=np.flatnonzero(owners==own)
 for issue in row['issues']:
  hits=ix[shapely.covers(shape(issue['geometry']),points[ix])];physical_issues.append(dict(target=row['target'],reason=issue['reason'],cells=len(hits)))
 for cl,g in row['support'].items():
  if not g or not isinstance(g,dict) or not g.get("type"):continue
  hits=ix[shapely.covers(shape(g),points[ix])];coverage[cl]+=len(hits)
  for i in hits:supported.setdefault(keys[i],[]).append(cl)
assert len(supported)==len(keys);assert not any(r['cells'] for r in physical_issues)
historical=[]
for issue,path in [(1268,'research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson'),(1243,'research/geography/gap-source-angola-drc-shared-seams-20261006/inputs/component-features.geojson'),(1423,'coordination/engineering/angola-original-envelope-20261007/vintages/final-focused-one/original-components.geojson')]:
 gs=j(path);rs=[];allix=set()
 for f in gs['features']:
  ids=np.flatnonzero(shapely.covers(shape(f['geometry']),points));allix.update(int(x) for x in ids);rs.append(dict(id=f.get('id',f['properties'].get('id')),cells=len(ids),owners=dict(collections.Counter(int(owners[i]) for i in ids)),classes=dict(collections.Counter(klass[keys[i]] for i in ids))))
 historical.append(dict(issue=issue,unique_cells=len(allix),rows=rs))
result=dict(head=H,baseline=B,original_cells=len(cells),original_intervals=len(rows),owners=len(set(owners)),classes=dict(collections.Counter(klass.values())),source_feature_counts=validity,family_hits=family_hits,physical_support_classes=dict(coverage),physical_issues=physical_issues,historical=historical,input_pins=pins,elapsed_seconds=time.monotonic()-start)
(D/'independent-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['input_pins','family_hits','historical']}));print('extra ADM2 competitors',json.dumps({f:family_hits[f] for f in families[-2:]}));print('historical',json.dumps([{k:v for k,v in x.items() if k!='rows'} for x in historical]))

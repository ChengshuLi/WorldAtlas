import pathlib,json,zipfile,xml.etree.ElementTree as E,unicodedata,gzip,subprocess,hashlib,struct,collections,sys,io,os,time
from shapely.geometry import Polygon,MultiPolygon,Point
from shapely.ops import transform
from pyproj import Transformer
from pyproj.transformer import TransformerGroup
W=pathlib.Path(sys.argv[1]).absolute(); C=sys.argv[2]; O=pathlib.Path(sys.argv[3]).absolute()
P='coordination/engineering/czechia-original-repair-20261017'; R=str(W); H='21984e9ec4ec7370bc807e2da23cea2228747698'
assert __debug__ and len(sys.argv)==4 and len(C)==40
assert O.parent.is_dir() and not O.exists() and all(not p.is_symlink() for root in (W,O) for p in (root,*root.parents))
env={**os.environ,'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_TERMINAL_PROMPT':'0'}
inputs=[]; start=time.monotonic()
def read(p,c=C):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',R,'show',c+':'+p],env=env)
 inputs.append({'commit':c,'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
 return b
assert read(P+'/probes/derive-official-adverse-holds.py')==pathlib.Path(__file__).read_bytes()
archive=read(P+'/official-source-review-001/cuzk-official-au-etrs89-20261017.zip')
assert len(archive)==72849710 and hashlib.sha256(archive).hexdigest()=='22454f195dd7f7e2acd244b82b949c04a20eaf45a792bcfc8802260e9f03772c'
norm=lambda x:''.join(c for c in unicodedata.normalize('NFD',x.casefold())if not unicodedata.combining(c)).replace(' ','').replace('-','');ns={'g':'http://www.opengis.net/gml/3.2','au':'http://inspire.ec.europa.eu/schemas/au/4.0','gn':'http://inspire.ec.europa.eu/schemas/gn/4.0'};polys={};info={}
t=Transformer.from_crs('EPSG:4258','EPSG:3035',always_xy=True);w=Transformer.from_crs('OGC:CRS84','EPSG:3035',always_xy=True)
with zipfile.ZipFile(io.BytesIO(archive)).open('1.xml') as f:
 for event,e in E.iterparse(f,events=('end',)):
  if e.tag.split('}')[-1]=='member':
   for a in e:
    ident=a.get('{http://www.opengis.net/gml/3.2}id','')
    if not ident.startswith('AU.3.'):continue
    name=a.find('.//gn:text',ns).text;pp=[]
    for p in a.findall('.//g:Polygon',ns):
     def ring(z):
      aa=list(map(float,z.find('.//g:posList',ns).text.split()));return [(aa[i+1],aa[i])for i in range(0,len(aa),2)]
     pp.append(Polygon(ring(p.find('g:exterior',ns)),[ring(z)for z in p.findall('g:interior',ns)]))
    g=MultiPolygon(pp);assert g.is_valid and not g.is_empty;polys[norm(name)]=transform(t.transform,g);info[norm(name)]={'name':name,'official_id':ident,'polygons':len(pp)}
   e.clear()
assert len(polys)==77
scope=json.loads(read(P+'/source-review/candidate-scope.json'));owners={o['index']:o for o in scope['owners']};assert len({norm(o['name'])for o in owners.values()})==35 and all(norm(o['name'])in polys for o in owners.values())
bind=json.loads(read('coordination/engineering/global-current-cell-work-queue-20261014/ownership-binding.json',H));pin=bind['native_latitudes'];b=read(pin['path'],pin['commit']);assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'];lat=gzip.decompress(b);assert hashlib.sha256(lat).hexdigest()==pin['decoded_sha256'];size=bind['size'];counts=collections.Counter();details=[]
for y,a,z,oo,*rest in json.loads(gzip.decompress(read(P+'/source-stage-001/original-intervals.json.gz'))):
 assert len(oo)==1;o=owners[oo[0]];key=norm(o['name']);g=polys[key]
 for x in range(a,z):
  lon=(x+.5)*360/size-180;la=struct.unpack_from('<d',lat,y*8)[0];p=Point(w.transform(lon,la));dist=g.boundary.distance(p);inside=g.contains(p);category='near_current_official_boundary_5m' if dist<=5 else ('inside_current_official_name_candidate' if inside else 'outside_current_official_name_candidate');counts[category]+=1;details.append({'y':y,'x':x,'owner':oo[0],'official_id_candidate':info[key]['official_id'],'category':category,'distance_to_boundary_m':dist})
assert sum(counts.values())==3934
out={'kind':'read-only-current-official-district-challenge','scope_cells':3934,'all_77_district_geometries_valid':True,'counts':dict(counts),'projection_official':t.description,'projection_retained':w.get_last_used_operation().description,'projection_retained_accuracy_m':w.get_last_used_operation().accuracy,'projection_retained_definition':w.get_last_used_operation().definition,'source_crs':'official EPSG:4258; native atlas centres CRS84','native_latitude_pin':pin,'matching':'Unique normalized-name candidates only; not legal identity replacement. All original target IDs preserved.','limits':['Current October 2026 source does not certify historical 2010 geometry.','Five-metre boundary band is a conservative diagnostic uncertainty flag, not a qualification rule.','No output assigns owners, changes scope, or qualifies native cells.','An original source-relative positive may still be contradicted by stronger current evidence; contrary evidence must remain explicit.'],'official_candidates':info,'cells':details}
out['inputs']=inputs
held=[c for c in details if c['category']!='inside_current_official_name_candidate']
assert counts=={'inside_current_official_name_candidate':3786,'near_current_official_boundary_5m':19,'outside_current_official_name_candidate':129}
by=collections.defaultdict(list)
for c in held:by[c['y']].append([c['x'],c['x']+1,c['owner'],'current_official_district_disagreement' if c['category'].startswith('outside') else 'current_official_boundary_uncertainty'])
rows=[]
for y,rr in sorted(by.items()):
 merged=[]
 for r in sorted(rr):
  if merged and merged[-1][1]==r[0] and merged[-1][2:]==r[2:]:merged[-1][1]=r[1]
  else:merged.append(r)
 rows.append({'y':y,'runs':merged})
assert sum(z-a for r in rows for a,z,*_ in r['runs'])==148
products={'official-district-challenge.json':out,'prior-official-source-holds.json':{'rows':rows}}
encoded={n:(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()for n,v in products.items()}
assert not O.exists() and all(not p.is_symlink()for p in (O,*O.parents));O.mkdir()
for n,b in encoded.items():
 with (O/n).open('xb')as f:f.write(b)
receipt={'complete':True,'method_commit':C,'mandatory_held_cells':148,'outputs':{n:{'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}for n,b in encoded.items()},'seconds':time.monotonic()-start}
with (O/'preparation.json').open('x')as f:json.dump(receipt,f);f.write('\n')
print(json.dumps(receipt))

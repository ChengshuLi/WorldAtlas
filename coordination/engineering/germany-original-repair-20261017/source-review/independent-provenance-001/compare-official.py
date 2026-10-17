import zipfile,struct,json,pathlib,hashlib,collections
import numpy as np
from pyproj import CRS,Transformer
from shapely import points,STRtree
P=pathlib.Path('/workspace/shared/worldatlas-recovery/germany-source-screening')
def shp(b):
 out=[];o=100
 while o<len(b):
  _,n=struct.unpack_from('>2i',b,o);v=b[o+8:o+8+n*2];typ=struct.unpack_from('<i',v)[0];assert typ==5
  nr,np_=struct.unpack_from('<2i',v,36);starts=struct.unpack_from('<'+'i'*nr,v,44);xy=np.frombuffer(v,dtype='<f8',offset=44+4*nr,count=np_*2).reshape(-1,2).copy();out.append((starts,xy));o+=8+n*2
 return out
def dbf(b):
 count=struct.unpack_from('<I',b,4)[0];h,r=struct.unpack_from('<HH',b,8);fields=[];o=32
 while b[o]!=13:
  f=b[o:o+32];fields.append((f[:11].split(b'\0')[0].decode(),f[16]));o+=32
 rows=[]
 for i in range(count):
  rec=b[h+i*r:h+(i+1)*r];k=1;d={}
  for name,n in fields:d[name]=rec[k:k+n].decode('utf-8').strip();k+=n
  rows.append(d)
 return rows
z=zipfile.ZipFile(P/'DEU_ADM3.zip');a=shp(z.read('DEU_ADM3.shp'));an=dbf(z.read('DEU_ADM3.dbf'))
z=zipfile.ZipFile(P/'bkg-2021-nuts250-utm32s.zip');stem=next(n[:-4] for n in z.namelist() if n.endswith('NUTS250_N3.shp'));b=shp(z.read(stem+'.shp'));bn=dbf(z.read(stem+'.dbf'));crs=CRS.from_wkt(z.read(stem+'.prj').decode());tr=Transformer.from_crs(crs,4326,always_xy=True)
assert len(a)==len(b)==428
out=[]
for i,((ars,axy),(brs,bxy)) in enumerate(zip(a,b)):
 assert len(axy)==len(bxy) and len(ars)==len(brs)
 bx,by=tr.transform(bxy[:,0],bxy[:,1]);q=np.column_stack((bx,by));tree=STRtree(points(q));pairs,dist=tree.query_nearest(points(axy),return_distance=True,all_matches=False)
 # Bidirectional full-vertex correspondence, retaining actual measured tolerance.
 _,back=STRtree(points(axy)).query_nearest(points(q),return_distance=True,all_matches=False)
 # Match each complete ring by vertex count and centroid, then challenge its cyclic order.
 ar=[axy[x:y] for x,y in zip(ars,(*ars[1:],len(axy)))];br=[q[x:y] for x,y in zip(brs,(*brs[1:],len(q)))];used=set();ring_max=0.
 for aa in ar:
  candidates=[(float(np.linalg.norm(aa.mean(axis=0)-bb.mean(axis=0))),j) for j,bb in enumerate(br) if j not in used and len(aa)==len(bb)]
  _,j=min(candidates);used.add(j);bb=br[j];assert np.linalg.norm(aa[0]-aa[-1])<1e-10 and np.linalg.norm(bb[0]-bb[-1])<1e-10
  aa=aa[:-1];bb=bb[:-1];start=int(np.argmin(np.linalg.norm(bb-aa[0],axis=1)));n=len(bb)
  err=min(float(np.max(np.linalg.norm(aa-bb[(start+direction*np.arange(n))%n],axis=1))) for direction in (1,-1));assert err<2e-8,(i,j,err);ring_max=max(ring_max,err)
 assert len(used)==len(br)
 out.append(dict(ring_cyclic_order_verified=True,ring_max_distance_degrees=ring_max,record=i,name=an[i].get('Name'),official_name=bn[i].get('NUTS_NAME'),gf=bn[i].get('GF'),official_fields=bn[i],vertices=len(axy),parts=len(ars),max_distance_degrees=float(max(dist.max(),back.max()))))
r=dict(kind='independent-official-whole-record-vertex-correspondence',records=len(out),official_crs=crs.to_string(),official_transform=tr.description,maximum_distance_degrees=max(x['max_distance_degrees'] for x in out),rows=out)
path=pathlib.Path('/workspace/shared/worldatlas-recovery/germany-independent-review/official-correspondence.json');path.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='rows'}));print(out[0])

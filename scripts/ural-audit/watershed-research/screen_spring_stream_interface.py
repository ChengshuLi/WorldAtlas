import sys,json,hashlib,xml.etree.ElementTree as ET,numpy as np
from shapely.geometry import LineString
from shapely.strtree import STRtree
from pyproj import Geod
sys.path.insert(0,'landed-1b494125')
from spring_connector_graph import basin_labels
osm='/tmp/ural-spring-r2.osm';raw=open(osm,'rb').read();digest=hashlib.sha256(raw).hexdigest();
if digest!='1efbbfba123408ed8ebd4552b1e95b026dd3074225bebef77341819177541fae':raise ValueError('OSM source hash mismatch')
print('osm_sha256',digest,flush=True);root=ET.fromstring(raw);nodes={n.get('id'):(float(n.get('lon')),float(n.get('lat'))) for n in root.findall('node')};ways=[]
for w in root.findall('way'):
 tags={t.get('k'):t.get('v') for t in w.findall('tag')}
 if tags.get('waterway') not in ('stream','river'):continue
 ids=[n.get('ref') for n in w.findall('nd')]
 if any(i not in nodes for i in ids):continue
 if len(ids)>=2:ways.append((w.get('id'),w.get('version'),tags,LineString([nodes[i] for i in ids])))
print('mapped_stream_ways',len(ways),flush=True)
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')];g=Geod(ellps='WGS84');spring=(59.4185198,54.7035941)
for name,p,h,mask,mh in [('aw3d','/tmp/ural-dsm.tif','542c51c1cd7f79fcf5677ed4977ba086e1864aab49e6375ad371de44ceb3488b','/tmp/ural-msk.tif','a6ad6691b1b00d61a866b6413de40ce9abd9df6d9903b61623bbc1eec0e7adf7'),('cop','/tmp/ural-copernicus-dem.tif','d1d0a6b65e0fc19695f9414fd5bcece8a2f508a6f7790c70bb20677f20be3ef6',None,None)]:
 labels,t,geo,unknown=basin_labels(p,h,mask,mh,basins,[59.31,54.60,59.56,54.81],[2120068680,2120067740,3120001840],30);edges=[]
 def add(u,v):edges.append(LineString([geo.transform(*(t*(u[1],u[0]))),geo.transform(*(t*(v[1],v[0])))]))
 a,b=labels[:,:-1],labels[:,1:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
 for r,c in zip(rr,cc):add((int(r),int(c+1)),(int(r+1),int(c+1)))
 a,b=labels[:-1,:],labels[1:,:];rr,cc=np.where(((a==1)&(b==2))|((a==2)&(b==1)))
 for r,c in zip(rr,cc):add((int(r+1),int(c)),(int(r+1),int(c+1)))
 tree=STRtree(edges);hits=[]
 for wid,ver,tags,line in ways:
  for j in tree.query(line):
   z=line.intersection(edges[j]);pts=[z] if z.geom_type=='Point' else list(z.geoms) if z.geom_type=='MultiPoint' else []
   for pt in pts:
    d=g.inv(*spring,pt.x,pt.y)[2]
    if d<=2000:hits.append({'way_id':wid,'version':ver,'waterway':tags.get('waterway'),'name':tags.get('name:en',tags.get('name')),'distance_from_mapped_ural_start_m':d,'point':[pt.x,pt.y]})
 hits.sort(key=lambda x:x['distance_from_mapped_ural_start_m']);print(json.dumps({'dem':name,'sha':h,'unknown':unknown,'hit_count':len(hits),'hits':hits,'limits':'planar geometry intersects; graph models surface drainage and raster artefacts; OSM mapped streams do not establish surveyed headwater; nearby not proof of connection'},sort_keys=True),flush=True)

if hashlib.sha256(open(osm,'rb').read()).hexdigest()!=digest:raise ValueError('OSM source changed during screen')

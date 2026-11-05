import sys,json,hashlib,importlib.util
from pathlib import Path
from shapely.geometry import LineString,Point
from shapely.ops import substring
sys.path.insert(0,'landed-1b494125')
from spring_connector_graph import basin_labels
from spring_triple_route import interfaces,route
from pyproj import Geod

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
files={'snapshot':('/tmp/review_snapshot.json','615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc'),'osm':('/tmp/ural-river-r2.osm','89cef99ad92bb8acbd81da3f371a2244892ae71da49c99d4c478e9f111af56a0'),'north':('/tmp/ural-northern-arctic-draft/geometry.json','5a61a6aed4e95681c0c5ea40fd7d7b2cb94221ab18cbd4db72d99a2ca1d0538b'),'flow':('/tmp/ural-spring-flow-candidates-v2.jsonl','15090c202c3376489237263645f026722f44e1599f5aa7e9a3db29b70329cf92'),'cop':('/tmp/ural-copernicus-dem.tif','d1d0a6b65e0fc19695f9414fd5bcece8a2f508a6f7790c70bb20677f20be3ef6')}
for k,(p,h) in files.items():
 if h is not None and sha(p)!=h:raise ValueError('bad input '+k)
flowsha=sha(files['flow'][0]);flow=next(json.loads(line) for line in open(files['flow'][0]) if json.loads(line)['dem']=='cop')['radius_cell_square']['0']['candidate'];cells=flow['interface_cells'];(rr,cc),(nr,nc)=cells
if abs(rr-nr)+abs(cc-nc)!=1:raise ValueError('interface cells are not cardinal neighbors')
basins=[('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03','/tmp/ural-hydro-eu/hybas_eu_lev12_v1c.shp'),('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd','/tmp/ural-hydro-si/hybas_si_lev12_v1c.shp')];labels,t,geo,unknown=basin_labels(files['cop'][0],files['cop'][1],None,None,basins,[59.31,54.60,59.56,54.81],[2120068680,2120067740,3120001840],30)
if int(labels[rr,cc])!=2 or int(labels[nr,nc])!=1:raise ValueError('flow interface classes mismatch')
if rr==nr:
 c=max(cc,nc);edge=((rr,c),(rr+1,c))
else:
 r=max(rr,nr);edge=((r,cc),(r,cc+1))
graph,edges,coords=interfaces(labels,t,geo);edge=tuple(sorted(edge))
if edge not in edges[2]:raise ValueError('flow interface edge not present')
a,b=coords[edge[0]],coords[edge[1]];mid=[(a[0]+b[0])/2,(a[1]+b[1])/2]
north=json.load(open(files['north'][0]))['coordinates'];retained=north[-300:];v=route(labels,t,geo,retained,mid)
if 'candidate' not in v:raise ValueError('no triple-basin route')
candidate=v['candidate'];near=candidate['river_interface_lonlat']
if near not in [list(a),list(b)]:raise ValueError('route selected a vertex outside target interface edge')
other=list(b) if near==list(a) else list(a)
if len(candidate['coordinates'])>=3 and candidate['coordinates'][-3]==other:
 candidate['coordinates'].pop(-2)  # target midpoint was crossed before the last graph vertex


if sha('/tmp/ural-reconstruct-hybrid.py')!='da49e3b3e0c5155c39cf95967f5f0a1ac3d5f68d9d8f4429f840391e37de64bd':raise ValueError('hybrid code hash mismatch')
spec=importlib.util.spec_from_file_location('hybrid','/tmp/ural-reconstruct-hybrid.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);original,metadata=mod.reconstruct(json.load(open(files['snapshot'][0])),files['osm'][0],4969)
if not metadata['matches_selected_geometry']:raise ValueError('OSM relation does not reproduce selected river')
river=original['coordinates'][4969:];spring=river[0]
if river[0]!=spring:raise ValueError('OSM start not mapped spring')
fullnorth=LineString(north);cut=Point(candidate['retained_intersection_lonlat']);prefix=substring(fullnorth,0,fullnorth.project(cut));prefix_coords=[list(p) for p in prefix.coords];prefix_coords[-1]=candidate['coordinates'][0]
flowcenters=flow['terrain_centers'];full=prefix_coords[:-1]+candidate['coordinates']+flowcenters+[spring]+river[1:];line=LineString(full)
if not line.is_simple:raise ValueError('prototype complete line self-intersects')
if sha(files['flow'][0])!=flowsha:raise ValueError('flow input changed')
for k,(p,h) in files.items():
 if h is not None and sha(p)!=h:raise ValueError('input changed '+k)
g={'type':'LineString','coordinates':full};gh=hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest();report={'status':'research-only-not-selected','full_geometry_sha256':gh,'vertex_count':len(full),'flow_input_sha256':flowsha,'north_input_sha256':files['north'][1],'retained_cut':candidate['retained_intersection_lonlat'],'triple_node':candidate['triple_node_lonlat'],'interface_edge_endpoints':[list(a),list(b)],'spring_snap_m':flow['spring_snap_wgs84_m'],'flow_length_m':flow['flow_length_wgs84_m'],'triple_path_length_m':sum(Geod(ellps='WGS84').inv(*a,*b)[2] for a,b in zip(candidate['coordinates'],candidate['coordinates'][1:])),'river_edges':metadata['osm_main_stream_edges'],'river_end':river[-1],'limitations':['Northern selected fallback remains in source, not fully raw-derived.','Copernicus local D8 geometry and 15 m Arctic northern gaps are provisional; geographic accuracy not certified.','Connection snaps mapped spring to raster pixel center; spring identity is unverified.','Delta main-channel convention is provisional; physical-grid closure separate.','Source river relation mouth-role is at the Shagan confluence, far upstream from the selected coastal endpoint; canal and coastal endpoint need final selection.','No map or Neon selected data created.']}
with open('/tmp/ural-continuous-model-prototype-v2.geometry.json','x') as f:json.dump(g,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.write('\n')
with open('/tmp/ural-continuous-model-prototype-v2.report.json','x') as f:json.dump(report,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(report,sort_keys=True))

"""Bounded current-input source resolver validation. No writer or map build."""
import hashlib,importlib.util,json,sys
from pathlib import Path
R=Path.cwd();D=R/'regional-writer-integration-prep';sys.path[:0]=[str(D),str(R/'regional-lydekker-rule-work'),str(R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype')]
from osgeo import ogr
from source_groups import resolve_feature_windows
from component_scan import scan,component_at
from regional_rule import Line
import land_archive_source,polygon_intersection

def H(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def J(p):return json.loads(Path(p).read_bytes())
P=R/'regional-lydekker-rule-work/selected-regional-policy.json';assert H(P)=='bbac2240a2af5f6653438ee8831dba31ab5addc6e8833225c714beb3809a69c3';policy=J(P)
root=R/'aegean-archive-containment-integrated-20261105/group-label-multipolygon-prototype';assert H(root/'land_archive_source.py')=='58df321e63cd563a0c8a91dd89147e816f40155f2c23bac9cdd0ba61eb6abac9';assert H(root/'polygon_intersection.py')=='391c7dee1b91dfa9c78ad087a46a9c9e9c8df778183ebc706b481e0286d110d5'
paths={'anu-west-new-guinea-lydekker-ch08':R/'lydekker-line-research-20261105/anu-official-r2-readback.pdf','nga-sailing-directions-pub164-project-copy':R/'indonesia-geonames-research-20261105/pub164-official-r2-readback.pdf','indonesia-big-national-gazetteer':R/'tanimbar-tandula-research-20261105/big-readback.pdf','geonames-country-id':R/'indonesia-geonames-research-20261105/r2-readback.zip','osm-land-polygons-split-4326':R/'v2-source-download-20261103-kKbO2t/osmdata-mirror-land-polygons-split-4326-20261103.zip','detik-talaud-mangupun':R/'indonesia-northern-arc-cluster-20261105/r2-detik.html'}
sources={r['source_id']:{'path':str(paths[r['source_id']]),'version':r['version'],'sha256':r['sha256']} for r in policy['sources']};sources['osm-land-polygons-split-4326']['shapefile']=str(R/'v2-source-download-20261103-kKbO2t/accepted-mirror-land-candidate/land-polygons-split-4326/land_polygons.shp')
inputs={'physical_rows':{'path':str(R/'physical-direct-output-20261103/rows.u32le'),'sha256':'6cf4b928b6609b4d9c8fdd9264bb6f463a38a5d7376d6ffb0ffc43502284a468'},'physical_runs':{'path':str(R/'physical-direct-output-20261103/runs.u32le'),'sha256':'1396fe9dfde48b65b6e5884089a5445682511fb47f9560ce06edd53c95d928d7'},'component_rows':{'path':str(R/'fresh-components-output-20261104/rows.u32le'),'sha256':'4beda178bfc7beeb2d30cbdfa5901a48f9a41bb82c69e534d4c8cddfdb09aea7'},'component_runs':{'path':str(R/'fresh-components-output-20261104/runs.u32le'),'sha256':'18d7f36fa22c5728662cdd40487bf684108da030c074fec6d22ac378d0df0961'}}
linepath=R/'boo-boundary-broader-20261105/boo-east-candidate.json';assert H(linepath)=='bb7a9c4621646c98d25c4cc4685346fbb6bc468db6015f2d7a3926780c27a02e';line=Line({'type':'LineString','coordinates':J(linepath)['coordinates']});grid={'width':131072,'height':54614,'west':-180,'north':90,'step':360/131072};print('scanning region',flush=True);region=scan(inputs['component_rows'],inputs['component_runs'],grid,policy['regional_bounds_lon_lat'],line)
def inside(geometry,lon,lat):
 g=ogr.CreateGeometryFromJson(json.dumps(geometry));p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(lon,lat);return bool(g.Contains(p))
print('resolving eight source features',flush=True);out=resolve_feature_windows(policy,region,grid,inputs,sources,extract=land_archive_source.extract,intersect=polygon_intersection.intersect,point_inside=inside,component_at=component_at)
# Report is diagnostic only, not an input selector. Runtime resolves from sources.
out['status']='live-source-resolution-diagnostic-not-selection';out['policy_file_sha256']=H(P);out['code_sha256']={'source_groups':H(D/'source_groups.py'),'land_archive_source':H(root/'land_archive_source.py'),'polygon_intersection':H(root/'polygon_intersection.py')};dest=D/'live-source-resolution.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print('completed',len(out['windows']),'groups',len(out['anchors']),'anchors',H(dest),flush=True)

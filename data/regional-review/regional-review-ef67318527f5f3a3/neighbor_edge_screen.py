#!/usr/bin/env python3
"""Compute a same-vintage Turkey ADM2 edge screen, not a topology correction."""
import csv,gzip,json,pathlib
from pyproj import Transformer
from shapely.geometry import shape
from shapely import make_valid
from shapely.ops import transform
from shapely.strtree import STRtree
ROOT=pathlib.Path(__file__).parent
src=json.load(gzip.open(ROOT/'sources/geoBoundaries-TUR-ADM2.geojson.gz','rt'))['features']
proj=Transformer.from_crs('EPSG:4326','EPSG:6933',always_xy=True).transform
geoms=[make_valid(transform(proj,make_valid(shape(x['geometry'])))) for x in src]
tree=STRtree(geoms); by_id={str(f['properties']['shapeID']):i for i,f in enumerate(src)}
issue=json.load(open(ROOT/'issue-71-api.json'));b=issue['body'];s=json.loads(b[b.index('{"area_scopes"'):b.index('\n```',b.index('{"area_scopes"'))])
scoped={x.rsplit(':',1)[-1] for x in s['member_location_ids'] if x.startswith('gb:TUR:ADM2:')}
rows=[]
for sid in sorted(scoped):
 i=by_id[sid];g=geoms[i];neighbors=[];overlaps=[]
 for j in tree.query(g):
  j=int(j)
  if j==i:continue
  h=geoms[j]
  shared=g.boundary.intersection(h.boundary).length
  if shared>0.1:neighbors.append((j,shared))
  overlap=g.intersection(h).area
  if overlap>1000:overlaps.append((j,overlap))
 rows.append({'shapeID':sid,'shapeName':src[i]['properties'].get('shapeName',''),'shared_boundary_neighbor_count_gt_0_1m':len(neighbors),'largest_shared_boundary_m':round(max((x[1] for x in neighbors),default=0),2),'source_subject_perimeter_km':round(g.length/1000,3),'unshared_boundary_fraction_including_coast_and_gaps':round(max(0,1-sum(x[1] for x in neighbors)/g.length),6) if g.length else '', 'positive_overlap_pair_count_area_gt_1000m2':len(overlaps),'interpretation':'Same-release edge screen only. Unshared boundary includes coast, islands, source gaps, and unmatched edges; positive sliver overlaps are candidates for inspection. Neither metric proves completeness or a defect.'})
with open(ROOT/'neighbor-edge-screen.csv','w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)
print('scoped Turkey rows',len(rows),'shared-edge candidates',sum(int(x['shared_boundary_neighbor_count_gt_0_1m'])>0 for x in rows),'overlap flags',sum(int(x['positive_overlap_pair_count_area_gt_1000m2'])>0 for x in rows))

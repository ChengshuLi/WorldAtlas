"""Small unchanged-helper/ordinary-reader controls; not another scoped execution."""
import json,math,pathlib,tempfile
import kernel,verify
from shapely.geometry import Polygon,MultiPolygon,LineString,box
HERE=pathlib.Path(__file__).resolve().parent
rows=[]
def check(name,candidate,residue,status,reason=None):
    actual=kernel.point_diagnostics(candidate,residue)
    if actual['status']!=status or reason and actual.get('reason')!=reason:raise ValueError('Intended unchanged helper branch failed '+name+str(actual))
    rows.append({'name':name,'outcome':'passed','status':actual['status'],'reason':actual.get('reason'),'complete_result':actual})
triangle=Polygon([(0,0),(1,0),(0,1),(0,0)])
check('actual-exact-helper-valid-triangle',box(-1,-1,2,2),triangle,'diagnostic')
check('actual-exact-helper-nontriangle-retained',box(-1,-1,2,2),box(0,0,1,1),'diagnostic')
assert rows[-1]['complete_result']['nontriangle_polygons'] and not rows[-1]['complete_result']['triangles']
check('actual-exact-helper-nonpolygon-unsupported',box(0,0,1,1),LineString([(0,0),(1,1)]),'unsupported','nonpolygon-or-missing-geometry')
check('actual-exact-helper-touching-multipart-unsupported',MultiPolygon([box(0,0,1,1),box(1,0,2,1)]),triangle,'unsupported')
assert rows[-1]['complete_result']['reason']=='intersecting-or-touching-rings'
for segments,reason in [(1030,'segment-budget-exceeded'),(800,'topology-pair-budget-exceeded')]:
 points=[(math.cos(i*2*math.pi/segments),math.sin(i*2*math.pi/segments))for i in range(segments)];points.append(points[0])
 check('actual-exact-helper-'+reason,Polygon(points),triangle,'unsupported',reason)
with tempfile.TemporaryDirectory(prefix='1353-small-reader-controls-',dir=HERE.parents[2]/'.cache')as directory:
 p=pathlib.Path(directory);(p/'positive').write_bytes(b'ordinary')
 assert verify.ordinary(p,'positive')==b'ordinary';rows.append({'name':'actual-ordinary-reader-positive','outcome':'passed'})
 (p/'link').symlink_to(p/'positive')
 for name in ('link','../foreign','/absolute'):
  try:verify.ordinary(p,name)
  except ValueError:rows.append({'name':'actual-ordinary-reader-reject-'+name,'outcome':'passed'})
  else:raise ValueError('Actual ordinary path guard did not reject')
 with (p/'overbound').open('wb')as f:f.truncate(verify.LIMIT+1)
 try:verify.ordinary(p,'overbound')
 except ValueError:rows.append({'name':'actual-ordinary-reader-stat-overbound-before-read','outcome':'passed'})
 else:raise ValueError('Ordinary pre-read bound failed')
print(json.dumps({'method_id':'retained-exact-point-diagnosis','kind':'controls','outcome':'passed','actual_controls':len(rows),'controls':rows,'limits':['Bounded directed fixtures only; unchanged helper caps/method.','No actual source/candidate coordinates changed; no new full46 operator/query cohort.']},sort_keys=True))

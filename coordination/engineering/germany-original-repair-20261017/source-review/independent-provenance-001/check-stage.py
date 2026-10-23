import subprocess,json,gzip,os,collections,pathlib
from shapely.geometry import shape
from shapely.ops import unary_union
R='/workspace/scratch/127991fc8b8e/worldatlas-primary';H='eb06af616eb876b612fd433d81d632981642799b';P='coordination/engineering/germany-original-repair-20261017/source-stage-001/'
def get(n):return subprocess.check_output(['git','-C',R,'show',H+':'+P+n],env=dict(os.environ,GIT_NO_LAZY_FETCH='1'))
stage=json.loads(get('original-stage-inputs.json'));members=json.loads(get('source-target-membership.json'));intervals=json.loads(gzip.decompress(get('original-intervals.json.gz')));patch=json.loads(get('original-native-patch.json'))
source=json.load(open('/workspace/shared/worldatlas-recovery/germany-source-screening/gb-DEU-ADM3-original.geojson'))['features'];byid={'gb:DEU:ADM3:'+f['properties']['shapeID']:f for f in source};byowner=collections.defaultdict(list);seen=set()
for s,m in zip(stage,members):
 assert s['target']==m['source_id'] and s['selected']['id']==m['target_id'];assert s['consumed']==byid[s['target']];assert s['target'] not in seen;seen.add(s['target']);byowner[m['pixelIndex']].append(s)
assert len(stage)==len(members)==len(seen)==100 and len(byowner)==82
unions=[]
for owner,ss in byowner.items():
 assert all(s['selected']==ss[0]['selected'] for s in ss)
 a=unary_union([shape(s['consumed']['geometry']) for s in ss]);b=shape(ss[0]['selected']['geometry']);diff=a.symmetric_difference(b).area
 unions.append(dict(owner=owner,atoms=len(ss),symmetric_difference_degrees2=diff,topologically_equal=a.equals(b)))

keys=set();category=collections.Counter()
for y,a,b,owners,physical,cat in intervals:
 assert len(owners)==1
 for x in range(a,b):
  k=(y,x,owners[0]);assert k not in keys;keys.add(k);category[cat]+=1
pk={(r['y'],x,o) for r in patch['rows'] for a,b,o,*rest in r['runs'] for x in range(a,b)};assert pk==keys and len(keys)==27555 and len(intervals)==7499
r=dict(head=H,original_cells=len(keys),intervals=len(intervals),categories=dict(category),owners=len(byowner),atoms=len(seen),all_consumed_atoms_literal=True,all_selected_geometries_equal_complete_atom_union=all(v['topologically_equal'] for v in unions),unions=unions)
pathlib.Path('/workspace/shared/worldatlas-recovery/germany-independent-review/source-stage-check.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k!='unions'})

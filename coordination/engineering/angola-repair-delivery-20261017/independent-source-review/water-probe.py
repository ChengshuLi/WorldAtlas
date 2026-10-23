import pathlib,json,subprocess,gzip,hashlib
import numpy as np,shapely
from shapely.geometry import shape
D=pathlib.Path(__file__).resolve().parent;W=(D/'workspace.txt').read_text();H='ffb3b4595367baa8dab5f16a0880410b2cb21532';P='coordination/engineering/angola-repair-delivery-20261017/'
def j(p):
 b=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',H+':'+p]);return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
s=j(P+'native-inputs-001/source-evidence.json')['native_latitudes'];b=subprocess.check_output(['git','-c','protocol.allow=never','-C',W,'show',s['commit']+':'+s['path']]);assert hashlib.sha256(b).hexdigest()==s['sha256'];lat=np.frombuffer(gzip.decompress(b),dtype='<f8');rows=[r for q in range(32,36) for r in j(P+f'frozen-queue/block-{q:03}.json.gz')];cells=[dict(y=y,x=x,owner=o[0],lon=(x+.5)/262166*360-180,lat=float(lat[y]),gshhg=cl) for y,a,z,o,s,cl in rows for x in range(a,z)];pts=shapely.points([(r['lon'],r['lat']) for r in cells]);gs=j('research/geography/gap-source-namibia-angola-20261006/inputs/original-components.geojson');out=[]
for f in gs['features']:
 ix=np.flatnonzero(shapely.covers(shape(f['geometry']),pts));out.extend(dict(**cells[i],component=f.get('id',f['properties'].get('id'))) for i in ix)
assert len(out)==6150;(D/'water-probe-centres.json').write_text(json.dumps(out));print(len(out))

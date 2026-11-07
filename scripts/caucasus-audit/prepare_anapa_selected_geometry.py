"""Prepare selected Anapa geometry and region hash; no Neon writes."""
import hashlib,json
from pathlib import Path
from shapely.geometry import Polygon,Point
s=json.loads(Path('caucasus-real-snapshot-recipe-local.json').read_text())
b={x['boundary_id']:x['geometry']['coordinates'] for x in s['mainland_boundaries']}
r={x['route_id']:x['geometry']['coordinates'] for x in s['routes']}
candidate=json.loads(Path('/tmp/caucasus-anapa-candidate-r2.json').read_text())
closure=json.loads(Path('/tmp/anapa-new-closure.json').read_text())
b['caucasus_blacksea_anapa_to_caspian']=candidate['coordinates'];r['europe_exterior_closure_v1']=closure['coordinates']
segments=[b['ural_kara_coast_to_caspian'],r['europe_caspian_closure_v1'],list(reversed(candidate['coordinates'])),list(reversed(closure['coordinates']))]
assert all(segments[i][-1]==segments[(i+1)%4][0] for i in range(4))
ring=[]
for x in segments:ring.extend(x if not ring else x[1:])
p=Polygon(ring)
assert p.is_valid and p.exterior.is_simple
region=next(x for x in s['seed_regions'] if x['region_id']=='europe_mainland_region_v1')
for w in region['witnesses']:
 assert p.contains(Point(float(w['lon']),float(w['lat'])))==w['inside']
def sha(g):return hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
report={'candidate_geometry_sha256':sha(candidate),'closure_geometry_sha256':sha(closure),
        'region_geometry_sha256':sha({'type':'Polygon','coordinates':[ring]}),
        'candidate_vertices':len(candidate['coordinates']),'closure_vertices':len(closure['coordinates']),
        'region_witnesses':len(region['witnesses']),'ring_valid':True}
assert report['candidate_geometry_sha256']=='e3dd7f326c0247f4d9f4c4c61b7c31782a5fc1b9e850d164cf46e729cbb60929'
assert report['closure_geometry_sha256']=='dc5ddd0580b3c1bed14d9428aa0a0d5a214d963f1efdddb629f88fa704ea7a87'
Path('/tmp/anapa-selection-geometry-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))

import sys,json,pathlib
sys.path.insert(0,str(pathlib.Path('scripts').resolve()))
from shapely.geometry import shape
from shapely import get_parts
from evidence.geometry import canonical_land
p=pathlib.Path('coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11')
d=json.loads((p/'results-v1/staged-neighbors.json').read_text());c=shape(d['component']['geometry'])
before={f['id']:shape(f['geometry']) for f in d['baseline']};after={f['id']:shape(f['geometry']) for f in d['candidate']}
pair=d['subject_ids'];a,b=pair
raw_before=before[a].intersection(before[b]);raw_after=after[a].intersection(after[b]);raw_added=raw_after.difference(raw_before)
canonical_before=canonical_land(before[a]).intersection(canonical_land(before[b]));canonical_after=canonical_land(after[a]).intersection(canonical_land(after[b]));canonical_added=canonical_after.difference(canonical_before)
rows=[]
for f in json.loads((p/'results-v1/world-regression.json').read_text())['regression']['findings']['features']:
 g=shape(f['geometry']);rows.append({'bounds':g.bounds,'area':g.area,'outside_component_area':g.difference(c).area,'inside_component_area':g.intersection(c).area})
result={'method':'diagnostic clone only, no source/candidate changes','pair':pair,'raw':{'before_overlap_area':raw_before.area,'after_overlap_area':raw_after.area,'new_overlap_area':raw_added.area},'canonical':{'before_overlap_area':canonical_before.area,'after_overlap_area':canonical_after.area,'new_overlap_area':canonical_added.area},'findings':rows,'subject_differences':{i:{'outside_component_added_area':after[i].difference(before[i]).difference(c).area,'outside_component_lost_area':before[i].difference(after[i]).difference(c).area}for i in pair}}
pathlib.Path('.cache/shared-edge-991/diagnosis-v1.json').write_text(json.dumps(result)+'\n');print(json.dumps(result))

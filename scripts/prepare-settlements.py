"""Import source-date settlement estimates, never location totals or inferred ranks."""
import json,pathlib
from shapely import STRtree
from shapely.geometry import shape
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];geoms=[shape(f['geometry']) for f in fs]
# Settlement population estimates belong to settlements, not their host location.
places=read(R/'.cache/semantic/populated-places.geojson')['features'];tree=STRtree(geoms);entities=[];history=[];seen=set();unsupported=[];series=0
for f in places:
 p=f['properties'];populations=[(year,p.get(f'POP{year}',0)) for year in range(1950,2030,5) if isinstance(p.get(f'POP{year}'),(int,float)) and p[f'POP{year}']>0]
 if not populations:continue
 series+=1
 point=shape(f['geometry']);hits=tree.query(point,predicate='intersects')
 if len(hits)!=1:unsupported.append({'source_id':p['NE_ID'],'name':p['NAME'],'matches':len(hits),'reason':'No unique source territory at the published settlement coordinate'});continue
 id='settlement:ne:'+str(p['NE_ID'])
 if id in seen:continue
 seen.add(id);entities.append({'id':id,'kind':'settlement','name':p['NAME'],'parent_id':fs[int(hits[0])]['id'],'source':'Natural Earth populated places / embedded UN urban agglomeration estimates'})
 for year,value in populations:history.append({'id':f'ne-pop:{id}:{year}','entity_id':id,'field':'attributes','valid_from':year,'valid_to':year+1,'source':'Natural Earth populated places / UN urban agglomeration estimate or projection; source values in thousands, converted to persons; not location population','value':{'population':round(value*1000)}})
write(D/'settlement-estimates.json',{'entities':entities,'entity_history':history});print(json.dumps({'settlements':len(entities),'population_estimates':len(history)}),flush=True)


write(D/'settlement-source-report.json',{'source_places':len(places),'places_with_series':series,'imported_settlements':len(entities),'supported_estimate_records':len(history),'unsupported':unsupported,'precision':'Source series in thousands converted to persons; values remain modeled estimates or projections, not census counts'})

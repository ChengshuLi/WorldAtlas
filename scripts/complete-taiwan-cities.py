"""Use source ADM1 membership for Taiwan's city districts.

Independently compiled Natural Earth city outlines differ at urban seams. The
same-source administrative membership takes precedence over footprint overlap.
"""
import json,pathlib
from shapely import union_all
from shapely.geometry import shape,mapping
R=pathlib.Path(__file__).resolve().parents[1];D=R/'data';C=R/'.cache/semantic'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')))
fs=[f for p in read(D/'world-index.json')['parts'] for f in read(D/p)['features']];units={u['id']:u for u in read(D/'hierarchy.json')};baseline=read(C/'input.geojson')['features'];bu={u['id']:u for u in read(C/'input-hierarchy.json')};report=read(D/'semantic-report.json')
cities={'Taipei':('TWN-1166',12),'New Taipei':('TWN-1167',29),'Taoyuan':('TWN-1168',13),'Taichung':('TWN-1174',29),'Tainan':('TWN-1160',37),'Kaohsiung':('TWN-1156',38),'Keelung':('TWN-1164',7),'Hsinchu':('TWN-1161',3),'Chiayi':('TWN-1171',2)}
if all(next((f['properties']['metadata'].get('city_membership_version') for f in fs if f['id']=='atlas:city:'+code),None)==1 for code,count in cities.values()):print('Taiwan city memberships already verified');raise SystemExit
members=[];new=[];remove=set();changes=[]
for name,(code,count) in cities.items():
 rows=[f for f in baseline if f['properties']['metadata'].get('source_id')=='gb:TWN:ADM2' and bu[f['properties']['parent_id']]['name']==name]
 assert len(rows)==count,(name,len(rows),count)
 assert all(f['properties']['metadata'].get('hierarchy_source')=='gb:TWN:ADM1' for f in rows)
 ids=[f['id'] for f in rows];members+=rows;id='atlas:city:'+code;remove.update(ids+[id]);g=union_all([shape(f['geometry']) for f in rows]);parent=rows[0]['properties']['parent_id'];u=bu[parent]
 while parent:
  units.setdefault(parent,bu[parent]);parent=bu[parent]['parent_id']
 parent=rows[0]['properties']['parent_id'];meta={'source_name':'Atlas source aggregation','source_id':id,'source_url':'https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/TWN','license':read(D/'administrative-sources.json')['gb:TWN:ADM2']['boundaryLicense'],'reference_year':'Source administrative snapshot; municipality status is modern reference','location_basis':'Published city municipality; same-source ADM1 district membership','administrative_level':'City municipality','source_member_ids':ids,'search_aliases':sorted({name,name+' City'}|{f['properties']['name'] for f in rows}),'representative_point':list(g.representative_point().coords)[0],'reference_version':3,'hierarchy_version':3,'topology_version':1,'semantic_version':1,'remote_version':1,'coverage_version':1,'city_membership_version':1}
 new.append({'type':'Feature','id':id,'properties':{'id':id,'name':name,'parent_id':parent,'reference_owner':'Taiwan','metadata':meta},'geometry':mapping(g)});changes.append({'id':id,'name':name,'basis':meta['location_basis'],'source':meta['source_url'],'replaces':ids,'source_names':[f['properties']['name'] for f in rows],'coverage_error_degrees2':0})
fs=[f for f in fs if f['id'] not in remove]+new;report['changes']=[x for x in report['changes'] if x['id'] not in {f['id'] for f in new}]+changes
old_retired={x['id'] for x in report['retired']};report['retired'].extend({'id':f['id'],'name':f['properties']['name']} for f in members if f['id'] not in old_retired);report['locations']=len(fs);report['retired_locations']=len(report['retired']);report['city_membership_audit']=[x for x in report['city_membership_audit'] if not x['source'].startswith('TWN-')];report['city_membership_audit'].extend({'city':c['name'],'source':'geoBoundaries TWN ADM1/ADM2','members':[{'id':id,'named_parent_match':True} for id in c['replaces']]} for c in changes);report['taiwan_city_membership']={name:{'location_id':'atlas:city:'+code,'districts':count,'source':'geoBoundaries Taiwan ADM1/ADM2 crosswalk'} for name,(code,count) in cities.items()};parts=[]
for i in range(0,len(fs),1500):
 p=f'geography/part-{i//1500}.json';parts.append(p);write(D/p,{'type':'FeatureCollection','features':fs[i:i+1500]})
write(D/'world-index.json',{'parts':parts});write(D/'hierarchy.json',list(units.values()));write(D/'semantic-report.json',report);print('Taiwan:',sum(c for _,c in cities.values()),'source districts →',len(new),'city territories',flush=True)

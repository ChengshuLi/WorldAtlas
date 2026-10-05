exec(open('.cache/shared-edge-991/exact-world-case.py').read().split('counts={};')[0])
from exact_arrangement import boundaries,export_rings
from shapely.geometry import shape
labels=[];before_labels=[];unknown=[]
for n,(ring,area,p)in enumerate(arrangement['faces']):
 old=[k for k in all_before if classify(p,polys['old:'+k])];in_component=classify(p,polys['component'])
 named=[k for k in source if classify(p,polys['source:'+k])]if in_component and not old else[]
 after=old if old else[ns['SUBJECTS'][named[0]]]if in_component and len(named)==1 else[]
 if in_component and not old and len(named)!=1:unknown.append(n)
 labels.append(after);before_labels.append(old)
export={};summaries={}
for id in d['subject_ids']:
 r=boundaries(arrangement['faces'],labels,id);g=export_rings(r);export[id]=g
 polygon=shape(g);summaries[id]={'rings':len(r),'valid_rounded':polygon.is_valid,'rounded_type':polygon.geom_type}
result={'diagnostic_only':True,'unknown_component_faces':unknown,'lost_face_memberships':sum(len(set(old)-set(new))for old,new in zip(before_labels,labels)),'new_multiple_faces':sum(len(new)>1 and len(old)<=1 for old,new in zip(before_labels,labels)),'source_added_faces':sum(not old and bool(new)for old,new in zip(before_labels,labels)),'summaries':summaries,'candidates':export}
pathlib.Path('.cache/shared-edge-991/exact-export-v1.json').write_text(json.dumps(result)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='candidates'}))

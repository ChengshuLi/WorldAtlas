import importlib.util,json,pathlib,struct,hashlib
from shapely.geometry import Polygon,box
from shapely import prepare
p=pathlib.Path(__file__).with_name('comparison.py');spec=importlib.util.spec_from_file_location('draft',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
passed=[]
def control(name,operation):
 operation();passed.append(name)
def nested():
 g=box(0,0,10,10);l1=g;l2=box(2,2,8,8);l3=box(3,3,7,7);l4=box(4,4,6,6)
 x=m.alternating_support(g,{1:[l1],2:[l2],3:[l3],4:[l4]})
 assert x['mapped_land_support'].area==76 and x['mapped_inland_water_support'].area==24
 assert all(v.is_empty for v in x['hierarchy_disagreements'].values())
 assert x['missing_reconstruction'].is_empty and x['extra_reconstruction'].is_empty
 assert not x['mapped_land_support'].covers(box(4.2,4.2,5.8,5.8))
 assert x['mapped_inland_water_support'].covers(box(4.2,4.2,5.8,5.8))
control('lake-island-pond-entire-alternating-footprints',nested)
def wrongnest():
 x=m.alternating_support(box(0,0,10,10),{1:[box(0,0,5,10)],2:[box(4,4,8,8)]})
 assert x['hierarchy_disagreements']['L2-outside-L1'].area==12
control('non-nested-water-creates-complete-positive-disagreement',wrongnest)
def exterior():
 x=m.alternating_support(box(-2,-2,2,2),{1:[box(0,0,1,1)]})
 assert x['outside_mapped_L1_context'].area==15 and x['mapped_land_support'].area==1
 assert x['mapped_inland_water_support'].is_empty
control('outside-L1-is-explicit-exterior-not-land',exterior)
def fjord():
 source=Polygon([(0,0),(10,0),(10,10),(6,10),(6,3),(4,3),(4,10),(0,10),(0,0)])
 g=box(3,4,7,8);row,w=m.relation(g,source,5)
 assert row['status']=='checked' and w.area==8 and g.difference(w).area==8
 assert len(w.geoms)==2
control('fjord-complete-two-sided-land-and-exterior-witnesses',fjord)
def holes():
 source=Polygon(box(0,0,10,10).exterior.coords,[box(3,3,7,7).exterior.coords]);g=box(4,4,6,6)
 row,w=m.relation(g,source,1);assert row['status']=='checked' and w.is_empty and row['source_covers_candidate'] is False
control('source-hole-prevents-prepared-covers-false-land',holes)
def covers():
 source=box(0,0,10,10);g=box(1,1,2,2);prepare(source)
 row,w=m.relation(g,source,1);assert row['witness']=='complete-candidate-reconstruction' and w.equals_exact(g,0)
control('prepared-covers-retains-entire-candidate-pointset',covers)
def invalid():
 source=Polygon([(0,0),(2,2),(2,0),(0,2),(0,0)]);row,w=m.relation(box(0,0,2,2),source,9)
 assert row['status']=='unknown' and row['source_id']==9 and w is None
control('invalid-source-keeps-query-ID-unresolved',invalid)
def contact():
 row,w=m.relation(box(0,0,1,1),box(1,0,2,1),2)
 assert w.geom_type=='LineString' and w.area==0 and row['witness_geometry']['type']=='LineString'
control('zero-area-line-contact-keeps-pointset-without-invented-width',contact)
def tiny():
 row,w=m.relation(box(0,0,1,1),box(0.999999999999,0,2,1),2)
 assert row['status']=='checked' and w.area>0 and not w.is_empty
control('tiny-positive-polygon-is-not-suppressed',tiny)
def frame():
 flag=1+(9<<8)+(2<<16);points=[(179000000,0),(181000000,0),(181000000,1000000),(179000000,1000000),(179000000,0)]
 raw=b''.join(struct.pack('>2i',*pt) for pt in points);header=m.HEADER.pack(97,5,flag,179000000,181000000,0,1000000,1,1,-1,-1)
 meta,g=m.decode_record(header,raw,97,0)
 assert meta['declared_range']=='GMT_IS_0_TO_P360_RANGE' and g.bounds==(179.0,0.0,181.0,1.0) and g.area==2
control('dateline-source-explicit-GMT-range-preserves-narrow-ring',frame)
def unclosed():
 pts=[(0,0),(1000000,0),(0,1000000)];raw=b''.join(struct.pack('>2i',*pt) for pt in pts)
 h=m.HEADER.pack(9,3,1+(9<<8),0,1000000,0,1000000,1,1,-1,-1);meta,g=m.decode_record(h,raw,9,0)
 assert g is None and 'unclosed-native-ring-not-implicitly-closed' in meta['geometry_issues']
control('unclosed-native-ring-cannot-be-implicitly-repaired',unclosed)
receipt={'kind':'directed actual source-relative methods; no worldwide execution or physical approval','draft_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'controls_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'passed':passed,'count':len(passed)}
p.with_name('method-controls-result.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(receipt))
from shapely.geometry import MultiPolygon
from shapely.strtree import STRtree

def multipart_query():
 source=[box(-179.5,0,-178.5,1),box(178.5,0,179.5,1),box(0,0,1,1)]
 g=MultiPolygon([box(-179.2,.2,-178.8,.8),box(178.8,.2,179.2,.8)])
 pairs=m.conservative_source_pairs(g,STRtree(source),[11,12,13])
 assert (11,0) in pairs and (12,0) in pairs and all(i!=13 for i,_ in pairs)
control('complete-multipart-query-excludes-only-real-disjoint-part-bboxes',multipart_query)
def hierarchy():
 x=m.full_container_relation(box(179.9,.1,180.1,.9),box(-180.5,0,-179.5,1))
 assert x['status']=='supported' and x['child_periodic_offset']==-360
 y=m.full_container_relation(box(1,1,2,2),box(0,0,1.5,1.5))
 assert y['status']=='unknown' and len(y['whole_member_observations'])==3
control('whole-container-periodic-support-or-explicit-unknown',hierarchy)
receipt.update(draft_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
               controls_sha256=hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
               passed=passed,count=len(passed))
p.with_name('method-controls-result.json').write_text(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps(receipt))

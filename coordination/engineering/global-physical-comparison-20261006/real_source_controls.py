"""Directed real-original record controls; no real candidate or physical verdict."""
import hashlib,importlib.util,json,pathlib,zipfile,numpy as np
from shapely.geometry import Polygon,MultiPolygon,box
from shapely import STRtree
base=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('private_geometry_draft',base/'comparison.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import producer,io
config=json.loads((base/'input-config.json').read_bytes());native=producer.original_native(pathlib.Path.cwd(),config)
expected={int(k):v for k,v in json.loads((base/'control-source-pins.json').read_text()).items()}
sha=hashlib.sha256();sha.update(native)
assert sha.hexdigest()=='af9215d58ebc525b2d09654a89959829f09e6edc457f3666759cded37be4ecf6'
records={};offset=ordinal=0
with io.BytesIO(native) as stream:
  while len(records)<3:
   header=stream.read(44);values=m.HEADER.unpack(header);raw=stream.read(values[1]*8)
   if values[0] in expected:
    e=expected[values[0]];assert hashlib.sha256(header+raw).hexdigest()==e['record_sha256'] and hashlib.sha256(raw).hexdigest()==e['coordinate_bytes_sha256']
    metadata,geometry=m.decode_record(header,raw,ordinal,offset);records[values[0]]=(metadata,geometry,raw)
   offset+=44+len(raw);ordinal+=1
checks=[]
def check(name,value):assert value,name;checks.append({'name':name,'outcome':'PASS'})
a,g,_=records[0]
check('actual-Eurasia-record-first-GMT-M180-to-P270-frame',a['declared_range']=='GMT_IS_M180_TO_P270_RANGE')
check('actual-Eurasia-retains-original-supported-over180-east',180<a['decoded_pointset_bounds'][2]<270)
check('actual-Eurasia-whole-original-supported-polygon-valid',g.is_valid and not a['geometry_issues'])
a,g,_=records[97]
check('actual-dateline-record-original-GMT-0-to360-frame',a['declared_range']=='GMT_IS_0_TO_P360_RANGE')
check('actual-dateline-full-ring-narrow-and-valid',g.is_valid and a['decoded_pointset_bounds'][2]-a['decoded_pointset_bounds'][0]<180)
lo,_,hi,_=g.bounds;y=(g.bounds[1]+g.bounds[3])/2
synthetic=MultiPolygon([box(179.9,y-0.001,179.99,y+0.001),box(-179.99,y-0.001,-179.9,y+0.001)])
pairs=m.conservative_source_pairs(synthetic,STRtree([g]),[97])
check('actual-source-complete-multipart-bbox-queries-both-dateline-frames',(97,0) in pairs and (97,-360) in pairs)
a,g,raw=records[2380]
check('actual-Maine-original-invalid-source-retained',a['id']==2380 and 'invalid-original-source-polygon' in a['geometry_issues'] and not g.is_valid)
native=Polygon(np.frombuffer(raw,dtype='>i4').reshape(-1,2).astype(np.float64));check('actual-invalid-native-integer-pointset-not-introduced-by-GMT-scaling',not native.is_valid)
row,piece=m.relation(box(*g.bounds),g,2380)
check('actual-invalid-original-source-never-inferred-as-land-or-water',row['source_id']==2380 and row['status']=='unknown' and row['issue']=='invalid-complete-source' and piece is None)
receipt={'kind':'directed actual original-source controls; synthetic candidate footprints are controls only, not actual gap classification','checks':checks,'complete_original_native_member_sha256':sha.hexdigest(),'source_records':[records[i][0]for i in sorted(records)],'executed_draft_sha256':hashlib.sha256((base/'comparison.py').read_bytes()).hexdigest(),'controls_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
(base/'real-source-controls-result.json').open('w').write(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n');print(json.dumps({'controls':len(checks),'outcome':'PASS','source_record_ids':sorted(records)}))

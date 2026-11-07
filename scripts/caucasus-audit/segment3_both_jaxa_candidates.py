import json,hashlib
from shapely.geometry import LineString,Point,mapping
from shapely.ops import substring
src=LineString(json.load(open('klukhor-no-connector-full-research.json'))['coordinates']);cut=LineString(json.load(open('jvari-jaxa-cut-research.json'))['coordinates']);a,b=Point(cut.coords[0]),Point(cut.coords[-1]);print('distances to source',src.distance(a),src.distance(b));i,j=src.project(a),src.project(b);pre=substring(src,0,i);post=substring(src,j,src.length);full=LineString(list(pre.coords)+list(cut.coords)[1:]+list(post.coords)[1:]);print('ordered',i<j,'simple',full.is_simple,'endpoint preserved',full.coords[0]==src.coords[0] and full.coords[-1]==src.coords[-1]);
if i>=j or not full.is_simple or src.distance(a)>1e-10 or src.distance(b)>1e-10:raise ValueError('invalid')
data=json.dumps(mapping(full),sort_keys=True,separators=(',',':'),allow_nan=False).encode();open('caucasus-segment3-continuous-jaxa-research.json','wb').write(data);print('hash',hashlib.sha256(data).hexdigest(),'vertices',len(full.coords))

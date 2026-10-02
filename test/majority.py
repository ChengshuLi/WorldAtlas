import sys,pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from majority import canonical,decide,area
from shapely.geometry import box,Polygon
for y in [0,60]:
 location=box(0,y,10,y+1)
 assert decide(location,{'a':[box(0,y,6,y+1)]})['owner']=='a'
 assert decide(location,{'a':[box(0,y,4,y+1)]})['status']=='no-majority'
 assert decide(location,{'a':[box(0,y,5,y+1)],'b':[box(5,y,10,y+1)]})['owner'] is None
 assert decide(location,{'a':[box(0,y,7,y+1)],'b':[box(6,y,10,y+1)]})['status']=='disputed'
 assert decide(location,{'a':[box(0,y,3,y+1),box(3,y,6,y+1)]})['owner']=='a'
location=canonical(Polygon([(179,0),(-179,0),(-179,1),(179,1),(179,0)]))
assert location.area==2 and area(location)<3e10
assert decide(location,{'a':[box(179,0,180,1),box(-180,0,-179.2,1)]})['owner']=='a'
near_half=decide(box(0,0,1,1),{'a':[box(0,0,.50000005,1)]})
assert near_half['owner']=='a' and near_half['share']>.5
tiny=box(0,0,.000001,.000001)
assert decide(tiny,{'a':[tiny]})['owner']=='a'
assert decide(tiny,{'a':[tiny],'b':[tiny]})['status']=='disputed'
print('PASS: WGS84 majority, uncovered denominator, same-owner unions, conflicts and antimeridian')

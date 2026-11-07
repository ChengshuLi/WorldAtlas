import json,math
from shapely.geometry import LineString,box
line=LineString(json.load(open('caucasus-anapa-abin-combined-candidate.json'))['coordinates']);out=[]
for i in range(12):
 a=47+i*.2;b=a+.2;seg=line.intersection(box(a,-90,b,90))
 if seg.is_empty:continue
 lo,bot,hi,top=seg.bounds;out.append({'id':i,'bbox':[round(a-.005,5),round(bot-.02,5),round(b+.005,5),round(top+.02,5)]})
print(json.dumps(out))

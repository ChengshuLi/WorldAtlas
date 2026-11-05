from hydro_overlay import load_archive
from shapely.geometry import box
from pyproj import Geod
A=load_archive('/tmp/ural-hydro-eu.zip','21797d53e0792cae047d25f0c3cfb570c7ef43700ec962b35b2ac92467e29f03',[59.40,61.92,59.52,62.02]);B=load_archive('/tmp/ural-hydro-si.zip','67ea00df7d14a397f8f78e5b1dc31dcca036018ccbcb36e007ce6854b91d71bd',[59.40,61.92,59.52,62.02]);a=next(x[3] for x in A if x[1]==2121045390);b=next(x[3] for x in B if x[1]==3120360000);z=a.intersection(b).intersection(box(59.40,61.92,59.52,62.02));g=Geod(ellps='WGS84');print('type',z.geom_type,'parts',len(z.geoms));
for p in z.geoms:
 if p.geom_type in ('Polygon','MultiPolygon'):print('polygon',p.wkt,'planar area',p.area,'geodesic area',g.geometry_area_perimeter(p)[0])

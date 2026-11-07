"""WGS84 measurement on caller-selected projected source-line geometry."""
import hashlib,json,math
from osgeo import osr
from pyproj import Geod
GEOD=Geod(ellps='WGS84')
METHOD='wgs84-ellipsoidal-geodesic-v1'
GEOMETRY='projected-linear-source-v1'

def coordinate(point):
 if not isinstance(point,(list,tuple)) or len(point)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in point):raise ValueError('invalid coordinate')
 lon,lat=map(float,point)
 if not (-180<=lon<=180 and -90<=lat<=90):raise ValueError('coordinate outside WGS84 bounds')
 return lon,lat

def transformer(epsg):
 geo=osr.SpatialReference();geo.ImportFromEPSG(4326);geo.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
 projected=osr.SpatialReference();projected.ImportFromEPSG(epsg)
 if not projected.IsProjected() or abs(projected.GetLinearUnits()-1)>1e-9:raise ValueError('source-line CRS must be projected in metres')
 projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
 return osr.CoordinateTransformation(geo,projected),osr.CoordinateTransformation(projected,geo)

def geodistance(a,b):
 _,_,d=GEOD.inv(*coordinate(a),*coordinate(b))
 if not math.isfinite(d):raise ValueError('invalid WGS84 inverse')
 return d

def offset_point(point,a,b,offset,forward,reverse):
 if isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset):raise ValueError('invalid offset')
 lon,lat=coordinate(point);ax,ay=forward.TransformPoint(*coordinate(a))[:2];bx,by=forward.TransformPoint(*coordinate(b))[:2];x,y=forward.TransformPoint(lon,lat)[:2]
 dx,dy=bx-ax,by-ay;den=dx*dx+dy*dy
 if not math.isfinite(den) or den<=0:raise ValueError('zero-length source edge')
 t=((x-ax)*dx+(y-ay)*dy)/den
 if not -1e-9<=t<=1+1e-9 or abs(x-(ax+t*dx))>1e-6 or abs(y-(ay+t*dy))>1e-6:raise ValueError('sample is not on specified projected source edge')
 t=max(0.,min(1.,t));q=min(1.,t+1e-6)
 if q==t:q=max(0.,t-1e-6);reverse_direction=True
 else:reverse_direction=False
 target=coordinate(reverse.TransformPoint(ax+q*dx,ay+q*dy)[:2]);azi,_,d=GEOD.inv(lon,lat,*target)
 if not math.isfinite(d) or d<=0:raise ValueError('undefined source-edge tangent')
 if reverse_direction:azi+=180
 if offset==0:return lon,lat
 x2,y2,_=GEOD.fwd(lon,lat,azi-90,offset)
 return coordinate((x2,y2))

def line_sha256(vertices):
 points=[list(coordinate(p)) for p in vertices]
 if len(points)<2:raise ValueError('source line needs at least two coordinates')
 encoded=json.dumps({'type':'LineString','coordinates':points},sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')
 return hashlib.sha256(encoded).hexdigest()

def require_samples(doc,epsg,vertices,section,start,end):
 if not isinstance(doc,dict) or doc.get('type')!='FeatureCollection' or doc.get('distance_method')!=METHOD or doc.get('source_geometry_method')!=GEOMETRY or doc.get('length_approximation')!='sum_of_wgs84_geodesic_chords' or doc.get('geodesic_chord_step_limit_m')!=100.01 or doc.get('projected_epsg')!=epsg or doc.get('source_line_sha256')!=line_sha256(vertices) or doc.get('section')!=section or not isinstance(doc.get('features'),list):raise ValueError('matching WGS84 measured source-line samples required; regenerate stale samples')
 if type(start) is not int or type(end) is not int or not 0<=start<end<len(vertices) or doc.get('start_vertex')!=start or doc.get('end_vertex')!=end:raise ValueError('invalid or mismatched sample section bounds')
 previous=-math.inf;prior_edge=start
 for feature in doc['features']:
  if not isinstance(feature,dict) or feature.get('type')!='Feature' or feature.get('geometry',{}).get('type')!='Point':raise ValueError('invalid sample feature')
  coordinate(feature['geometry'].get('coordinates'))
  p=feature.get('properties',{});idx=p.get('source_edge_index');distance=p.get('distance_along_section_m')
  if p.get('section')!=section or type(idx) is not int or not start<=idx<end or idx<prior_edge or isinstance(distance,bool) or not isinstance(distance,(int,float)) or not math.isfinite(distance) or distance<0 or distance<previous:raise ValueError('invalid sample section or position')
  previous=distance;prior_edge=idx
 return doc['features']

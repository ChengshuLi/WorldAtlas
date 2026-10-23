import json,pathlib,hashlib,zipfile,xml.etree.ElementTree as ET,math
import pyproj,shapely
from shapely.geometry import Polygon,MultiPolygon,Point
from pyproj import Transformer
p=pathlib.Path(__file__).resolve().parent
zpath=p/'Basisdata_0000_Norge_25833_Fylker2022_GML.zip';b=zpath.read_bytes();assert hashlib.sha256(b).hexdigest()=='0162fff92a3354104a5e5380c82836ab50d4f8353de1a2d28f75d8a345746ad7'
g='{http://www.opengis.net/gml/3.2}';s='{http://skjema.geonorge.no/SOSI/produktspesifikasjon/AdmEnheter/4.1}'
features=[]
with zipfile.ZipFile(zpath) as z:
 with z.open('Basisdata_0000_Norge_25833_Fylker2022_GML.gml') as f:
  for _,m in ET.iterparse(f,events=['end']):
   if m.tag!=g+'featureMember':continue
   ft=list(m)[0]
   if ft.tag==s+'Fylke':
    polys=[]
    for patch in ft.iter(g+'PolygonPatch'):
     ringdict={}
     for tag in ['exterior','interior']:
      rings=[]
      for bounds in patch.findall(g+tag):
       pts=[]
       for pl in bounds.iter(g+'posList'):
        vals=list(map(float,pl.text.split()));assert len(vals)%2==0
        seq=list(zip(vals[::2],vals[1::2]));pts.extend(seq[1:] if pts and seq[0]==pts[-1] else seq)
       assert pts[0]==pts[-1];rings.append(pts)
      ringdict[tag]=rings
     assert len(ringdict['exterior'])==1
     polys.append(Polygon(ringdict['exterior'][0],ringdict['interior']))
    poly=MultiPolygon(polys) if len(polys)>1 else polys[0]
    features.append((ft.find(s+'fylkesnummer').text,poly))
   m.clear()
assert len(features)==11
tr=Transformer.from_crs('OGC:CRS84','EPSG:25833',always_xy=True)
old=json.loads((p/'two-center-2022-fylke-comparison.json').read_text());out=[]
for r in old['tested_points']:
 xy=tr.transform(*r['retained_center_lon_lat']);q=Point(xy)
 hits=[n for n,poly in features if poly.covers(q)]
 nearest=min((poly.boundary.distance(q),n) for n,poly in features)
 delta=math.dist(xy,r['transformed_center_epsg25833_metres'])
 out.append({'native_key_xy':r['native_key_xy'],'pyproj_epsg25833':xy,'difference_from_handwritten_transform_m':delta,'shapely_covers_features':hits,'nearest_boundary_m':nearest[0],'nearest_feature':nearest[1]})
result={'source_zip_sha256':hashlib.sha256(b).hexdigest(),'pyproj':pyproj.__version__,'shapely':shapely.__version__,'transform':tr.description,'transform_accuracy_reported_m':tr.accuracy,'all_11_geometry_valid':all(poly.is_valid for _,poly in features),'results':out,'limits':'Independent bounded numerical check of two existing coordinates only; CRS operation accuracy is not source geometry accuracy. No geometry repair, qualification, owner observation or assignment.'}
(p/'independent-numerical-crosscheck.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

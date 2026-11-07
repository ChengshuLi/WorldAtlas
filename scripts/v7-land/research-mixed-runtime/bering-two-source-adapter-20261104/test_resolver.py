import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace
from osgeo import ogr,osr
from pyproj import Transformer
from pyproj.enums import TransformDirection
ROOT=Path(__file__).resolve().parent.parent
PIPE='proj=pipeline step inv proj=aea lat_0=50 lon_0=-154 lat_1=55 lat_2=65 x_0=0 y_0=0 ellps=GRS80 step proj=unitconvert xy_in=rad xy_out=deg'
def pin(p):return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size_bytes':p.stat().st_size}
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT);self.addCleanup(self.tmp.cleanup);self.r=Path(self.tmp.name);self.grid={'width':8,'height':4,'west':-180,'north':90,'step':45};x,y=Transformer.from_pipeline(PIPE).transform(-157.5,67.5,direction=TransformDirection.INVERSE)
  v=self.r/'shp';v.mkdir();ds=ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(v/'epa.shp'));srs=osr.SpatialReference();srs.ImportFromEPSG(3338);l=ds.CreateLayer('epa',srs,ogr.wkbPolygon);l.CreateField(ogr.FieldDefn('CODE',ogr.OFTString));l.CreateField(ogr.FieldDefn('NAME',ogr.OFTString));ring=ogr.Geometry(ogr.wkbLinearRing)
  for a,b in [(x-100,y-100),(x+100,y-100),(x+100,y+100),(x-100,y+100),(x-100,y-100)]:ring.AddPoint_2D(a,b)
  poly=ogr.Geometry(ogr.wkbPolygon);poly.AddGeometry(ring);f=ogr.Feature(l.GetLayerDefn());f.SetField('CODE','2.2.6');f.SetField('NAME','Aleutian Islands');f.SetGeometry(poly);l.CreateFeature(f);f=l=ds=None;z=self.r/'source.zip'
  with zipfile.ZipFile(z,'w') as q:
   for p in v.iterdir():q.write(p,arcname=p.name)
  self.geom={'type':'Polygon','coordinates':[[[-180,40],[-90,40],[-90,89],[-180,89],[-180,40]]]};doc={'type':'FeatureCollection','features':[{'type':'Feature','properties':{'NE_ID':42,'NAME':'ALEUTIAN ISLANDS','FEATURECLA':'Island group','REGION':'North America'},'geometry':self.geom}]};label=self.r/'label.json';label.write_text(json.dumps(doc));self.inputs={'label':pin(label),'ecoregion':pin(z)}
  for k in ('physical_rows','physical_runs','component_rows','component_runs'):
   p=self.r/k;p.write_bytes(b'x');self.inputs[k]=pin(p)
  area={'west':-180,'east':180,'south':-90,'north':90};ops=[{'id':'one','pipeline':PIPE,'area_bounds':area},{'id':'two','pipeline':PIPE,'area_bounds':area}];self.dec={'method':'label_contained_ecoregion_contact_v1','affiliation_id':'bering','entity_id':20,'label':{'source':{'sha256':self.inputs['label']['sha256'],'size_bytes':self.inputs['label']['size_bytes']},'feature':{'source_feature_id':'42','geometry_sha256':'a'*64,'evidence':{'selector_property':'NE_ID'}}},'ecoregion':{'source':{'sha256':self.inputs['ecoregion']['sha256'],'size_bytes':self.inputs['ecoregion']['size_bytes']},'contract':{'layer':'epa','selector_property':'CODE','selector_value':'2.2.6','name_property':'NAME','name_value':'Aleutian Islands','expected_feature_count':1}},'selector':{'pyproj_version':'3.7.1','proj_version':'9.6.0','label_expected_properties':{'NAME':'ALEUTIAN ISLANDS','FEATURECLA':'Island group','REGION':'North America'},'operations':ops,'operation_preference':['two','one'],'operation_manifest_sha256':'b'*64,'partial_root_behavior':'exclude','protected_root_behavior':'exclude','untested_or_boundary_behavior':'exclude','contact_rule':'at_least_one_strictly_inside_center'}}
  self.reader=SimpleNamespace(readrow=lambda a,b,y,w,k:([(0,1,1),(1,2,2),(2,3,3),(3,5,4)] if y==0 and k=='component' else []),equal_coverage=lambda p,c,w:None)
  self.profile=lambda *a:{'rows':[{'component_id_current_generation_only':1,'inside_polygon_cells':1,'outside_polygon_cells':0,'total_land_cells':1},{'component_id_current_generation_only':2,'inside_polygon_cells':1,'outside_polygon_cells':0,'total_land_cells':1},{'component_id_current_generation_only':3,'inside_polygon_cells':1,'outside_polygon_cells':0,'total_land_cells':1},{'component_id_current_generation_only':4,'inside_polygon_cells':1,'outside_polygon_cells':1,'total_land_cells':2}]}
  self.extract=lambda *a:(self.geom,{'source_sha256':self.inputs['label']['sha256']})

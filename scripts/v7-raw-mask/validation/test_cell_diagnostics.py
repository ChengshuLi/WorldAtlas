import contextlib,hashlib,io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from osgeo import gdal,ogr,osr
import cell_diagnostics as diagnostic

def pin(path):return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
class DiagnosticTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);srs=osr.SpatialReference();srs.ImportFromEPSG(4326)
  shp=self.root/'land.shp';self.ds=ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(shp));layer=self.ds.CreateLayer('land',srs=srs,geom_type=ogr.wkbPolygon)
  ring=ogr.Geometry(ogr.wkbLinearRing)
  for x,y in [(-1.5,-1.5),(1.5,-1.5),(1.5,1.5),(-1.5,1.5),(-1.5,-1.5)]:ring.AddPoint_2D(x,y)
  poly=ogr.Geometry(ogr.wkbPolygon);poly.AddGeometry(ring);f=ogr.Feature(layer.GetLayerDefn());f.SetGeometry(poly);layer.CreateFeature(f)
  new=self.root/'new.tif';r=gdal.GetDriverByName('GTiff').Create(str(new),40,40,1,gdal.GDT_Byte);r.SetGeoTransform((-20,1,0,20,0,-1));r.SetSpatialRef(srs);gdal.RasterizeLayer(r,[1],layer,burn_values=[1]);arr=r.ReadAsArray();r=None;self.ds=None
  oldarr=arr.copy();xs=(20,21,24)
  for x in xs:oldarr[20,x]=1-arr[20,x]
  old=self.root/'old.tif';r=gdal.GetDriverByName('GTiff').Create(str(old),40,40,1,gdal.GDT_Byte);r.SetGeoTransform((-20,1,0,20,0,-1));r.SetSpatialRef(srs);r.GetRasterBand(1).WriteArray(oldarr);r=None
  mismatch=self.root/'mismatch.jsonl';mismatch.write_text(''.join(json.dumps({'row':20,'start':x,'end':x+1,'reference':17 if oldarr[20,x] else 1,'candidate':17 if arr[20,x] else 1})+'\n' for x in xs))
  files=[shp.with_suffix(x) for x in ('.shp','.shx','.dbf','.prj')]
  self.config={'grid':{'width':40,'height':40,'west':-20,'north':20,'step':1},'study_bbox':[-1,-1,5,1], 'inputs':{'mismatch':pin(mismatch),'historical_land_mask':pin(old),'new_land_mask':pin(new),'new_land_files':[pin(x) for x in files],'new_land_dataset':str(shp)}}
  self.cp=self.root/'config.json';self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.cp.write_text(json.dumps(self.config))
 def run_diagnostic(self):
  out=io.StringIO()
  with contextlib.redirect_stdout(out):diagnostic.main(self.cp)
  return json.loads(out.getvalue())
 def test_polygon_and_alignment(self):
  report=self.run_diagnostic();self.assertEqual(report['mismatch_cells'],3)
  groups=report['current_polygon_containment'];self.assertEqual(sum(x['count'] for x in groups if x['strictly_inside']),1);self.assertEqual(sum(x['count'] for x in groups if x['touching']),1);self.assertEqual(sum(x['count'] for x in groups if not x['strictly_inside'] and not x['touching']),1)
  shifts=report['study']['integer_shifts'];zero=next(v['differences'] for v in shifts if v['dx']==v['dy']==0);self.assertEqual(zero,3)
  sub=report['study']['subcell_shifts'];self.assertEqual(next(v['differences_from_new_mask'] for v in sub if v['dx']==v['dy']==0),0)
 def test_hash_mismatch_rejected(self):
  self.config['inputs']['historical_land_mask']['sha256']='0'*64;self.save()
  with self.assertRaisesRegex(ValueError,'hash mismatch'):self.run_diagnostic()
 def test_shifted_transform_rejected(self):
  path=self.root/'old.tif';r=gdal.Open(str(path),gdal.GA_Update);r.SetGeoTransform((-19,1,0,20,0,-1));r=None;self.config['inputs']['historical_land_mask']=pin(path);self.save()
  with self.assertRaisesRegex(ValueError,'transform differs'):self.run_diagnostic()
 def test_no_points_in_bbox_rejected(self):
  self.config['study_bbox']=[-19,-19,-18,-18];self.save()
  with self.assertRaisesRegex(ValueError,'contains no mismatch'):self.run_diagnostic()
 def test_span_labels_must_match_masks(self):
  p=self.root/'mismatch.jsonl';rows=[json.loads(line) for line in p.read_text().splitlines()];rows[0]['reference'],rows[0]['candidate']=rows[0]['candidate'],rows[0]['reference'];p.write_text(''.join(json.dumps(row)+'\n' for row in rows));self.config['inputs']['mismatch']=pin(p);self.save()
  with self.assertRaisesRegex(ValueError,'does not match pinned masks'):self.run_diagnostic()
 def test_duplicate_span_rejected(self):
  p=self.root/'mismatch.jsonl';first=p.read_text().splitlines()[0];p.write_text(first+'\n'+first+'\n');self.config['inputs']['mismatch']=pin(p);self.save()
  with self.assertRaisesRegex(ValueError,'overlap or are out of order'):self.run_diagnostic()
 def test_missing_sidecar_and_bad_span_rejected(self):
  self.config['inputs']['new_land_files']=self.config['inputs']['new_land_files'][:-1];self.save()
  with self.assertRaisesRegex(ValueError,'required shapefile sidecar'):self.run_diagnostic()
  self.config['inputs']['new_land_files'].append(pin(self.root/'land.prj'));p=self.root/'mismatch.jsonl';p.write_text(json.dumps({'row':99,'start':0,'end':1,'reference':1,'candidate':17})+'\n');self.config['inputs']['mismatch']=pin(p);self.save()
  with self.assertRaisesRegex(ValueError,'invalid mismatch span'):self.run_diagnostic()
if __name__=='__main__':unittest.main()

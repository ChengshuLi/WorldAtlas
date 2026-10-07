"""Scientific controls and immutable reproduction failure regressions."""
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from shapely.geometry import Polygon, MultiPolygon, box, mapping
from shapely import segmentize
from shapely.geometry.polygon import orient
from pyproj import Geod
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from evidence.geometry import land_area_m2, distance_m, transform_point, ownership_overlap
from evidence.immutable import Baseline, descriptor, canonical_json, deterministic_gzip, validate_source_receipts, write_new_vintage
from evidence.prepare import prepare
from evidence.contracts import source_crs


def analytic(west, south, east, north):
    a, f = 6378137., 1/298.257223563
    e2 = f*(2-f); e = math.sqrt(e2)
    def strip(lat):
        u = math.sin(math.radians(lat))
        return a*a*(1-e2)/2*(u/(1-e2*u*u)+math.atanh(e*u)/e)
    return math.radians(east-west)*(strip(north)-strip(south))


class Geometry(unittest.TestCase):
    def test_native_datum_is_not_silently_relabelled_wgs84(self):
        self.assertEqual(source_crs('EPSG:4326', expected_crs='EPSG:4326').to_epsg(), 4326)
        for native in ('EPSG:4269', 'EPSG:4687'):
            with self.assertRaises(ValueError): source_crs(native, expected_crs='EPSG:4326')
        with self.assertRaises(ValueError): source_crs(None)

    def test_axis_control_and_geodesic_distance(self):
        x,y=transform_point(10,45,'EPSG:3857')
        self.assertAlmostEqual(x,1113194.9079327357,places=5)
        self.assertAlmostEqual(y,5621521.486192066,places=5)
        self.assertAlmostEqual(distance_m((0,0),(1,0)),111319.49079327357,places=5)
        self.assertAlmostEqual(distance_m((179,0),(-179,0)),222638.98158654713,places=5)
        with self.assertRaises(ValueError):distance_m((10,95),(0,0))

    def test_independent_area_high_latitude_holes_and_islands(self):
        for lat in (0,45,80,89.8):
            g=box(10,lat,10.2,lat+.1)
            self.assertTrue(math.isclose(land_area_m2(g),analytic(10,lat,10.2,lat+.1),rel_tol=1e-10))
            second=abs(Geod(ellps='WGS84').geometry_area_perimeter(orient(segmentize(g,.001)))[0])
            self.assertTrue(math.isclose(land_area_m2(g),second,rel_tol=1e-6))
        outer,hole=box(10,50,11,51),box(10.2,50.2,10.8,50.8)
        land=Polygon(outer.exterior.coords,[hole.exterior.coords])
        island=box(12,50,12.1,50.1)
        expected=analytic(10,50,11,51)-analytic(10.2,50.2,10.8,50.8)+analytic(12,50,12.1,50.1)
        self.assertTrue(math.isclose(land_area_m2(MultiPolygon([land,island])),expected,rel_tol=1e-10))
        reversed_island = Polygon(list(island.exterior.coords)[::-1])
        self.assertTrue(math.isclose(land_area_m2(MultiPolygon([land,reversed_island])),expected,rel_tol=1e-10))

    def test_dateline_holes_and_unsupported_poles(self):
        g=Polygon([(179,0),(-179,0),(-179,2),(179,2),(179,0)], [[(179.5,.5),(-179.5,.5),(-179.5,1.5),(179.5,1.5),(179.5,.5)]])
        self.assertTrue(math.isclose(land_area_m2(g),analytic(179,0,181,2)-analytic(179.5,.5,180.5,1.5),rel_tol=1e-10))
        for bad in (box(0,89,1,90),Polygon([(0,0),(1,1),(1,0),(0,1),(0,0)]),MultiPolygon([box(0,0,2,2),box(1,1,3,3)])):
            with self.assertRaises(ValueError):land_area_m2(bad)

    def test_entire_land_denominator_union_conflicts_and_partial_coverage(self):
        land=box(0,0,1,1)
        r=ownership_overlap(land,{'a':[box(0,0,.4,1),box(.2,0,.6,1)]})
        self.assertEqual(r['owner'],'a');self.assertAlmostEqual(r['shares']['a'],.6,places=8)
        self.assertEqual(ownership_overlap(land,{'a':[box(0,0,.4,1)]})['owner'],None)
        self.assertEqual(ownership_overlap(land,{'a':[box(0,0,.5,1)],'b':[box(.5,0,1,1)]})['owner'],None)
        self.assertEqual(ownership_overlap(land,{'a':[box(0,0,.7,1)],'b':[box(.6,0,1,1)]})['status'],'conflicting-claims')
        self.assertEqual(ownership_overlap(land,{})['coverage'],0)


class Preparation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.git=lambda *a:subprocess.check_output(['git','-C',str(self.root),*a],stderr=subprocess.PIPE).decode().strip()
        self.git('config','user.name','Fixture');self.git('config','user.email','fixture@example.com')
        files={'data/world-index.json':{'parts':['geography/part-0.json']},
               'data/geography/part-0.json':{'features':[{'type':'Feature','id':'location-a','properties':{},'geometry':mapping(box(10,40,11,41))}]},
               'release.json':{'release':'fixture'},'hierarchy.json':{'parent':'fixture'},'scope.json':{'ids':['location-a']},'source.json':{'source':'fixture'}}
        self.pins=[]
        for name,value in files.items():
            raw=canonical_json(value);p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);self.pins.append(descriptor(name,raw))
        self.git('add','.');self.git('commit','-qm','Immutable fixture');self.commit=self.git('rev-parse','HEAD')
        self.baseline=Baseline(self.root,self.commit,self.pins)
        self.request={'version':1,'baseline':{'commit':self.commit,'files':self.pins,'pin_files':dict(zip(('release','hierarchy','scope','source_registry'),('release.json','hierarchy.json','scope.json','source.json')))},'subject_ids':['location-a'],'owned_path':'data/regional-review/test-packet/','new_vintage':'run-a','output_filename':'areas.json.gz'}

    def test_actual_part_zero_and_worktree_mutation(self):
        (self.root/'data/geography/part-0.json').write_text('corrupt working tree')
        features,files=self.baseline.subjects(['location-a'])
        self.assertEqual(files['location-a']['path'],'data/geography/part-0.json')
        self.assertNotIn('part',features['location-a']['properties'])
        with self.assertRaises(ValueError):self.baseline.subjects(['missing'])

    def test_two_runs_match_and_originals_never_overwritten(self):
        first=prepare(self.root,self.request);original=(self.root/first['path']).read_bytes()
        second=prepare(self.root,{**self.request,'new_vintage':'run-b'})
        self.assertEqual(original,(self.root/second['path']).read_bytes())
        self.assertEqual(first['sha256'],second['sha256'])
        self.assertEqual(first['uncompressed_sha256'],second['uncompressed_sha256'])
        self.assertEqual(original[4:8],b'\0\0\0\0');self.assertEqual(original[3],0);self.assertEqual(original[9],255)
        with self.assertRaises(FileExistsError):prepare(self.root,self.request)
        self.assertEqual(original,(self.root/first['path']).read_bytes())
        with self.assertRaises(ValueError):write_new_vintage(self.baseline,'data/core/','new','areas.json',{})

    def test_actual_cli_and_changed_commit_require_new_reviewed_pins(self):
        request_file=self.root/'request.json'
        request_file.write_text(json.dumps(self.request))
        cli=Path(__file__).resolve().parents[1]/'scripts/evidence/prepare.py'
        result=json.loads(subprocess.check_output([sys.executable,str(cli),'--repo',str(self.root),'--request',str(request_file)]))
        self.assertEqual(result['hash_kind'],'file-bytes')
        (self.root/'scope.json').write_text('{"ids":["different"]}')
        self.git('add','scope.json');self.git('commit','-qm','Changed scope')
        changed=self.git('rev-parse','HEAD')
        bad={**self.request,'new_vintage':'bad','baseline':{**self.request['baseline'],'commit':changed}}
        request_file.write_text(json.dumps(bad))
        run=subprocess.run([sys.executable,str(cli),'--repo',str(self.root),'--request',str(request_file)],capture_output=True)
        self.assertNotEqual(run.returncode,0)
        self.assertIn(b'hash/size mismatch',run.stderr)
        self.assertFalse((self.root/'data/regional-review/test-packet/vintages/bad').exists())

    def test_actual_cli_admits_destination_before_computation(self):
        request_file = self.root / 'request.json'
        request_file.write_text(json.dumps({**self.request, 'new_vintage': '../../../escaped'}))
        cli = Path(__file__).resolve().parents[1] / 'scripts/evidence/prepare.py'
        run = subprocess.run([sys.executable, str(cli), '--repo', str(self.root), '--request', str(request_file)], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(b'fresh vintage', run.stderr)
        self.assertFalse((self.root / 'data/regional-review').exists())

    def test_bad_input_baseline_scope_source_and_symlink_fail_before_write(self):
        bad=[{**self.pins[0],'sha256':'a'*64},*self.pins[1:]]
        with self.assertRaises(ValueError):prepare(self.root,{**self.request,'baseline':{**self.request['baseline'],'files':bad}})
        self.assertFalse((self.root/'data/regional-review').exists())
        with self.assertRaises(ValueError):Baseline(self.root,'main',self.pins)
        with self.assertRaises(ValueError):prepare(self.root,{**self.request,'baseline':{**self.request['baseline'],'pin_files':{}}})
        registry=[{'id':'s','sha256':self.pins[-1]['sha256']}]
        validate_source_receipts(registry,[{'id':'s','path':'source.json','sha256':self.pins[-1]['sha256']}],self.baseline)
        with self.assertRaises(ValueError):validate_source_receipts(registry,[{'id':'s','path':'source.json','sha256':'b'*64}],self.baseline)
        directory=self.root/'data/regional-review';directory.mkdir();(directory/'test-packet').symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(ValueError):prepare(self.root,self.request)
        self.assertFalse((self.root/'vintages').exists())


if __name__=='__main__':unittest.main()

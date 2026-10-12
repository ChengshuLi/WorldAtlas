"""Exact JSON comparison preserves geometry while accepting wire representation."""
import importlib.util, json, pathlib, sys
ROOT=pathlib.Path.cwd()
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('original_detector',ROOT/'scripts/check-geographic-regression.py')
detector=importlib.util.module_from_spec(spec);spec.loader.exec_module(detector)
from shapely.geometry import Polygon
polygon=Polygon([(0,0),(1,0),(0,1),(0,0)])
feature=detector.report_feature('gained-coverage',polygon,['x'],{}, {'x':polygon},['x'])
wire=json.loads(json.dumps(feature))
assert isinstance(feature['geometry']['coordinates'],tuple)
assert isinstance(wire['geometry']['coordinates'],list)
assert feature != wire
canonical=lambda value: json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
assert canonical(feature)==canonical(wire)
wire['geometry']['coordinates'][0][0][0]=0.001
assert canonical(feature)!=canonical(wire)
print('PASS original Shapely tuple/list wire comparison; altered coordinate rejects; zero omitted fields')

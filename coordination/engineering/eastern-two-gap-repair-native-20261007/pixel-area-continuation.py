"""Exactly two changed source areas using the original unchanged area recipe."""
import hashlib,json,pathlib,sys
import numpy,shapely
from shapely.geometry import shape
ROOT=pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from ellipsoidal_area import area
assert sys.version_info[:2]==(3,12) and shapely.__version__=='2.1.2' and numpy.__version__=='2.3.5'
value=json.load(sys.stdin)
assert set(value['geometries'])=={'atlas:physical:CAN-103:QUE','atlas:physical:CAN-114:NFL'}, 'Complete exact two-target roster required'
assert hashlib.sha256((ROOT/'scripts/ellipsoidal_area.py').read_bytes()).hexdigest()==value['area_algorithm_sha256'], 'Original unchanged area algorithm required'
rows={}
for identity,raw in value['geometries'].items():
 g=shape(raw)
 assert g.is_valid and not g.is_empty, 'Valid nonempty full source geometry required'
 result=area(g)
 assert result>0
 rows[identity]=result
json.dump({'areas':rows,'method':'unchanged ellipsoidal_area.area','runtime':{'python':sys.version,'numpy':numpy.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'executable':sys.executable}},sys.stdout,separators=(',',':'))

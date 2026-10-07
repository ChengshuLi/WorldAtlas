"""Authenticate official N03 2017 source roster/native geometry; no candidate comparisons."""
import hashlib, json, pathlib, zipfile
from collections import Counter
from restore_mlit_source import restore
from mlit_shapefile import iter_features
ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
archive,manifest=restore();z=zipfile.ZipFile(archive)
# The complete ZIP body pin covers all six original members, including the 522 MB
# GML member. Only the native SHP/DBF and exact metadata/PRJ are opened for this
# source census; the large duplicate GML member is not expanded or repackaged.
member_receipts=[{'name':i.filename,'compressed_bytes':i.compress_size,'uncompressed_bytes':i.file_size,'crc32':f'{i.CRC:08x}'} for i in z.infolist()]
prj=z.read('N03-17_170101.prj').decode('ascii')
if 'GCS_JGD_2011' not in prj:raise ValueError('Native PRJ does not identify JGD2011')
meta=z.read('KS-META-N03-17_170101.xml')
shp=z.read('N03-17_170101.shp');dbf=z.read('N03-17_170101.dbf')
features=list(iter_features(z))
code_values=[f['properties'].get('N03_007') for f in features]
if len(features)!=116024:raise ValueError(f'Unexpected complete N03 2017 SHP record count {len(features)}')
if not all(c is None or (isinstance(c,str) and len(c)==5 and c.isdigit()) for c in code_values):raise ValueError('N03_007 contains malformed nonempty code values')
if any(f['geometry_errors'] for f in features):raise ValueError('Original SHP contains a ring/part assembly error; fail closed')
invalid=[]
source={
 'status':'PASS','comparison_performed':False,'archive_sha256':manifest['archive_sha256'],'archive_bytes':manifest['http_content_length'],
 'member_receipts':member_receipts,
 'opened_member_hashes':{'KS-META-N03-17_170101.xml':{'bytes':len(meta),'sha256':sha(meta)},'N03-17_170101.prj':{'bytes':len(prj.encode()),'sha256':sha(prj.encode())},'N03-17_170101.dbf':{'bytes':len(dbf),'sha256':sha(dbf)},'N03-17_170101.shp':{'bytes':len(shp),'sha256':sha(shp)}},
 'native_prj':prj,'source_shape_record_count':len(features),'distinct_N03_007_code_count':len(set(c for c in code_values if c is not None)),'N03_007_code_count_is_unit_count':False,'unit_count_interpretation':'DBF census reports nonempty distinct N03_007 values only; code rows are not assumed equal to municipal units, and 140 rows have blank code.','shape_type':'ESRI Polygon (5)','dbf_record_count':len(features),
 'dbf_code_unique_count':len(set(f['properties'].get('N03_007') for f in features)),
 'dbf_deleted_record_count':sum(bool(f['properties'].get('__deleted__')) for f in features),
 'dbf_blank_N03_007_record_count':sum(c is None for c in code_values),
 'dbf_code_value_widths':sorted(set(len(c) for c in code_values if c is not None)),
 'dbf_duplicate_code_count':sum(1 for c,n in Counter(f['properties'].get('N03_007') for f in features).items() if n>1),
 'source_geometry_invalid_count':None,'source_geometry_invalid_count_limit':'Whole-source validity is not normalized into a roster field; target-relevant source geometries are checked as read in the frozen overlay. Full source ring/part assembly errors: 0.',
 'full_native_source':'The complete official national ZIP byte body is verified. Every polygon in its SHP and DBF is read; coordinates/rings remain native and unedited. No GML member expansion is required because the exact whole original ZIP SHA-256 binds all six archive members.'
}
(ROOT/'receipts/mlit-source-authentication.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:source[k] for k in ('status','source_shape_record_count','distinct_N03_007_code_count','shape_type','dbf_record_count','dbf_duplicate_code_count','dbf_deleted_record_count','dbf_blank_N03_007_record_count','source_geometry_invalid_count')}))

"""Assemble mainland region polygons from selected Neon L2 lines.

This module does not choose a boundary, source, route, root or category. Its
caller must authenticate the pinned combined Neon export and provide a physical
mask closure validator. No historical label grid is read.
"""
import hashlib,json,math,re
from decimal import Decimal,InvalidOperation
from osgeo import ogr
ogr.UseExceptions()

CONSTRUCTION_RELATIONSHIP = "construction_input"


def geometry_hash(g):return hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def coord(v):
 if isinstance(v,bool) or not isinstance(v,(int,float,str,Decimal)):raise ValueError('invalid coordinate')
 try:d=Decimal(str(v))
 except InvalidOperation:raise ValueError('invalid coordinate') from None
 if not d.is_finite():raise ValueError('nonfinite coordinate')
 return d

def points(g):
 if not isinstance(g,dict) or set(g)!={'type','coordinates'} or g['type']!='LineString' or not isinstance(g['coordinates'],list) or len(g['coordinates'])<2:raise ValueError('invalid L2 LineString')
 out=[]
 for p in g['coordinates']:
  if not isinstance(p,list) or len(p)!=2:raise ValueError('invalid coordinate pair')
  x,y=map(coord,p)
  if not (-180<=x<=180 and -90<=y<=90):raise ValueError('coordinate outside CRS84')
  out.append((x,y))
 if any(a==b for a,b in zip(out,out[1:])):raise ValueError('duplicate consecutive vertex')
 if any(abs(a[0]-b[0])>180 for a,b in zip(out,out[1:])):raise ValueError('antimeridian crossing unsupported')
 return out

def assemble(revision_id,records,decision,source_catalog,closure_checker,*,physical_rows_sha256,physical_runs_sha256,checker_sha256,closure_contract_sha256,guard,terminal_checker_sha256=None):
 if not isinstance(revision_id,str) or not revision_id or not isinstance(decision,dict) or set(decision)!={'region_id','revision_id','execution_status','segments','geometry_sha256','geometry_hash_method','witnesses'} or decision['geometry_hash_method']!='binary64-sorted-compact-geojson-v1' or decision['revision_id']!=revision_id or decision['execution_status']!='selected_for_research' or not isinstance(decision['region_id'],str) or not decision['region_id'] or not isinstance(decision['segments'],list) or not decision['segments'] or not callable(closure_checker) or not callable(guard) or any(not re.fullmatch('[0-9a-f]{64}',str(x)) for x in (physical_rows_sha256,physical_runs_sha256,checker_sha256,closure_contract_sha256)):raise ValueError('invalid selected region decision')
 ring=[];trace=[];used=set()
 for item in decision['segments']:
  guard()
  if not isinstance(item,dict) or set(item)!={'kind','id','start','end','reverse'} or item['kind'] not in ('boundary','route') or not isinstance(item['id'],str) or type(item['start']) is not int or type(item['end']) is not int or type(item['reverse']) is not bool:raise ValueError('invalid region segment selection')
  key=(item['kind'],item['id']);record=records.get(key)
  if not isinstance(record,dict) or record.get('revision_id')!=revision_id or record.get('execution_status')!='selected_for_research' or record.get('id')!=item['id'] or record.get('kind')!=item['kind']:raise ValueError('missing, stale or unselected L2 geometry')
  if record.get('geometry_hash_method')!='binary64-sorted-compact-geojson-v1':raise ValueError('unsupported L2 geometry hash method')
  g=record.get('geometry');pts=points(g)
  canon={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in pts]}
  if geometry_hash(canon)!=record.get('geometry_sha256'):raise ValueError('L2 geometry hash mismatch')
  a,b=item['start'],item['end']
  if not 0<=a<b<=len(pts) or b-a<2:raise ValueError('invalid L2 vertex slice')
  citations=[]
  if item['kind']=='boundary':
   refs=record.get('qualified_source_refs');status=record.get('lineage_status')
   if not isinstance(refs,list) or not refs or status not in ('complete','incomplete'):raise ValueError('boundary provenance missing')
   for ref in refs:
    if not isinstance(ref,dict) or set(ref)!={'source_id','version','relationship','role'} or not isinstance(ref['relationship'],str) or not ref['relationship'] or ref['role'] not in ('construction_input','supporting_evidence'):raise ValueError('invalid boundary source citation')
    if ref['role']!=('construction_input' if ref['relationship']==CONSTRUCTION_RELATIONSHIP else 'supporting_evidence'):raise ValueError('unsupported or inconsistent source role')
    source=source_catalog.get((ref['source_id'],ref['version']))
    if not isinstance(source,dict) or source.get('kind')!='raw' or not re.fullmatch('[0-9a-f]{64}',str(source.get('sha256'))) or not source.get('bucket') or not source.get('key'):raise ValueError('boundary citation not a pinned raw source')
    citations.append({'source_id':ref['source_id'],'version':ref['version'],'relationship':ref['relationship'],'role':ref['role'],'sha256':source['sha256'],'bucket':source['bucket'],'key':source['key']})
  else:
   role=record.get('role')
   if role!='water_closure':raise ValueError('route requires physical closure proof')
   refs=record.get('source_refs')
   if not isinstance(refs,list) or not refs:raise ValueError('route source references missing')
   for ref in refs:
    if not isinstance(ref,dict) or set(ref)!={'source_id','version'}:raise ValueError('invalid route source citation')
    source=source_catalog.get((ref['source_id'],ref['version']))
    if not isinstance(source,dict) or source.get('kind')!='raw' or not re.fullmatch('[0-9a-f]{64}',str(source.get('sha256'))) or not source.get('bucket') or not source.get('key'):raise ValueError('route citation not a pinned raw source')
    citations.append({'source_id':ref['source_id'],'version':ref['version'],'sha256':source['sha256'],'bucket':source['bucket'],'key':source['key'],'origin':source.get('origin')})
  selected=pts[a:b];selected=selected[::-1] if item['reverse'] else selected
  if ring and ring[-1]!=selected[0]:raise ValueError('L2 segments do not connect exactly')
  if item['kind']=='route':
   method=record.get('closure_method')
   if method=='physical_water_closure_v1':
    proof=closure_checker(record,selected)
    expected_schema='physical-water-closure-proof-v1'
   elif method=='physical_terminal_closure_v1':
    if not isinstance(terminal_checker_sha256,str) or not re.fullmatch('[0-9a-f]{64}',terminal_checker_sha256):raise ValueError('terminal checker pin missing')
    if a!=0 or b!=len(pts):raise ValueError('terminal closure must use complete route')
    refs=[]
    for side in (('end','start') if item['reverse'] else ('start','end')):
     ref=record.get(side+'_terminal')
     if not isinstance(ref,dict) or set(ref)!={'boundary_id','endpoint'} or ref['endpoint'] not in ('start','end'):raise ValueError('invalid terminal reference')
     boundary=records.get(('boundary',ref['boundary_id']))
     if not isinstance(boundary,dict) or boundary.get('revision_id')!=revision_id or boundary.get('execution_status')!='selected_for_research':raise ValueError('closure terminal boundary is not selected')
     bp=points(boundary.get('geometry'));canonical={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in bp]}
     if geometry_hash(canonical)!=boundary.get('geometry_sha256'):raise ValueError('closure terminal boundary geometry mismatch')
     refs.append({'boundary_id':ref['boundary_id'],'endpoint':ref['endpoint'],'geometry':canonical,'geometry_sha256':boundary['geometry_sha256']})
    if selected[0]!=points(refs[0]['geometry'])[0 if refs[0]['endpoint']=='start' else -1] or selected[-1]!=points(refs[1]['geometry'])[0 if refs[1]['endpoint']=='start' else -1]:raise ValueError('closure endpoint does not match selected boundary')
    proof=closure_checker(record,selected,refs)
    expected_schema='physical-terminal-closure-proof-v1'
    if not isinstance(proof,dict) or proof.get('start_geometry_sha256')!=refs[0]['geometry_sha256'] or proof.get('end_geometry_sha256')!=refs[1]['geometry_sha256'] or proof.get('start_endpoint')!=refs[0]['endpoint'] or proof.get('end_endpoint')!=refs[1]['endpoint'] or proof.get('no_land_land_edge_touched') is not True:raise ValueError('terminal closure proof mismatch')
   else:raise ValueError('unsupported closure method')
   selected_line={'type':'LineString','coordinates':[[float(x),float(y)] for x,y in selected]}
   if not isinstance(proof,dict) or proof.get('schema')!=expected_schema or proof.get('status')!='valid' or proof.get('geometry_sha256')!=geometry_hash(selected_line) or proof.get('physical_rows_sha256')!=physical_rows_sha256 or proof.get('physical_runs_sha256')!=physical_runs_sha256 or proof.get('contract_sha256')!=closure_contract_sha256 or proof.get('checker_sha256')!=(terminal_checker_sha256 if method=='physical_terminal_closure_v1' else checker_sha256):raise ValueError('water closure not validated against geometry, physical mask and checker pins')
  else:proof=None
  ring.extend(selected if not ring else selected[1:]);used.add(key)
  trace.append({'kind':item['kind'],'id':item['id'],'geometry_sha256':record['geometry_sha256'],'start':a,'end':b,'reverse':item['reverse'],'lineage_status':record.get('lineage_status'),'source_citations':citations,'route_provenance':record.get('provenance') if item['kind']=='route' else None,'stored_proof_status':'hash_reference_not_loaded' if item['kind']=='route' else None,'closure_proof':proof})
 if len(ring)<4 or ring[0]!=ring[-1]:raise ValueError('region ring is not explicitly closed')
 if any(abs(a[0]-b[0])>180 for a,b in zip(ring,ring[1:])):raise ValueError('antimeridian crossing unsupported')
 guard();geom={'type':'Polygon','coordinates':[[[float(x),float(y)] for x,y in ring]]};g=ogr.CreateGeometryFromJson(json.dumps(geom))
 if g is None or g.IsEmpty() or not g.IsValid():raise ValueError('invalid assembled region')
 if geometry_hash(geom)!=decision['geometry_sha256']:raise ValueError('region output geometry hash mismatch')
 if not isinstance(decision['witnesses'],list):raise ValueError('invalid region witnesses')
 for w in decision['witnesses']:
  if not isinstance(w,dict) or set(w)!={'lon','lat','inside'} or type(w['inside']) is not bool:raise ValueError('invalid region witness')
  lon,lat=coord(w['lon']),coord(w['lat'])
  if not(-180<=lon<=180 and -90<=lat<=90):raise ValueError('witness outside CRS84')
  p=ogr.Geometry(ogr.wkbPoint);p.AddPoint_2D(float(lon),float(lat))
  if g.Boundary().Intersects(p) or bool(g.Contains(p))!=w['inside']:raise ValueError('region witness fails or touches boundary')
 return geom,{'revision_id':revision_id,'region_id':decision['region_id'],'geometry_sha256':decision['geometry_sha256'],'input_trace':trace,'used_geometry_ids':sorted([list(x) for x in used]),'lineage_limitations':[t['id'] for t in trace if t['lineage_status']=='incomplete'],'method':'selected Neon L2 line and route geometries; explicit ordered concatenation, no geometric repair'}

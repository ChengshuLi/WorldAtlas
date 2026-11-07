"""Disk-backed unseeded-water candidate classifier.

Rows and component summaries are indexed in a fresh SQLite work file. The
source partition and output are streamed. No application-imposed memory cap
is enforced; actual memory use depends on inputs and algorithm workload.
"""
import collections,hashlib,json,math,sqlite3,struct
from functools import cache
from bisect import bisect_right
from pathlib import Path
import numpy as np
import closed_water_core as core
import partition_json_stream
from partition_json_stream import read_partition
from exclusive_outputs import create_directory_exclusive,create_gzip_text_exclusive,write_json_exclusive


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()


def open_database(path):
 db=sqlite3.connect(path);db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
 db.execute('PRAGMA temp_store=FILE');db.execute('PRAGMA foreign_keys=ON')
 db.executescript('''
 CREATE TABLE components(root INTEGER PRIMARY KEY, expected INTEGER NOT NULL, reported_cut INTEGER NOT NULL,
   boundary_mask INTEGER NOT NULL DEFAULT 0, unknown INTEGER NOT NULL DEFAULT 0, crop_edge INTEGER NOT NULL DEFAULT 0,
   cut INTEGER NOT NULL DEFAULT 0, method TEXT, code INTEGER);
 CREATE TABLE spans(y INTEGER NOT NULL, a INTEGER NOT NULL, b INTEGER NOT NULL, root INTEGER NOT NULL REFERENCES components(root),
   PRIMARY KEY(y,a)) WITHOUT ROWID;
 CREATE TABLE mixed(y INTEGER NOT NULL, a INTEGER NOT NULL, b INTEGER NOT NULL, code INTEGER NOT NULL, root INTEGER NOT NULL,
   PRIMARY KEY(y,a)) WITHOUT ROWID;
 ''')
 return db


def ingest_partition(db,path,width,height,snapshot_sha,inputs,revision):
 def insert(c):
  if 'ocean_code' not in c or (c['ocean_code'] is not None and (type(c['ocean_code']) is not int or c['ocean_code'] not in (7,8,9,10))):
   raise ValueError('invalid component ocean code')
  if c['ocean_code'] is not None:return
  root,count,cut=c.get('component_root'),c.get('cell_count'),c.get('source_barrier_contact_edge_count')
  if any(type(x) is not int for x in (root,count,cut)) or not (0<=root<2**32 and count>0 and cut>=0):
   raise ValueError('invalid unseeded component metadata')
  try:db.execute('INSERT INTO components(root,expected,reported_cut) VALUES(?,?,?)',(root,count,cut))
  except sqlite3.IntegrityError as e:raise ValueError('duplicate component root') from e
 meta=read_partition(path,insert)
 if meta.get('schema')!='fresh-ocean-run-partition-v1' or meta.get('grid',{}).get('W')!=width or meta.get('grid',{}).get('H')!=height:
  raise ValueError('partition schema or grid mismatch')
 pin=meta.get('inputs',{})
 if (pin.get('decision_snapshot_sha256')!=snapshot_sha or pin.get('legacy_ocean_label_inheritance') is not False
     or pin.get('decision_revision')!=revision.get('id') or pin.get('entity_revision')!=revision.get('entity_revision')):
  raise ValueError('partition snapshot or historical-label lineage mismatch')
 for key in ('physical_rows_sha256','physical_runs_sha256','prefill_rows_sha256','prefill_runs_sha256','prefill_audit_sha256','source_cut_edges_sha256'):
  if pin.get(key)!=inputs.get(key):raise ValueError(f'partition input mismatch: {key}')
 return meta


def ingest_spans(db,rows_path,spans_path,width,height,meta,batch_size=4096):
 raw=Path(rows_path).read_bytes()
 if len(raw)!=(height+1)*8:raise ValueError('unseeded offset size mismatch')
 offsets=struct.unpack('<%dQ'%(height+1),raw);size=Path(spans_path).stat().st_size
 if offsets[0]!=0 or offsets[-1]*12!=size or any(a>b for a,b in zip(offsets,offsets[1:])):raise ValueError('invalid unseeded offsets')
 batch=[];cells=0
 try:
  with Path(spans_path).open('rb') as f:
   for y in range(height):
    prev=0
    for _ in range(offsets[y+1]-offsets[y]):
     raw=f.read(12)
     if len(raw)!=12:raise ValueError('truncated unseeded span')
     a,b,root=struct.unpack('<III',raw)
     if not (0<=a<b<=width) or a<prev:raise ValueError('invalid or overlapping unseeded span')
     prev=b;cells+=b-a;batch.append((y,a,b,root))
     if len(batch)>=batch_size:db.executemany('INSERT INTO spans VALUES(?,?,?,?)',batch);batch.clear()
   if batch:db.executemany('INSERT INTO spans VALUES(?,?,?,?)',batch)
 except sqlite3.IntegrityError as e:raise ValueError('unseeded spans reference unknown roots or overlap') from e
 if cells!=meta.get('unseeded_cell_count') or offsets[-1]!=meta.get('unseeded_span_count'):
  raise ValueError('partition unseeded totals mismatch')
 db.execute('CREATE INDEX spans_root_y ON spans(root,y,a)')
 # Both the sum and root count must match; no component may be omitted.
 missing=db.execute('''SELECT c.root FROM components c LEFT JOIN (SELECT root,SUM(b-a) n FROM spans GROUP BY root) s
  ON c.root=s.root WHERE s.n IS NULL OR s.n!=c.expected LIMIT 1''').fetchone()
 if missing:raise ValueError(f'unseeded component size mismatch: {missing[0]}')
 return cells,offsets[-1]


def classify_boundaries(db, physical, prefill, width, height, pairs, batch_cells=4096):
    """Sweep sparse RLE spans; classify contacts without expanding cell grids."""
    allowed_water={0,*(w for _,_,w in pairs)}; allowed_land={l for _,l,_ in pairs}
    bits={w:1<<w for _,_,w in pairs};bits.update({l:1<<w for _,l,w in pairs})
    def row_rle(grid,y):
        rows,runs=grid; i,j=int(rows[y]),int(rows[y+1]); ends=runs[2*i:2*j:2]; vals=runs[2*i+1:2*j:2]
        if not len(ends) or int(ends[0])<=0 or int(ends[-1])!=width or np.any(ends[1:]<=ends[:-1]): raise ValueError(f'invalid RLE row {y}')
        return ends,vals
    def load(y):
        if y<0 or y>=height:return None
        pe,pv=row_rle(physical,y);qe,qv=row_rle(prefill,y);i=j=0
        while i<len(pe) and j<len(qe):
            p,q=int(pv[i]),int(qv[j]);end=min(int(pe[i]),int(qe[j]))
            if p not in (1,17) or (p==17 and q not in allowed_land) or (p==1 and q not in allowed_water): raise ValueError(f'invalid physical/prefill relationship at row {y}')
            if int(pe[i])==end:i+=1
            if int(qe[j])==end:j+=1
        if i!=len(pe) or j!=len(qe):raise ValueError('RLE endpoints mismatch')
        spans=db.execute('SELECT a,b,root FROM spans WHERE y=? ORDER BY a',(y,)).fetchall()
        return (pe,pv,qe,qv,spans,[s[0] for s in spans])
    def visit_rle(ends,vals,a,b,fn):
        i=bisect_right(ends,a);x=a
        while x<b:
            end=min(b,int(ends[i]));fn(x,end,int(vals[i]));x=end;i+=1
    def owner(row,x):
        spans,starts=row[4],row[5]; i=bisect_right(starts,x)-1
        return spans[i][2] if i>=0 and x<spans[i][1] else None
    def is_same_root_throughout(row,a,b,root):
        # Adjacent spans can share one root. All cells must be represented.
        spans,starts=row[4],row[5];i=bisect_right(starts,a)-1;x=a
        if i<0 or spans[i][1]<=a:i+=1
        while x<b and i<len(spans):
            sa,sb,sr=spans[i]
            if sa>x or sb<=x or sr!=root:return False
            x=min(b,sb);i+=1
        return x==b
    # Only three neighboring rows are held during this monotonic sweep.
    window={}
    for (y,) in db.execute('SELECT DISTINCT y FROM spans ORDER BY y'):
        window={k:v for k,v in window.items() if y-1<=k<=y+1}
        for yy in (y-1,y,y+1):
            if 0<=yy<height and yy not in window:window[yy]=load(yy)
        current=window[y];updates={}
        for a,b,root in current[4]:
            mask=0;unknown=0;crop=int(y==0 or y==height-1)
            def validate_segment(lo,hi,code):
                if code!=1:raise ValueError('component contains non-residual water')
            visit_rle(current[0],current[1],a,b,validate_segment)
            def validate_prefill(lo,hi,code):
                if code!=0:raise ValueError('component contains non-residual water')
            visit_rle(current[2],current[3],a,b,validate_prefill)
            for x in ((a-1)%width,b%width):
                if owner(current,x)==root:continue
                code=int(current[3][bisect_right(current[2],x)])
                if code==0:unknown=1
                else:mask|=bits[code]
            for ny in (y-1,y+1):
                if not 0<=ny<height:continue
                other=window[ny]
                def add(lo,hi,code):
                    nonlocal mask,unknown
                    if code==0:
                        if not is_same_root_throughout(other,lo,hi,root):unknown=1
                    else:
                        # A matching-root span must always be residual water;
                        # it is checked when that row is swept.
                        mask|=bits[code]
                visit_rle(other[2],other[3],a,b,add)
            m,u,c=updates.get(root,(0,0,0));updates[root]=(m|mask,max(u,unknown),max(c,crop))
        db.executemany('UPDATE components SET boundary_mask=boundary_mask|?,unknown=MAX(unknown,?),crop_edge=MAX(crop_edge,?) WHERE root=?',((m,u,c,r) for r,(m,u,c) in updates.items()))


def mark_cut_contacts(db,path,width,height,batch_size=4096):
 from bisect import bisect_right
 @cache
 def row(y):
  spans=db.execute('SELECT a,b,root FROM spans WHERE y=? ORDER BY a',(y,)).fetchall()
  return ([z[0] for z in spans],spans)
 def owner(y,x):
  starts,spans=row(y);i=bisect_right(starts,x)-1
  return spans[i][2] if i>=0 and x<spans[i][1] else None
 batch=[];prev=None
 with Path(path).open('rb') as f:
  while True:
   raw=f.read(12)
   if not raw:break
   if len(raw)!=12:raise ValueError('truncated barrier edge')
   k,y,x=record=struct.unpack('<III',raw)
   if prev is not None and record<=prev:raise ValueError('barrier edges not unique and sorted')
   prev=record
   if k==0 and y<height and x<width-1:pts=((y,x),(y,x+1))
   elif k==1 and y<height-1 and x<width:pts=((y,x),(y+1,x))
   elif k==2 and y<height and x==0:pts=((y,width-1),(y,0))
   else:raise ValueError('barrier edge outside grid')
   batch.extend((r,) for r in {owner(*pt) for pt in pts}-{None})
   if len(batch)>=batch_size:db.executemany('UPDATE components SET cut=1 WHERE root=?',batch);batch.clear()
 if batch:db.executemany('UPDATE components SET cut=1 WHERE root=?',batch)
 if db.execute('SELECT root FROM components WHERE reported_cut>0 AND cut=0 LIMIT 1').fetchone():
  raise ValueError('independent barrier scan contradicts partition')


def assign_components(db,physical,land,width,height,pairs,tolerance,pad,chunk,pending_file):
 step=360/width;last=-1;pending_cells=assigned_cells=0;pending_count=direct_count=mixed_count=0
 # Page by stable root key to avoid retaining all components or modifying an active cursor.
 cache_key=None;edges=indexes=None
 with create_gzip_text_exclusive(pending_file,encoding='utf8') as pf:
  while True:
   batch=db.execute('SELECT root,expected,reported_cut,boundary_mask,unknown,crop_edge,cut FROM components WHERE root>? ORDER BY root LIMIT 256',(last,)).fetchall()
   if not batch:break
   for root,expected,reported,mask,unknown,crop_edge,cut in batch:
    last=root
    reason=('pending-source-cut-contact' if cut else 'pending-grid-crop-edge' if crop_edge else
            'pending-unknown-zero-boundary' if unknown else 'pending-no-boundary-continent' if not mask else None)
    if reason:
     pf.write(json.dumps({'component_root':root,'reason':reason,'cells':expected},separators=(',',':'))+'\n')
     db.execute('UPDATE components SET method=? WHERE root=?',(reason,root));pending_cells+=expected;pending_count+=1;continue
    participants=[p for p in pairs if mask&(1<<p[2])]
    if not participants or mask!=sum(1<<p[2] for p in participants):raise ValueError('unknown participant boundary mask')
    if len(participants)==1:
     db.execute("UPDATE components SET method='direct',code=? WHERE root=?",(participants[0][2],root))
     assigned_cells+=expected;direct_count+=1;continue
    bbox=db.execute('SELECT MIN(a),MAX(b),MIN(y),MAX(y)+1 FROM spans WHERE root=?',(root,)).fetchone()
    crop=core.shore.crop_bounds(bbox,width,height,step,pad);key=(tuple(crop),tuple(p[1] for p in participants))
    if key!=cache_key:
     # Release the prior tree before constructing a different one.
     edges=indexes=None;cache_key=None
     edges=core.shore.centers_for_crop(physical,land,crop,width,height,step,[p[1] for p in participants])
     indexes=core.shore.make_indexes(edges,participants);cache_key=key
    source=db.execute('SELECT y,a,b FROM spans WHERE root=? ORDER BY y,a',(root,));produced=0;staged=[]
    while True:
     records=source.fetchmany(1024)
     if not records:break
     for y,a,b in records:
      for start in range(a,b,chunk):
       end=min(start+chunk,b);xs=np.arange(start,end,dtype=np.float64)
       codes,_,_=core.shore.classify(np.full(len(xs),90-(y+.5)*step),-180+(xs+.5)*step,crop,width,height,step,participants,tolerance,indexes)
       cuts=np.r_[0,np.flatnonzero(np.diff(codes)!=0)+1,len(codes)]
       for i,j in zip(cuts[:-1],cuts[1:]):
        aa,bb=start+int(i),start+int(j);staged.append((y,aa,bb,int(codes[i]),root));produced+=bb-aa
        if len(staged)>=4096:db.executemany('INSERT INTO mixed VALUES(?,?,?,?,?)',staged);staged.clear()
    if staged:db.executemany('INSERT INTO mixed VALUES(?,?,?,?,?)',staged)
    if produced!=expected:raise ValueError('mixed component cell count mismatch')
    db.execute("UPDATE components SET method='mixed' WHERE root=?",(root,));assigned_cells+=produced;mixed_count+=1
 return {'assigned_cells':assigned_cells,'pending_cells':pending_cells,'pending_components':pending_count,
         'direct_components':direct_count,'mixed_components':mixed_count}


def write_assignments(db,path,decision_id,width,height):
 query='''SELECT s.y,s.a,s.b,c.code,s.root FROM spans s JOIN components c ON c.root=s.root WHERE c.method='direct'
          UNION ALL SELECT y,a,b,code,root FROM mixed ORDER BY 1,2'''
 count=spans=0;last_y=-1;last_end=0;first=True
 with create_gzip_text_exclusive(path,encoding='utf8') as f:
  for y,a,b,code,root in db.execute(query):
   if not (0<=y<height and 0<=a<b<=width and 1<=code<=6) or y<last_y or (y==last_y and a<last_end):
    raise ValueError('invalid or overlapping closed-water output')
   if y!=last_y:
    if last_y>=0:f.write(']}\n')
    f.write('{"row":'+str(y)+',"spans":[');last_y=y;last_end=0;first=True
   if not first:f.write(',')
   rec={'start':a,'end':b,'code':code,'rule_id':'closed-water-policy-v1','member_id':f'{decision_id}-component-{root}'}
   f.write(json.dumps(rec,separators=(',',':')));first=False;last_end=b;count+=b-a;spans+=1
  if last_y>=0:f.write(']}\n')
 return count,spans


def run(snapshot,snapshot_sha,physical,prefill,land,partition_path,component_rows,component_spans,barrier_edges,
        out,width,height,pad,inputs,*,allow_selected_research=False,chunk=5000,verify_inputs=None):
 if chunk<=0 or not math.isfinite(pad) or pad<=0:raise ValueError('invalid chunk or halo')
 decision,pairs,tolerance=core.policy(snapshot,allow_selected_research=allow_selected_research)
 code_paths={'streaming_closed_water':Path(__file__),'partition_json_stream':Path(partition_json_stream.__file__),
             'closed_water_core':Path(core.__file__),'shared_nearest':Path(core.shore.__file__)}
 code_pins={name:sha(path) for name,path in code_paths.items()}
 out=Path(out);create_directory_exclusive(out);db=open_database(out/'work.sqlite3')
 try:
  meta=ingest_partition(db,partition_path,width,height,snapshot_sha,inputs,snapshot['decision_revision'])
  cells,nspans=ingest_spans(db,component_rows,component_spans,width,height,meta)
  classify_boundaries(db,physical,prefill,width,height,pairs)
  mark_cut_contacts(db,barrier_edges,width,height)
  stats=assign_components(db,physical,land,width,height,pairs,tolerance,pad,chunk,out/'pending-components.jsonl.gz')
  count,output_spans=write_assignments(db,out/'closed-water-assignments.jsonl.gz',decision['id'],width,height)
  if count!=stats['assigned_cells'] or count+stats['pending_cells']!=cells:raise ValueError('closed-water cell conservation failed')
  db.commit();db.close();db=None
  if verify_inputs:verify_inputs()
  if any(sha(path)!=code_pins[name] for name,path in code_paths.items()):raise ValueError('algorithm changed during generation')
  manifest={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'partial' if stats['pending_cells'] else 'completed_unverified_candidate_not_published',
    'grid':{'width':width,'height':height,'angular_step_deg':360/width,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},
    'coverage':{'complete':not stats['pending_cells'],'meaning':'classified listed unseeded components; geographic and upstream partition correctness remain unverified'},
    'source':{**inputs,'decision_id':decision['id'],'policy_definition':decision['definition'],'policy_sha256':snapshot_sha,
      'decision_snapshot_sha256':snapshot_sha,'decision_revision':snapshot['decision_revision']['id'],'entity_revision':snapshot['decision_revision']['entity_revision'],'legacy_ocean_label_inheritance':False},
    **stats,'input_span_count':nspans,'span_count':output_spans,
    'pending_file':{'path':'pending-components.jsonl.gz','sha256':sha(out/'pending-components.jsonl.gz')},
    'work_database':{'path':'work.sqlite3','sha256':sha(out/'work.sqlite3'),'purpose':'disk-backed row/component and mixed-output index'},
    'algorithm_parameters':{'classification_chunk':chunk},
    'algorithm_sha256':code_pins['streaming_closed_water'],'code_sha256':code_pins,
    'tiles':[{'core_rows':[0,height],'core_cols':[0,width],'span_file':{'path':'closed-water-assignments.jsonl.gz','sha256':sha(out/'closed-water-assignments.jsonl.gz')}}]}
  write_json_exclusive(out/'manifest.json',manifest,indent=2)
  return manifest
 finally:
  if db is not None:db.close()

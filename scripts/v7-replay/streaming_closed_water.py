"""Disk-backed, bounded-memory unseeded-water candidate classifier.

Rows and component summaries are indexed in a fresh SQLite work file. The
source partition and output are streamed. Memory scales with one grid row,
fixed batches, SQLite cache and the capped shoreline index, not total spans.
"""
import collections,hashlib,json,math,sqlite3,struct
from functools import lru_cache
from pathlib import Path
import numpy as np
import closed_water_core as core
import partition_json_stream
from partition_json_stream import read_partition
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exclusive_outputs import create_directory_exclusive,create_gzip_text_exclusive,write_json_exclusive


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()


def open_database(path,cache_kib):
 if type(cache_kib) is not int or not 1024<=cache_kib<=262144:raise ValueError('invalid SQLite cache limit')
 db=sqlite3.connect(path);db.execute('PRAGMA journal_mode=OFF');db.execute('PRAGMA synchronous=OFF')
 db.execute('PRAGMA temp_store=FILE');db.execute(f'PRAGMA cache_size=-{cache_kib}');db.execute('PRAGMA foreign_keys=ON')
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


def classify_boundaries(db,physical,prefill,width,height,pairs,batch_cells=4096):
    """Batch boundary checks by row; fixed-size point chunks bound memory."""
    water_to_entity={w:e for e,_,w in pairs};land_to_entity={l:e for e,l,_ in pairs}
    entity_to_water={e:w for e,_,w in pairs};water_codes=list(water_to_entity);land_codes=list(land_to_entity)
    bits_by_code=np.zeros(23,dtype=np.uint32)
    for code,entity in {**water_to_entity,**land_to_entity}.items():bits_by_code[code]=1<<entity_to_water[entity]
    @lru_cache(maxsize=3)
    def classes(y):
        p=core.shore.crop(*physical,y,0,width,width);q=core.shore.crop(*prefill,y,0,width,width)
        if np.any(~np.isin(p,[1,17])) or np.any((p==17)&~np.isin(q,land_codes)) or np.any((p==1)&~np.isin(q,[0,*water_codes])):
            raise ValueError(f'invalid physical/prefill relationship at row {y}')
        return p,q
    @lru_cache(maxsize=3)
    def row_index(y):
        rows=db.execute('SELECT a,b,root FROM spans WHERE y=? ORDER BY a',(y,)).fetchall()
        if not rows:return None
        return tuple(np.fromiter((r[i] for r in rows),dtype=np.int64,count=len(rows)) for i in range(3))
    def owners(y,x):
        data=row_index(y)
        if data is None:return np.full(len(x),-1,dtype=np.int64)
        starts,ends,roots=data;ix=np.searchsorted(starts,x,side='right')-1;safe=np.maximum(ix,0)
        return np.where((ix>=0)&(x<ends[safe]),roots[safe],-1)
    for y in range(height):
        data=row_index(y)
        if data is None:continue
        starts,ends,roots=data;p,q=classes(y);updates={};crop=int(y==0 or y==height-1)
        def accumulate(ids,ny,x):
            external=owners(ny,x)!=ids
            if not np.any(external):return
            ids=ids[external];values=classes(ny)[1][x[external]]
            unique,inverse=np.unique(ids,return_inverse=True)
            masks=np.zeros(len(unique),dtype=np.uint32);unknown=np.zeros(len(unique),dtype=bool)
            np.bitwise_or.at(masks,inverse,bits_by_code[values]);np.logical_or.at(unknown,inverse,values==0)
            for root,mask,unk in zip(unique,masks,unknown):
                root=int(root);prior=updates.get(root,(0,0,0))
                updates[root]=(prior[0]|int(mask),max(prior[1],int(unk)),max(prior[2],crop))
        # Horizontal boundary cells only: interiors have the same component root.
        for at in range(0,len(starts),batch_cells):
            sub=slice(at,min(at+batch_cells,len(starts)));ids=roots[sub]
            accumulate(ids,y,(starts[sub]-1)%width);accumulate(ids,y,ends[sub]%width)
            if crop:
                for root in ids:
                    root=int(root);prior=updates.get(root,(0,0,0));updates[root]=(prior[0],prior[1],1)
        coords=[];ids=[];used=0
        def flush():
            nonlocal coords,ids,used
            if not used:return
            xx=np.concatenate(coords);rr=np.concatenate(ids)
            if np.any(p[xx]!=1) or np.any(q[xx]!=0):raise ValueError('component contains non-residual water')
            if y>0:accumulate(rr,y-1,xx)
            if y+1<height:accumulate(rr,y+1,xx)
            coords=[];ids=[];used=0
        for a,b,root in zip(starts,ends,roots):
            a,b,root=int(a),int(b),int(root)
            while a<b:
                take=min(b-a,batch_cells-used)
                coords.append(np.arange(a,a+take,dtype=np.int64));ids.append(np.full(take,root,dtype=np.int64));used+=take;a+=take
                if used==batch_cells:flush()
        flush()
        db.executemany('UPDATE components SET boundary_mask=boundary_mask|?,unknown=MAX(unknown,?),crop_edge=MAX(crop_edge,?) WHERE root=?',
                       ((mask,unknown,crop_edge,root) for root,(mask,unknown,crop_edge) in updates.items()))


def mark_cut_contacts(db,path,width,height,batch_size=4096):
 from bisect import bisect_right
 @lru_cache(maxsize=4)
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


def assign_components(db,physical,land,width,height,pairs,tolerance,pad,max_shore_segments,chunk,pending_file):
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
     edges=core.shore.edges_for_crop(physical,land,crop,width,height,step,[p[1] for p in participants],max_segments=max_shore_segments)
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
        out,width,height,pad,inputs,*,allow_selected_research=False,cache_kib=32768,max_shore_segments=1000000,
        chunk=5000,verify_inputs=None):
 if chunk<=0 or max_shore_segments<=0 or not math.isfinite(pad) or pad<=0:raise ValueError('invalid resource or halo limit')
 decision,pairs,tolerance=core.policy(snapshot,allow_selected_research=allow_selected_research)
 code_paths={'streaming_closed_water':Path(__file__),'partition_json_stream':Path(partition_json_stream.__file__),
             'closed_water_core':Path(core.__file__),'shared_nearest':Path(core.shore.__file__),'spherical_shore':Path(core.shore.geom.__file__)}
 code_pins={name:sha(path) for name,path in code_paths.items()}
 out=Path(out);create_directory_exclusive(out);db=open_database(out/'work.sqlite3',cache_kib)
 try:
  meta=ingest_partition(db,partition_path,width,height,snapshot_sha,inputs,snapshot['decision_revision'])
  cells,nspans=ingest_spans(db,component_rows,component_spans,width,height,meta)
  classify_boundaries(db,physical,prefill,width,height,pairs)
  mark_cut_contacts(db,barrier_edges,width,height)
  stats=assign_components(db,physical,land,width,height,pairs,tolerance,pad,max_shore_segments,chunk,out/'pending-components.jsonl.gz')
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
    'resource_limits':{'sqlite_cache_kib':cache_kib,'shore_segments':max_shore_segments,'classification_chunk':chunk},
    'algorithm_sha256':code_pins['streaming_closed_water'],'code_sha256':code_pins,
    'tiles':[{'core_rows':[0,height],'core_cols':[0,width],'span_file':{'path':'closed-water-assignments.jsonl.gz','sha256':sha(out/'closed-water-assignments.jsonl.gz')}}]}
  write_json_exclusive(out/'manifest.json',manifest,indent=2)
  return manifest
 finally:
  if db is not None:db.close()

"""Streaming RLE writer for authenticated, source-resolved stage-3 claims.

Internal library only: the caller must authenticate Neon/export/source pins,
resolve every selected affiliation from source, validate its List 1 links,
verify stage-2/physical/component provenance, and supply a monitored guard.
No historical/reference labels or changed-cell ledgers are accepted as input.
"""
import ctypes,hashlib,json,os,shutil,struct
from pathlib import Path
from overlay import overlay_row,validate_component_claims
U=struct.Struct('<I');PAIR=struct.Struct('<II');TRIPLE=struct.Struct('<III')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(path,guard):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  while True:
   guard();b=f.read(1<<20)
   if not b:break
   h.update(b)
 return h.hexdigest()
def readrow(rows,runs,y,width,size,kind,previous):
 rows.seek(y*4);raw=rows.read(8);need(len(raw)==8,'truncated row offsets');a,b=struct.unpack('<II',raw);need(a==previous and b>=a and b-a<=width,'invalid row offsets')
 runs.seek(a*size);raw=runs.read((b-a)*size);need(len(raw)==(b-a)*size,'truncated row runs')
 if kind=='physical':
  values=[];start=0
  for end,code in PAIR.iter_unpack(raw):values.append((start,end,code));start=end
  return values,b
 return list((TRIPLE if kind=='component' else PAIR).iter_unpack(raw)),b

def write_streams(*,grid,physical_rows,physical_runs,component_rows,component_runs,baseline_rows,baseline_runs,component_claims,mainland_roots,region_rows,output,guard,disk_reserve_bytes):
 """Write fresh land output and output-only trace; region_rows(y) is trusted code.

 The callback must rasterize authenticated selected geometries, not accept
 externally provided mismatch spans. Every root ID is current-generation only.
 The caller must recheck snapshot, sources, code and all input hashes after this
 routine and before treating its report as accepted.
 """
 need(isinstance(grid,dict) and type(grid.get('width')) is int and type(grid.get('height')) is int and 1<grid['width']<=1000000 and 0<grid['height']<=1000000 and callable(guard) and callable(region_rows) and type(disk_reserve_bytes) is int and disk_reserve_bytes>=2*1024**3,'invalid writer controls')
 width,height=grid['width'],grid['height'];validate_component_claims(component_claims);need(isinstance(mainland_roots,(set,frozenset)) and mainland_roots and all(type(x) is int and 0<=x<0xffffffff for x in mainland_roots) and not (set(component_claims)&mainland_roots),'whole-component claim targets mainland')
 paths=[Path(x).resolve(strict=True) for x in (physical_rows,physical_runs,component_rows,component_runs,baseline_rows,baseline_runs)];out=Path(output).resolve();need(not out.exists() and out.parent.is_dir() and all(not out.is_relative_to(p.parent) and not p.is_relative_to(out) for p in paths),'output exists or overlaps inputs')
 def check(extra=0):
  guard();need(shutil.disk_usage(out.parent).free>=disk_reserve_bytes+extra,'disk reserve reached')
 check(1<<20);out.mkdir(mode=0o700);fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 files=[p.open('rb') for p in paths];counts=[0,0,0];offset=0;stats={};changed_total=0;trace_count=0
 credit=0;outputs=[]
 def charge(n):
  nonlocal credit
  need(type(n) is int and n>=0,'invalid output size')
  if n>credit:
   for f in outputs:f.flush()
   credit=max(1<<20,n);check(credit+(1<<20))
  credit-=n
 try:
  need(all(os.fstat(files[i].fileno()).st_size==(height+1)*4 for i in (0,2,4)),'invalid row-index length');need(all(os.fstat(files[i].fileno()).st_size%n==0 for i,n in ((1,8),(3,12),(5,8))),'invalid run alignment')
  with (out/'rows.u32le').open('xb') as rows,(out/'runs.u32le').open('xb') as runs,(out/'changes.jsonl').open('xb') as trace:
   outputs[:]=[rows,runs,trace]
   charge(4);rows.write(U.pack(0))
   for y in range(height):
    check()
    physical,counts[0]=readrow(files[0],files[1],y,width,8,'physical',counts[0]);components,counts[1]=readrow(files[2],files[3],y,width,12,'component',counts[1]);baseline,counts[2]=readrow(files[4],files[5],y,width,8,'baseline',counts[2])
    def changed(a,b,old,new,affiliations,entries):
     nonlocal changed_total,trace_count
     raw=(json.dumps({'row':y,'start':a,'end':b,'from_code':old,'to_code':new,'affiliation_ids':affiliations,'entry_ids':entries},sort_keys=True,separators=(',',':'))+'\n').encode('utf-8');charge(len(raw));trace.write(raw);changed_total+=b-a;trace_count+=1
    regions=region_rows(y);need(isinstance(regions,list) and all(isinstance(r,dict) and isinstance(r.get('roots'),(set,frozenset)) and not (r['roots']&mainland_roots) for r in regions),'region claim targets mainland')
    pairs=overlay_row(width,physical,baseline,components,component_claims,regions,stats,changed)
    charge(len(pairs)*8+4)
    for end,code in pairs:runs.write(PAIR.pack(end,code))
    offset+=len(pairs);need(offset<=0xffffffff,'output run count exceeds uint32');rows.write(U.pack(offset))
   for f in (rows,runs,trace):f.flush();os.fsync(f.fileno())
  need(all(counts[i]==os.fstat(files[1+2*i].fileno()).st_size//(12 if i==1 else 8) for i in range(3)),'unreferenced trailing runs')
 finally:
  for f in files:f.close()
 fd=os.open(out,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);check()
 return {'schema':'stage3-land-writer-result-v1','status':'pending-caller-validation','grid':grid,'output_rows_sha256':sha(out/'rows.u32le',guard),'output_runs_sha256':sha(out/'runs.u32le',guard),'changes_sha256':sha(out/'changes.jsonl',guard),'changed_cells':changed_total,'change_spans':trace_count,'affiliation_statistics':stats,'limitations':['Resolved claims and region rasterization must be authenticated and rechecked by caller.','Changes are output evidence, never input selectors.','Overlapping same-target affiliations are counted separately in per-affiliation statistics.']}

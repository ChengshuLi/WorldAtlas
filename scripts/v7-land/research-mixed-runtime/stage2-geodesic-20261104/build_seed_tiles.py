#!/usr/bin/env python3
"""Build fresh, bounded tile-run files from the current source-derived seed RLE.

No historical labels/checkpoints or geographic decisions are read. The caller
must independently verify every tile against the selected seed before use.
"""
import hashlib,json,os,resource,struct,time
from pathlib import Path
from write_land_stream import _Rows,_full,PAIR
from verify_inputs import sha_file
REC=struct.Struct('<IIII')

def sync_dir(path):
 fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def build(rows,runs,rows_sha256,runs_sha256,width,height,output,*,tile_size=1024,disk_floor_bytes,buffer_bytes=65536):
 import checkpoints
 rows,runs,out=Path(rows).resolve(),Path(runs).resolve(),Path(output).resolve();code=Path(__file__).resolve();deps=[code,code.with_name('write_land_stream.py'),code.with_name('verify_inputs.py'),code.with_name('checkpoints.py')]
 if (type(width) is not int or type(height) is not int or not 1<=width<=1000000 or not 1<=height<=1000000
     or type(tile_size) is not int or tile_size<1 or type(buffer_bytes) is not int or buffer_bytes<1
     or type(disk_floor_bytes) is not int or disk_floor_bytes<0):raise ValueError('invalid tile build controls')
 nx=(width+tile_size-1)//tile_size;ny=(height+tile_size-1)//tile_size
 soft,_=resource.getrlimit(resource.RLIMIT_NOFILE)
 if nx>2048 or nx*ny>200000 or (soft!=resource.RLIM_INFINITY and nx+32>soft):raise ValueError('tile grid exceeds descriptor or tile bounds')
 if out.exists() or not out.parent.is_dir() or any(out.is_relative_to(p.parent) or p.is_relative_to(out) for p in (rows,runs,code)):raise ValueError('tile output overlaps input/code or already exists')
 guard=lambda:checkpoints.guard(out.parent,disk_floor_bytes);guard()
 before={p.name:sha_file(p,guard) for p in deps}
 if sha_file(rows,guard)!=rows_sha256 or sha_file(runs,guard)!=runs_sha256:raise ValueError('seed input hash mismatch')
 start=time.monotonic();out.mkdir(mode=0o700)
 try:sync_dir(out.parent)
 except OSError as exc:raise RuntimeError('tile directory may exist; durability uncertain, inspect before retry') from exc
 stream=None;open_tiles={};metadata={};current_y=None
 def flush(state):
  guard();buf=state['buffer']
  if buf:state['file'].write(buf);state['sha'].update(buf);buf.clear()
 def close_band():
  for st in open_tiles.values():
   flush(st);st['file'].flush();os.fsync(st['file'].fileno());st['file'].close()
  open_tiles.clear()
 try:
  stream=_Rows(rows,runs,height,PAIR)
  for y in range(height):
   if y%128==0:guard()
   ty=y//tile_size
   if current_y is not None and ty!=current_y:close_band()
   current_y=ty
   for a,b,codevalue in _full(stream.next(),width,{0,17,18,19,20,21,22},'seed'):
    if not codevalue:continue
    while a<b:
     tx=a//tile_size;z=min(b,(tx+1)*tile_size);key=(ty,tx)
     if key not in open_tiles:
      needpath=out/f'{ty:05d}-{tx:05d}.bin';f=open(needpath,'xb');st={'file':f,'buffer':bytearray(),'sha':hashlib.sha256(),'count':0,'mask':0};open_tiles[key]=st;metadata[key]=st
     st=open_tiles[key];st['buffer'].extend(REC.pack(y,a,z,codevalue));st['count']+=1;st['mask']|=1<<(codevalue-17)
     if len(st['buffer'])>=buffer_bytes:flush(st)
     a=z
  stream.finish();close_band()
  if not metadata:raise ValueError('empty seed')
  manifest=out/'manifest.txt'
  with open(manifest,'x') as f:
   for (ty,tx),st in sorted(metadata.items()):
    guard();path=out/f'{ty:05d}-{tx:05d}.bin';digest=st['sha'].hexdigest()
    if path.stat().st_size!=st['count']*REC.size or sha_file(path,guard)!=digest:raise ValueError('tile readback mismatch')
    f.write(f'{ty} {tx} {st["count"]} {st["mask"]} {digest}\n')
   f.flush();os.fsync(f.fileno())
  if sha_file(rows,guard)!=rows_sha256 or sha_file(runs,guard)!=runs_sha256 or {p.name:sha_file(p,guard) for p in deps}!=before:raise ValueError('seed or code changed')
  result={'schema':'stage2-fresh-seed-tiles-v1','status':'intermediate-research-not-independent-verification','seed_rows_sha256':rows_sha256,'seed_runs_sha256':runs_sha256,'width':width,'height':height,'tile_size':tile_size,'tile_count':len(metadata),'manifest_sha256':sha_file(manifest,guard),'code_sha256':before,'elapsed_seconds':time.monotonic()-start,'limitations':'Tiles must be independently verified against the same selected seed before use.'}
  pending=out/'report.pending';final=out/'report.json';linked=False
  try:
   with open(pending,'x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
   guard();os.link(pending,final);linked=True
   sync_dir(out);os.unlink(pending)
   sync_dir(out)
  except Exception as exc:
   if linked or final.exists():raise RuntimeError('tile completion marker may exist; inspect before retry') from exc
   raise
  return result
 finally:
  if stream is not None:stream.close()
  for st in open_tiles.values():st['file'].close()

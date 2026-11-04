#!/usr/bin/env python3
"""Copy verified finished coastal tiles into a new, halo-changed continuation."""
import argparse,fcntl,gzip,hashlib,json,math,shutil,sys
from pathlib import Path
import coastal_band_adaptive as band
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
import exclusive_outputs as xo
sys.path.insert(0,str(HERE.parent/'v7-replay'))
import assemble_coastal_tiles as assembly

NAMES=('physical_rows','physical_runs','land_rows','land_runs','land_report')
METHOD='12 nautical miles inclusive; spherical distance to physical-grid land/water edge; lowest continent code wins ties within 0.00001 metres'
def migrate(old_config,new_config,source,identity_sha,output):
 lock=Path(source).resolve()/'run.lock'
 with lock.open('r+') as handle:
  try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise ValueError('source run is still locked') from None
  return _migrate_locked(old_config,new_config,source,identity_sha,output)

def _migrate_locked(old_config,new_config,source,identity_sha,output):
 migration_code_sha=band.sha(Path(__file__).resolve())
 old_config=Path(old_config).resolve();new_config=Path(new_config).resolve();oldraw=old_config.read_bytes();newraw=new_config.read_bytes();old=json.loads(oldraw);new=json.loads(newraw);source=Path(source).resolve();out=Path(output).resolve()
 if (old.get('schema')!='simple-v2-coastal-resumable-v1' or {k:v for k,v in old.items() if k!='pad_degrees'}!={k:v for k,v in new.items() if k!='pad_degrees'} or old.get('pad_degrees')==new.get('pad_degrees') or any(type(c.get('pad_degrees')) not in (int,float) or not math.isfinite(c['pad_degrees']) or c['pad_degrees']<=0 for c in (old,new))):raise ValueError('only an explicit halo change is supported')
 if any(out==p or p.is_relative_to(out) or out.is_relative_to(p) for p in (source,old_config.parent,new_config.parent,HERE)):raise ValueError('output overlaps input directories')
 ident_path=source/'identity.json';ident=band.pin({'path':str(ident_path),'sha256':identity_sha});identity=json.loads(ident.read_bytes())
 if identity.get('schema')!='simple-v2-coastal-resumable-identity-v1' or identity.get('config_sha256')!=hashlib.sha256(oldraw).hexdigest() or (source/'report.json').exists():raise ValueError('source identity or partial status mismatch')
 code_paths={'runner':HERE/'build_coastal_resumable.py','coastal_band':Path(band.__file__).resolve(),'core':Path(band.core.__file__).resolve(),'shore':Path(band.core.shore.__file__).resolve(),'geometry':Path(band.core.shore.geom.__file__).resolve(),'grid_io':Path(band.grid_io.__file__).resolve(),'output_io':Path(xo.__file__).resolve(),'coverage_io':Path(assembly.__file__).resolve()}
 code=identity.get('code_sha256',{})
 if any(code.get(k)!=band.sha(p) for k,p in code_paths.items()):raise ValueError('source code identity mismatch')
 tile_code={k:code[k] for k in ('coastal_band','core','shore','geometry','grid_io','output_io')};pins={k:band.pin(old[k]) for k in NAMES}
 g=old['grid'];w,h=g['width'],g['height'];tw,th=old['tile_width'],old['tile_height'];nx=math.ceil(w/tw);reserve=old.get('minimum_free_bytes',2*(1<<30))
 if any(out==p or p.is_relative_to(out) or out.is_relative_to(p.parent) for p in [*pins.values(),*code_paths.values()]):raise ValueError('output overlaps input or code')
 if shutil.disk_usage(out.parent).free<reserve:raise ValueError('free disk below configured reserve')
 if out.exists():raise ValueError('output must be new')
 reports=sorted((source/'tiles').glob('*/attempt-*/report.json'))
 if not reports:raise ValueError('no completed source tiles')
 xo.create_directory_exclusive(out);(out/'configs').mkdir(mode=0o700);(out/'tiles').mkdir(mode=0o700);records={}
 for rp in reports:
  idx=int(rp.parent.parent.name)
  if idx in map(int,records):raise ValueError('duplicate source tile')
  x=(idx%nx)*tw;y=(idx//nx)*th;box=[x,min(w,x+tw),y,min(h,y+th)]
  if y>=h:raise ValueError('tile outside grid')
  cp=source/'configs'/f'{idx:06d}.json';cfg=json.loads(cp.read_bytes());m=json.loads(rp.read_bytes());ch=band.sha(cp)
  expected={'schema':'simple-v2-coastal-band-v1','grid':g,**{k:old[k] for k in NAMES},'core':box,'pad_degrees':old['pad_degrees'],'chunk':old.get('chunk',5000),'max_shore_segments':old.get('max_shore_segments',1000000),'minimum_free_bytes':reserve}
  if (cfg!=expected or m.get('schema')!='simple-v2-coastal-tile-report-v1' or m.get('status')!='research-partial-not-published' or m.get('config_sha256')!=ch or m.get('grid')!=g or m.get('core')!=box or m.get('inputs')!={k:old[k] for k in NAMES} or m.get('code_sha256')!=tile_code or m.get('method')!=METHOD or m.get('crop')!=list(band.adaptive_crop(box,w,h,g['step'],old['pad_degrees']))):raise ValueError('source tile lineage mismatch')
  span=(rp.parent/m['span_file']['path']).resolve()
  if m['span_file']['path']!='coastal-spans.jsonl.gz' or not span.is_relative_to(rp.parent) or band.sha(span)!=m['span_file']['sha256']:raise ValueError('source span mismatch')
  n=ns=0;last_y=box[2]-1
  with gzip.open(span,'rt',encoding='utf8') as f:
   for line in f:
    row=json.loads(line);yy=row.get('row');spans=row.get('spans')
    if type(yy) is not int or not last_y<yy<box[3] or not isinstance(spans,list) or not spans:raise ValueError('invalid span row')
    last_y=yy;end=box[0]
    for q in spans:
     if not isinstance(q,dict) or set(q)!={'start','end','code'} or any(type(q[k]) is not int for k in q) or not end<=q['start']<q['end']<=box[1] or q['code'] not in range(1,7):raise ValueError('invalid span')
     n+=q['end']-q['start'];ns+=1;end=q['end']
  if n!=m.get('assigned_cells') or ns!=m.get('span_count'):raise ValueError('span totals mismatch')
  td=out/'tiles'/f'{idx:06d}'/'attempt-0001';td.mkdir(parents=True,mode=0o700);dstcp=out/'configs'/cp.name;dstrp=td/'report.json';dstspan=td/span.name
  rh=band.sha(rp);sh=band.sha(span)
  for a,b,digest in ((cp,dstcp,ch),(rp,dstrp,rh),(span,dstspan,sh)):
   shutil.copyfile(a,b)
   if band.sha(a)!=digest or band.sha(b)!=digest:raise ValueError('source or copy changed')
  records[str(idx)]={'config_sha256':ch,'report_sha256':rh,'span_sha256':sh}
  if shutil.disk_usage(out).free<reserve:raise ValueError('free disk below configured reserve')
 for k in NAMES:band.pin(old[k])
 if band.sha(ident_path)!=identity_sha or band.sha(Path(__file__).resolve())!=migration_code_sha or old_config.read_bytes()!=oldraw or new_config.read_bytes()!=newraw or any(code[k]!=band.sha(p) for k,p in code_paths.items()):raise ValueError('input or code changed')
 manifest={'schema':'simple-v2-coastal-migration-v1','migration_code_sha256':migration_code_sha,'old_identity_sha256':identity_sha,'old_config_sha256':hashlib.sha256(oldraw).hexdigest(),'new_config_sha256':hashlib.sha256(newraw).hexdigest(),'old_pad_degrees':old['pad_degrees'],'new_pad_degrees':new['pad_degrees'],'tile_count':len(records),'tiles':records,'method':'Copy only completed, hash-verified source tiles using the unchanged coastal engine; each tile retains its original config and successful omitted-shore certificate. New tiles use the new halo and the same certificate. This is not historical proof.'}
 xo.write_json_exclusive(out/'migration.json',manifest,indent=2);return manifest
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('old_config');p.add_argument('new_config');p.add_argument('source');p.add_argument('identity_sha');p.add_argument('output');a=p.parse_args()
 try:print(json.dumps(migrate(a.old_config,a.new_config,a.source,a.identity_sha,a.output),indent=2))
 except Exception as e:print('error: '+str(e),file=sys.stderr);raise SystemExit(1)

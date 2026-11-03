#!/usr/bin/env python3
"""Read-only V6 global continental-water/coastal-support consistency audit.

Uses only published V6 land assignments plus the physical mask. It does not
replay any earlier land candidate and does not write/change V2 or V6. Ordinary
coastal-water candidates are exact nearest-assigned-shore results inside the
22.224 km band. Out-of-band current continental-water cells are counted as
unsupported generic-ocean-default cases; the ocean basin destination is left
for the named-ocean assignment layer.
"""
import argparse,gzip,hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import distance_transform_edt
AUD=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'audit'))
from spherical_shore import edge_data,nearest,unit,R
W,H=131072,54614; STEP=360.0/W; BAND=22224.0
V6=Path('/tmp/v6-aegean-final-publication-20261103/final-candidate-grid-root-approved-v3')
PH=Path('/tmp/worldatlas-v5-recovery/raw')
EXC=ROOT/'output/v6-satellite-final-20261102/data/exception-spans'
TY=3600; TX=7200; Y85=int(math.ceil(5/STEP)); PADY=int(math.ceil((BAND+1500)/(111195.0*STEP)))+4
ALGORITHM_REVISION='v2_exact_inband_mismatch_checks'

def rss_mib():
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmRSS:'):return int(line.split()[1])/1024
 except Exception:pass
 return -1.0

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def exception_manifest():
 files=sorted(EXC.glob('*.json'));h=hashlib.sha256()
 for fp in files:
  digest=sha(fp);h.update(fp.name.encode());h.update(b'\0');h.update(digest.encode());h.update(b'\n')
 return h.hexdigest(),len(files),max((fp.stat().st_mtime for fp in files),default=0.0)

def expand_row(rows,runs,y):
 a,b=int(rows[y]),int(rows[y+1]); r=runs[2*a:2*b].reshape(-1,2)
 ends=r[:,0].astype(np.int64,copy=False); vals=r[:,1].astype(np.uint8,copy=False)
 starts=np.empty_like(ends); starts[0]=0; starts[1:]=ends[:-1]
 if int(ends[-1])!=W: raise ValueError(f'row {y} ends at {ends[-1]}')
 return np.repeat(vals,ends-starts)

def crop(rows,runs,y,x0,x1):
 """RLE crop with cyclic longitude, preserving unwrapped x for geometry."""
 width=x1-x0
 if width>=W:
  return expand_row(rows,runs,y)
 a=np.empty(width,np.uint8); cur=0; x=x0
 while x<x1:
  xm=x%W; take=min(x1-x,W-xm)
  first,last=int(rows[y]),int(rows[y+1]); ends=runs[2*first:2*last:2]; vals=runs[2*first+1:2*last:2]
  i=int(np.searchsorted(ends,xm,side='right')); xx=xm; local=cur
  stop=xm+take
  while xx<stop:
   e=min(int(ends[i]),stop); a[local:local+(e-xx)]=int(vals[i]);local+=e-xx;xx=e;i+=1
  cur+=take;x+=take
 return a

def extract_edges(phys,labels,x0,y0,include_dateline=False):
 h,w=phys.shape; parts=[]; cols=np.arange(x0,x0+w,dtype=np.float64); lon0=-180+cols*STEP;lon1=lon0+STEP
 for iy in range(h):
  y=y0+iy; dry=(phys[iy]==17)&(labels[iy]>=17)&(labels[iy]<=22)
  if dry.any():
   c=(labels[iy]-16).astype(np.uint8)
   for edge in (1,-1):
    m=np.zeros(w,bool)
    if edge==1:m[1:]=dry[1:]&(phys[iy,:-1]==1)
    else:m[:-1]=dry[:-1]&(phys[iy,1:]==1)
    ix=np.flatnonzero(m)
    if len(ix):
     lo=-180+(x0+ix)*STEP+(0 if edge==1 else STEP);top=90-y*STEP;bot=top-STEP
     parts.append((np.full(len(ix),top),lo,np.full(len(ix),bot),lo,np.zeros(len(ix),np.uint8),c[ix]))
   if include_dateline and w==W:
    # Explicitly include vertical coastline at the longitude wrap.
    if dry[0] and phys[iy,-1]==1:
     lo=-180.0; top=90-y*STEP; bot=top-STEP
     parts.append((np.array([top]),np.array([lo]),np.array([bot]),np.array([lo]),np.zeros(1,np.uint8),np.array([c[0]],np.uint8)))
    if dry[-1] and phys[iy,0]==1:
     lo=180.0; top=90-y*STEP; bot=top-STEP
     parts.append((np.array([top]),np.array([lo]),np.array([bot]),np.array([lo]),np.zeros(1,np.uint8),np.array([c[-1]],np.uint8)))
  if iy>0:
   for mask,cats in (((phys[iy-1]==17)&(phys[iy]==1),(labels[iy-1]-16).astype(np.uint8)),
                     ((phys[iy-1]==1)&(phys[iy]==17),(labels[iy]-16).astype(np.uint8))):
    ix=np.flatnonzero(mask)
    if len(ix):
     lat=90-y*STEP; lo=-180+(x0+ix)*STEP
     parts.append((np.full(len(ix),lat),lo,np.full(len(ix),lat),lo+STEP,np.ones(len(ix),np.uint8),cats[ix]))
 return edge_data(parts)

def get_exception_index():
 by={}; total=0
 for fp in EXC.glob('*.json'):
  d=json.load(open(fp)); mid=d['member_id']; kind=('enclosed-pocket' if mid.startswith('enclosed-ocean-pocket-') else ('named-seavox' if mid.startswith('seavox-v19-mrgid-') else ('ordinary-water' if mid.startswith('ordinary-') else 'other-exception')))
  for s in d['spans']:
   by.setdefault(int(s['row']),[]).append((int(s['start']),int(s['end']),kind));total+=1
 for y in by: by[y].sort()
 return by,total

def exc_masks(row,x0,x1,idx):
 w=x1-x0; masks={k:np.zeros(w,bool) for k in ('all','enclosed-pocket','named-seavox','ordinary-water','other-exception')}
 for a,b,k in idx.get(row,()):
  lo=max(a,x0);hi=min(b,x1)
  if lo<hi:
   masks['all'][lo-x0:hi-x0]=True;masks[k][lo-x0:hi-x0]=True
 return masks

def spans(xs):
 if len(xs)==0:return []
 a=np.asarray(sorted(set(map(int,xs))),dtype=np.int64); cuts=np.flatnonzero(np.diff(a)>1)
 st=np.r_[0,cuts+1]; en=np.r_[cuts+1,len(a)]
 return [(int(a[i]),int(a[j-1])+1) for i,j in zip(st,en)]

def coarse_certificates(points,src,tree,edges,maxhalf,k=16):
 """Return cells whose current donor/support can be certified without exact work.

 Segment-midpoint distances plus/minus each segment half-length are rigorous
 spherical lower/upper bounds. The k-th midpoint minus global max-half bounds
 every unqueried segment. Only class/distance ambiguity reaches exact checks.
 """
 n=len(points); q=min(k,len(edges['mids']))
 chord,idx=tree.query(points,k=q,workers=-1)
 if q==1:chord=chord[:,None];idx=idx[:,None]
 mid=2*R*np.arcsin(np.clip(chord/2,0,1));cats=edges['category'][idx];half=edges['half_lengths'][idx]
 lo=np.maximum(0.0,mid-half);hi=mid+half
 unseen=np.maximum(0.0,mid[:,-1]-maxhalf)
 cert_same=np.zeros(n,bool);cert_inband=np.zeros(n,bool);cert_outband=np.zeros(n,bool)
 all_lower=np.minimum(lo.min(axis=1),unseen)
 cert_outband=all_lower>BAND+1e-6
 for c in range(1,7):
  rows=np.flatnonzero(src==c)
  if not len(rows):continue
  mask=(cats[rows]==c);has=mask.any(axis=1)
  curr_hi=np.full(len(rows),np.inf);curr_hi[has]=(np.where(mask[has],hi[rows][has],np.inf)).min(axis=1)
  other_mask=cats[rows]!=c
  other_lo=np.full(len(rows),np.inf);hasother=other_mask.any(axis=1)
  other_lo[hasother]=(np.where(other_mask[hasother],lo[rows][hasother],np.inf)).min(axis=1)
  # Any unqueried segment may be another category, so include its conservative lower bound.
  other_lo=np.minimum(other_lo,unseen[rows])
  same=has&(curr_hi+1e-5<other_lo)
  cert_same[rows]=same
  cert_inband[rows]=same&(curr_hi<=BAND+1e-6)
 return cert_same,cert_inband,cert_outband

def census(pr,pu,vr,vu,exidx,t0):
 main_water=set();main_coast=set();polar_water=0;polar_coast_rows=0
 total_water={i:0 for i in range(1,7)};tilewater={};exception_tilewater={};exception_polarwater={};prevp=None
 for y in range(H):
  p=expand_row(pr,pu,y);lab=expand_row(vr,vu,y);wm=(p==1)&(lab>=1)&(lab<=6)
  if np.any(wm):
   xs=np.flatnonzero(wm);codes=lab[xs]
   for c,n in zip(*np.unique(codes,return_counts=True)):total_water[int(c)]+=int(n)
   if y<Y85:polar_water+=int(len(xs))
   else:
    by=(y-Y85)//TY
    for tx in np.unique(xs//TX):main_water.add((by,int(tx)))
    txs=xs//TX
    for tx in np.unique(txs):
     sel=txs==tx
     for c,n in zip(*np.unique(codes[sel],return_counts=True)):
      tilewater[(by,int(tx),int(c))]=tilewater.get((by,int(tx),int(c)),0)+int(n)
  if y in exidx:
   masks=exc_masks(y,0,W,exidx)
   if y<Y85:
    for kind,mask in masks.items():
     for c in range(1,7):
      n=int(np.count_nonzero(mask&(p==1)&(lab==c)))
      if n:exception_polarwater[(kind,c)]=exception_polarwater.get((kind,c),0)+n
   else:
    by=(y-Y85)//TY
    for tx in range((W+TX-1)//TX):
     a=tx*TX;b=min(W,a+TX)
     for kind,mask in masks.items():
      sl=mask[a:b]&(p[a:b]==1)
      if not np.any(sl):continue
      for c in range(1,7):
       n=int(np.count_nonzero(sl&(lab[a:b]==c)))
       if n:exception_tilewater[(by,tx,c,kind)]=exception_tilewater.get((by,tx,c,kind),0)+n
  if y>=Y85-PADY:
   land=p==17;water=p==1;by=max(0,(y-Y85)//TY)
   wx=np.flatnonzero(land&(np.roll(water,1)|np.roll(water,-1)))
   if prevp is not None:
    wx2=np.flatnonzero(((prevp==17)&water)|((prevp==1)&land));wx=np.unique(np.r_[wx,wx2])
   if len(wx):
    for tx in np.unique(wx//TX):main_coast.add((by,int(tx)))
  elif np.any((p==17)&(np.roll(p==1,1)|np.roll(p==1,-1))):polar_coast_rows+=1
  prevp=p
  if (y+1)%10000==0:print(f'occupancy prepass row {y+1}/{H}; {len(main_water):,} water tiles, {len(main_coast):,} coast tiles; {time.time()-t0:.1f}s',flush=True)
 return main_water,main_coast,polar_water,polar_coast_rows,total_water,tilewater,exception_tilewater,exception_polarwater

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True,help='new isolated directory under this audit folder');ap.add_argument('--resume',action='store_true',help='explicitly resume an active run with matching manifest');args=ap.parse_args()
 run_dir=Path(args.run_dir).resolve()
 if not run_dir.is_relative_to(AUD.resolve()):raise ValueError('run directory must remain under this audit folder')
 if run_dir.exists() and not args.resume:raise FileExistsError(f'run directory already exists; use --resume only for the same active manifest: {run_dir}')
 if not run_dir.exists():
  if args.resume:raise FileNotFoundError(f'cannot resume missing run directory: {run_dir}')
  run_dir.mkdir(parents=True)
 start_time=time.time(); print('Pinning V6 and physical inputs',flush=True)
 vrp=V6/'rows.u32le';vup=V6/'runs.u32le';prp=PH/'physical-rows.u32';pup=PH/'physical-runs.u32'
 vr=np.memmap(vrp,dtype='<u4',mode='r');vu=np.memmap(vup,dtype='<u4',mode='r');pr=np.memmap(prp,dtype='<u4',mode='r');pu=np.memmap(pup,dtype='<u4',mode='r')
 exidx,exspans=get_exception_index();ex_manifest_sha,ex_file_count,ex_newest_mtime=exception_manifest();print(f'Loaded {exspans:,} exception spans in {ex_file_count} files; manifest {ex_manifest_sha}; grid H={H} Y85={Y85} PADY={PADY}',flush=True)
 run_manifest_path=run_dir/'run-manifest.json';run_inputs={'v6_rows_sha256':sha(vrp),'v6_runs_sha256':sha(vup),'physical_rows_sha256':sha(prp),'physical_runs_sha256':sha(pup),'physical_mask_sha256':'660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017','exception_manifest_sha256':ex_manifest_sha,'exception_file_count':ex_file_count,'algorithm_sha256':sha(Path(__file__))}
 if args.resume:
  if not run_manifest_path.exists():raise ValueError('explicit resume requires an existing run-manifest.json')
  existing=json.load(open(run_manifest_path))
  if existing.get('status')!='active' or existing.get('inputs')!=run_inputs:raise ValueError('resume manifest status or input fingerprints differ')
 else:
  if run_manifest_path.exists():raise FileExistsError('new run directory unexpectedly already has a manifest')
  run_manifest_path.write_text(json.dumps({'status':'active','inputs':run_inputs,'run_dir':str(run_dir)},indent=2)+'\n')
 # Reuse the exact row census on reruns; source hashes bind it to this V6/physical pair.
 cache=AUD/'occupancy-census-cache.json'; key={'v6_rows_sha256':sha(vrp),'v6_runs_sha256':sha(vup),'physical_rows_sha256':sha(prp),'physical_runs_sha256':sha(pup),'exception_manifest_sha256':ex_manifest_sha,'exception_file_count':ex_file_count}
 if cache.exists():
  c=json.load(open(cache))
  if c.get('inputs')!=key:
   old=c.get('inputs',{});grid_keys=('v6_rows_sha256','v6_runs_sha256','physical_rows_sha256','physical_runs_sha256')
   old_grid_matches=all(old.get(k)==key[k] for k in grid_keys)
   files_precede_cache=all(fp.stat().st_mtime<=cache.stat().st_mtime for fp in EXC.glob('*.json'))
   if old_grid_matches and 'exception_manifest_sha256' not in old and files_precede_cache:
    c['inputs']=key;cache.write_text(json.dumps(c,separators=(',',':'))+'\n');print('Bound legacy census exception counts to unchanged pre-cache exception manifest',flush=True)
   else:raise ValueError('occupancy cache input hashes differ; remove only this audit cache before retry')
  main_water={tuple(z) for z in c['main_water']};main_coast={tuple(z) for z in c['main_coast']};polar_water=int(c['polar_water']);polar_coast_rows=int(c['polar_coast_rows'])
  total_water={int(k):int(v) for k,v in c['total_water'].items()};tilewater={tuple(map(int,k.split(','))):int(v) for k,v in c['tilewater'].items()}
  exception_tilewater={tuple([int(a),int(b),int(cc),kind]):int(v) for k,v in c['exception_tilewater'].items() for a,b,cc,kind in [k.split(',')]}
  exception_polarwater={(kind,int(cc)):int(v) for k,v in c['exception_polarwater'].items() for kind,cc in [k.split(',')]}
  print(f'Reused occupancy census cache from {cache}',flush=True)
 else:
  main_water,main_coast,polar_water,polar_coast_rows,total_water,tilewater,exception_tilewater,exception_polarwater=census(pr,pu,vr,vu,exidx,start_time)
  payload={'inputs':key,'main_water':[list(z) for z in sorted(main_water)],'main_coast':[list(z) for z in sorted(main_coast)],'polar_water':polar_water,'polar_coast_rows':polar_coast_rows,'total_water':{str(k):v for k,v in total_water.items()},'tilewater':{','.join(map(str,k)):v for k,v in tilewater.items()},'exception_tilewater':{','.join(map(str,k)):v for k,v in exception_tilewater.items()},'exception_polarwater':{','.join(map(str,k)):v for k,v in exception_polarwater.items()}}
  cache.write_text(json.dumps(payload,separators=(',',':'))+'\n');print(f'Wrote resumable occupancy cache {cache}',flush=True)
 # Candidate main tiles: any water tile whose 8-neighborhood contains a coast tile.
 candidate_tiles=[]; far_water_tiles=[]
 nband=(H-Y85+TY-1)//TY
 for by,tx in sorted(main_water):
  lat0=90-(Y85+by*TY)*STEP;lat1=90-min(H,Y85+(by+1)*TY)*STEP;latmax=max(abs(lat0),abs(lat1))
  rx=2 if latmax>=83 else 1
  near=any((by+dy, (tx+dx)%math.ceil(W/TX)) in main_coast for dy in (-1,0,1) for dx in range(-rx,rx+1) if 0<=by+dy<nband)
  if near:candidate_tiles.append((by,tx))
  else:far_water_tiles.append((by,tx))
 print(f'occupancy complete: total code1..6 physical-water {sum(total_water.values()):,}; main water tiles {len(main_water):,}, candidate coast-neighbor tiles {len(candidate_tiles):,}, far tiles {len(far_water_tiles):,}; polar cells {polar_water:,}; {time.time()-start_time:.1f}s',flush=True)
 summary={'schema':'worldatlas-v6-global-current-shore-water-consistency-audit-v1','status':'diagnostic_only_no_v2_v6_or_publication_changes','v6_rows_sha256':sha(vrp),'v6_runs_sha256':sha(vup),'physical_rows_sha256':sha(prp),'physical_runs_sha256':sha(pup),'physical_mask_sha256':'660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017','exception_span_manifest_sha256':ex_manifest_sha,'exception_span_file_count':ex_file_count,'grid':{'width':W,'height':H,'step_deg':STEP,'coordinate_rule':'lon=-180+(x+0.5)*step; lat=90-(y+0.5)*step','south_cutoff':'60S'},'water_code_legend':{'1':'Africa shore water','2':'Asia shore water','3':'Europe shore water','4':'North America shore water','5':'South America shore water','6':'Oceania shore water'},'rule':'Emit a candidate only for physical-water current codes 1..6 whose exact nearest current-V6 assigned exposed shore is a different continental category and is within 22,224m. Current ocean codes 7..10 are out of scope. Generic out-of-band ocean defaults are not merged or counted in this pass; named/enclosed overlays remain separate.','method':'Coast-neighbor tile census with source-hash cache; complete local shoreline halo. Homogeneous tiles with one current-water label and the same sole shore category are certified as having no class deltas. Otherwise, a conservative EDT shortlist uses crop-extreme cos(latitude), +1km margin, and exact fallback only for midpoint-class or coastal-band ambiguity; interval bounds include the 17th/unseen segment lower bound. No old land candidates are replayed.','band_m':BAND,'tile_cells':[TX,TY],'y85_row':Y85,'row_halo_cells':PADY,'source_exception_spans':exspans,'total_physical_water_code1_to6_by_code':{str(k):v for k,v in total_water.items()},'candidate_water_tiles':len(candidate_tiles),'far_water_tiles':len(far_water_tiles),'polar_water_cells':polar_water,'counts':{'ordinary_transition_cells_by_from_to':{},'candidate_transition_exception_overlaps':{}},'screened_water_cells':0,'exact_nearest_checks':0,'coast_segments_indexed_total':0,'tiles':[],'candidate_spans_file':'global-candidate-spans.jsonl.gz','protected_overlaps_note':'Candidate transitions are emitted without silently removing overlaps. Exception/enclosed-pocket intersections are reported for precedence review.'}
 supported={}; support_matrix={}; changed={}; ex_water={}; ex_supported={}; trans_ex={}; spans_tmp=run_dir/'global-candidate-spans.jsonl.gz.tmp';tiles_tmp=run_dir/'global-tile-coverage.jsonl.gz.tmp'
 spans_file=run_dir/'global-candidate-spans.jsonl.gz';tiles_file=run_dir/'global-tile-coverage.jsonl.gz'
 checkpoint_dir=run_dir/'completed-tiles';checkpoint_dir.mkdir(exist_ok=True)
 def ckpaths(by,tx):
  stem=f'tile_{by:03d}_{tx:03d}';return checkpoint_dir/(stem+'.json'),checkpoint_dir/(stem+'.spans.jsonl')
 with gzip.open(spans_tmp,'wt') as out, gzip.open(tiles_tmp,'wt') as tout:
  # Reassemble valid prior tile checkpoints into fresh aggregate streams.
  checkpoint_records=sorted(checkpoint_dir.glob('tile_*.json'))
  for rp in checkpoint_records:
   rec=json.load(open(rp))
   if rec.get('algorithm_revision') not in (ALGORITHM_REVISION,'v1_certified_homogeneous_no_class_change'):raise ValueError(f'checkpoint revision mismatch: {rp.name} has {rec.get("algorithm_revision")}')
   _,sp=ckpaths(*rec['tile'])
   if not sp.exists():raise ValueError(f'checkpoint missing spans file for {rp.name}')
   for line in sp.read_text().splitlines():out.write(line+'\n')
   tout.write(json.dumps(rec,separators=(',',':'))+'\n')
   for key,n in rec.get('changed_transitions',{}).items():summary['counts']['ordinary_transition_cells_by_from_to'][key]=summary['counts']['ordinary_transition_cells_by_from_to'].get(key,0)+int(n)
   summary['screened_water_cells']+=int(rec.get('midpoint_screen_survivors',0));summary['exact_nearest_checks']+=int(rec.get('exact_nearest_checks',0));summary['coast_segments_indexed_total']+=int(rec.get('shore_segments',0))
   if rec.get('class_fastpath'):
    summary['certified_no_class_change_tiles']=summary.get('certified_no_class_change_tiles',0)+1
    summary['certified_no_class_change_water_cells']=summary.get('certified_no_class_change_water_cells',0)+int(rec.get('certified_no_class_change_water_cells',0))
   for c,n in rec.get('south_cutoff_unresolved_by_code',{}).items():summary.setdefault('south_cutoff_unresolved_by_code',{}).__setitem__(str(c),summary.setdefault('south_cutoff_unresolved_by_code',{}).get(str(c),0)+int(n))
  out.flush();tout.flush()
  # Polar cap, full longitude (includes all potential wraparound donor shores).
  y0=0;y1=min(H,Y85+PADY)
  pp=np.empty((y1,W),np.uint8);ll=np.empty_like(pp)
  for iy,y in enumerate(range(y0,y1)):pp[iy]=expand_row(pr,pu,y);ll[iy]=expand_row(vr,vu,y)
  edges=extract_edges(pp,ll,0,y0,include_dateline=True);del pp,ll
  if len(edges['mids']):
   tree=cKDTree(edges['mids'],compact_nodes=True,balanced_tree=True);maxhalf=float(edges['half_lengths'].max());th=2*math.sin((BAND+maxhalf)/(2*R));summary['coast_segments_indexed_total']+=len(edges['mids'])
  else:tree=None;maxhalf=0;th=0
  polar_support={};polar_changes={};polar_total={k:0 for k in range(1,7)};polar_ex={};polar_exsup={}
  for y in range(Y85):
   p=expand_row(pr,pu,y);lab=expand_row(vr,vu,y);xs=np.flatnonzero((p==1)&(lab>=1)&(lab<=6))
   if not len(xs):continue
   for c,n in zip(*np.unique(lab[xs],return_counts=True)):polar_total[int(c)]+=int(n)
   masks=exc_masks(y,0,W,exidx); exhere={k:masks[k][xs] for k in masks}
   if tree is None:continue
   src=lab[xs];lat=90-(y+.5)*STEP;lon=-180+(xs+.5)*STEP;xyz=unit(np.full(len(xs),lat),lon)
   chord,_=tree.query(xyz,k=1,workers=-1);cand=np.flatnonzero(chord<=th+1e-12);summary['screened_water_cells']+=len(cand)
   for st in range(0,len(cand),5000):
    ii=cand[st:st+5000];d,j,k=nearest(xyz[ii],np.full(len(ii),lat),lon[ii],edges,tree=tree,workers=-1);summary['exact_nearest_checks']+=len(ii)
    dst=edges['category'][j];good=d<=BAND+1e-6
    for c,n in zip(*np.unique(src[ii][good],return_counts=True)):polar_support[int(c)]=polar_support.get(int(c),0)+int(n)
    pairv,pairn=np.unique(np.column_stack((src[ii][good],edges['category'][j][good])),axis=0,return_counts=True)
    for (s0,t0),n in zip(pairv,pairn):support_matrix[(int(s0),int(t0))]=support_matrix.get((int(s0),int(t0)),0)+int(n)
    for kind,maskv in exhere.items():
     if kind=='all':continue
     key=(kind,int(src[ii][good][maskv[ii][good]].size)) if False else None
    for q in np.flatnonzero(good):
     x=int(xs[ii[q]]);s=int(src[ii[q]]);t=int(dst[q]);
     # Record all ordinary transitions; the existing named/enclosed mask is an overlay, not silently discarded.
     if s!=t:
      polar_changes.setdefault((s,t,y),[]).append(x)
      for kind,maskv in exhere.items():
       if maskv[ii[q]]:trans_ex[(kind,s,t)]=trans_ex.get((kind,s,t),0)+1
     for kind,maskv in exhere.items():
      if maskv[ii[q]]:
       ex_supported[(kind,s)]=ex_supported.get((kind,s),0)+1
       if kind!='all':
        # All exception kinds are accumulated below at changed-cell granularity as well.
        pass
   for q in range(len(xs)):
    for kind,maskv in exhere.items():
     if kind!='all' and maskv[q]:polar_ex[(kind,int(src[q]))]=polar_ex.get((kind,int(src[q])),0)+1
  # emit polar deltas and row-level coverage
  for (s,t,y),xx in polar_changes.items():
   for a,b in spans(xx):out.write(json.dumps({'row':y,'start':a,'end':b,'from_code':s,'to_code':t,'basis':'nearest_current_assigned_shore_within_22224m','tile':'north-polar'},separators=(',',':'))+'\n')
  for s,n in polar_support.items():supported[(s,'all')]=supported.get((s,'all'),0)+n
  for (kind,s),n in polar_ex.items():ex_water[(kind,s)]=ex_water.get((kind,s),0)+n
  for (kind,s),n in ex_supported.items():ex_supported[(kind,s)]=ex_supported.get((kind,s),0)+n
  summary['coast_segments_indexed_total']+=0
  summary['tiles'].append({'tile':'north-polar','core_rows':[0,Y85],'crop_rows':[0,y1],'crop_columns':[0,W],'screened':sum(1 for _ in ()),'water_cells':sum(polar_total.values()),'supported_by_current_code':polar_support,'candidate_changes':{f'{s}->{t}':sum(b-a for (ss,tt,y),xx in polar_changes.items() if ss==s and tt==t for a,b in spans(xx)) for s,t in sorted({(s,t) for s,t,y in polar_changes})}})
  print(f'north polar done: water={sum(polar_total.values()):,}, supported={sum(polar_support.values()):,}, transitions={sum(len(v) for v in polar_changes.values()):,}; {time.time()-start_time:.1f}s',flush=True)
  del edges,tree
  # Main bands under 85N through the map's 60S cutoff.
  for ti,(by,tx) in enumerate(candidate_tiles):
   recpath,spanpath=ckpaths(by,tx)
   if recpath.exists() and spanpath.exists():continue
   cy0=Y85+by*TY;cy1=min(H,cy0+TY);cx0=tx*TX;cx1=min(W,cx0+TX)
   y0=max(0,cy0-PADY);y1=min(H,cy1+PADY)
   crop_latmax=max(abs(90-y0*STEP),abs(90-y1*STEP));cosx=max(1e-5,math.cos(math.radians(crop_latmax)))
   padx=int(math.ceil((BAND+2000)/(111195*cosx*STEP)))+4
   # Main bands are below 85N; cap padding to one third of the globe for safety.
   padx=min(padx,W//3);x0=cx0-padx;x1=cx1+padx;h=y1-y0;w=x1-x0
   p=np.empty((h,w),np.uint8);lab=np.empty((h,w),np.uint8)
   for iy,y in enumerate(range(y0,y1)):p[iy]=crop(pr,pu,y,x0,x1);lab[iy]=crop(vr,vu,y,x0,x1)
   edges=extract_edges(p,lab,x0,y0)
   yyoff=cy0-y0;xxoff=cx0-x0
   corep=p[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)].copy();corel=lab[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)].copy()
   wc=(corep==1)&(corel>=1)&(corel<=6);total_tile={c:int(np.count_nonzero(wc&(corel==c))) for c in range(1,7)}
   cutoff_tile={c:0 for c in range(1,7)};valid_w=wc
   if cy1==H:
    unresolved_start=max(cy0,H-PADY);sl=slice(unresolved_start-cy0,None)
    for c in range(1,7):cutoff_tile[c]=int(np.count_nonzero(wc[sl]&(corel[sl]==c)))
    valid_w[sl]=False
   water_labels=np.unique(corel[valid_w]);coast_categories=np.unique(edges['category']) if len(edges['mids']) else np.empty(0,np.uint8)
   homogeneous=(not len(water_labels)) or (not len(coast_categories)) or (len(water_labels)==1 and len(coast_categories)==1 and int(water_labels[0])==int(coast_categories[0]))
   if homogeneous:
    summary.setdefault('certified_no_class_change_tiles',0);summary['certified_no_class_change_tiles']+=1
    certified_cells=sum(total_tile.values())-sum(cutoff_tile.values());summary.setdefault('certified_no_class_change_water_cells',0);summary['certified_no_class_change_water_cells']+=certified_cells
    tile_record={'algorithm_revision':ALGORITHM_REVISION,'tile':[by,tx],'core_rows':[cy0,cy1],'core_cols':[cx0,cx1],'crop_rows':[y0,y1],'crop_unwrapped_cols':[x0,x1],'core_water_by_code':{str(c):n for c,n in total_tile.items() if n},'south_cutoff_unresolved_by_code':{str(c):n for c,n in cutoff_tile.items() if n},'coast_categories':[int(c) for c in coast_categories],'shore_segments':len(edges['mids']),'class_fastpath':'no within-band class delta possible for non-cutoff cells: all current water labels and all exposed shore donors in the certified halo are the same category' if len(coast_categories) else 'no exposed shore segments in complete coastal halo for non-cutoff cells','certified_no_class_change_water_cells':certified_cells,'changed_transitions':{},'midpoint_screen_survivors':0,'exact_nearest_checks':0,'crop_halo_proof_m':BAND+2000}
    tile_record['certified_no_class_change_water_cells']=sum(total_tile.values())-sum(cutoff_tile.values())
    tile_record['algorithm_revision']=ALGORITHM_REVISION
    spanpath.write_text('');tmprec=recpath.with_suffix('.json.tmp');tmprec.write_text(json.dumps(tile_record,separators=(',',':'))+'\n');tmprec.replace(recpath)
    tout.write(json.dumps(tile_record,separators=(',',':'))+'\n');tout.flush();out.flush()
    if ti<3 or (ti+1)%10==0 or ti+1==len(candidate_tiles):print(f'main tile {ti+1}/{len(candidate_tiles)} {by},{tx}: homogeneous fastpath, water={sum(total_tile.values()):,}, shorecats={coast_categories.tolist()}, elapsed={time.time()-start_time:.1f}s',flush=True)
    del edges,corep,corel,wc,p,lab
    continue
   # Fast conservative pixel-center screen. Every point within BAND of a shore
   # segment is within BAND+1km of an exposed physical-land cell center.
   # Longitude sampling uses the minimum cos(latitude) over the crop.
   dry=(p==17)&(lab>=17)&(lab<=22);wet=p==1
   shore=dry&(np.roll(wet,1,axis=1)|np.roll(wet,-1,axis=1))
   shore[1:]|=dry[1:]&wet[:-1];shore[:-1]|=dry[:-1]&wet[1:]
   pixel_dist=distance_transform_edt(~shore,sampling=(111195.0*STEP,111195.0*STEP*cosx)) if len(edges['mids']) else None
   del shore,dry,wet
   print(f'main tile {by},{tx} memory after EDT: RSS={rss_mib():.0f} MiB crop={h}x{w} edges={len(edges["mids"]):,}',flush=True)
   wc=(corep==1)&(corel>=1)&(corel<=6)
   if pixel_dist is not None:
    dd=pixel_dist[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)]
    near=wc&(dd<=BAND+1000.0)
   else:dd=None;near=np.zeros_like(wc)
   del pixel_dist,p,lab
   if cy1==H:near[max(0,unresolved_start-cy0):]=False
   ys,xs=np.nonzero(near);pixel_dists=dd[near].copy() if dd is not None else np.empty(0,float);del near,dd; nwater=len(xs)
   print(f'main tile {by},{tx} memory after shortlist: RSS={rss_mib():.0f} MiB near={nwater:,}',flush=True)
   tile_span_handle=open(spanpath,'w');changed_tile={};support_tile={};support_pair={};ex_tile={};exsup_tile={};screened=0;exact=0;changes_by={}
   for kind in ('all','enclosed-pocket','named-seavox','ordinary-water','other-exception'):
    for c in range(1,7):
     ex_tile[(kind,c)]=exception_tilewater.get((by,tx,c,kind),0)
   if len(edges['mids']):tree=cKDTree(edges['mids'],compact_nodes=True,balanced_tree=True);maxhalf=float(edges['half_lengths'].max());summary['coast_segments_indexed_total']+=len(edges['mids'])
   else:tree=None;maxhalf=0
   print(f'main tile {by},{tx} memory after tree: RSS={rss_mib():.0f} MiB',flush=True)
   for st in range(0,nwater,10000):
    en=min(st+10000,nwater);latq=90-(ys[st:en]+cy0+.5)*STEP;lonq=-180+(xs[st:en]+cx0+.5)*STEP;xyz=unit(latq,lonq);src=corel[ys[st:en],xs[st:en]];pd=pixel_dists[st:en]
    screened+=en-st
    if tree is None:continue
    supported_here=np.zeros(en-st,bool);target_here=np.zeros(en-st,np.uint8)
    if len(coast_categories)==1:
     one=int(coast_categories[0])
     # The crop-wide-cosine EDT is a conservative lower-bound shortlist, not
     # an in-band certificate. Same-class water cannot change its label; for
     # every other source class, exact-filter the near-band candidate.
     certout=pd>=BAND+500.0
     exact_idx=np.flatnonzero((src!=one)&~certout)
    else:
     certsame,_,_=coarse_certificates(xyz,src,tree,edges,maxhalf,k=16)
     # A certified same-class nearest shore implies no label change. All other
     # potential mismatches are checked against exact spherical segment distance.
     exact_idx=np.flatnonzero(~certsame)
    if len(exact_idx):
     d,j,k=nearest(xyz[exact_idx],latq[exact_idx],lonq[exact_idx],edges,tree=tree,workers=2);exact+=len(exact_idx);dst0=edges['category'][j];good0=d<=BAND+1e-6
     supported_here[exact_idx]=good0;target_here[exact_idx[good0]]=dst0[good0]
     for q in np.flatnonzero(good0):
      pos=exact_idx[q];s=int(src[pos]);t=int(dst0[q])
      if s!=t:
       y=cy0+int(ys[st+pos]);x=cx0+int(xs[st+pos]);changes_by.setdefault((s,t,y),[]).append(x);changed_tile[(s,t)]=changed_tile.get((s,t),0)+1
    for c,n in zip(*np.unique(src[supported_here],return_counts=True)):support_tile[int(c)]=support_tile.get(int(c),0)+int(n)
    pairv,pairn=np.unique(np.column_stack((src[supported_here],target_here[supported_here])),axis=0,return_counts=True)
    for (s0,t0),n in zip(pairv,pairn):support_pair[(int(s0),int(t0))]=support_pair.get((int(s0),int(t0)),0)+int(n);support_matrix[(int(s0),int(t0))]=support_matrix.get((int(s0),int(t0)),0)+int(n)
    supidx=np.flatnonzero(supported_here)
    if len(supidx):
     rowgood=ys[st+supidx];cuts=np.r_[0,np.flatnonzero(np.diff(rowgood)!=0)+1,len(supidx)]
     for aa,bb in zip(cuts[:-1],cuts[1:]):
      yy=int(rowgood[aa]);mm=exc_masks(cy0+yy,cx0,cx1,exidx);pos=st+supidx[aa:bb];xx=xs[pos];ss=src[supidx[aa:bb]];tt=target_here[supidx[aa:bb]]
      for kind,mask in mm.items():
       hit=mask[xx]
       if np.any(hit):
        for c,n in zip(*np.unique(ss[hit],return_counts=True)):exsup_tile[(kind,int(c))]=exsup_tile.get((kind,int(c)),0)+int(n)
        if kind!='all':
         changedhit=hit&(ss!=tt)
         if np.any(changedhit):
          pairv,pairn=np.unique(np.column_stack((ss[changedhit],tt[changedhit])),axis=0,return_counts=True)
          for (s0,t0),n in zip(pairv,pairn):trans_ex[(kind,int(s0),int(t0))]=trans_ex.get((kind,int(s0),int(t0)),0)+int(n)
   for c,n in support_tile.items():supported[(c,'all')]=supported.get((c,'all'),0)+n
   for (kind,c),n in ex_tile.items():ex_water[(kind,c)]=ex_water.get((kind,c),0)+n
   for (kind,c),n in exsup_tile.items():ex_supported[(kind,c)]=ex_supported.get((kind,c),0)+n
   for (s,t,y),xx in changes_by.items():
    for a,b in spans(xx):
     line=json.dumps({'row':y,'start':a,'end':b,'from_code':s,'to_code':t,'basis':'nearest_current_assigned_shore_within_22224m','tile':[by,tx]},separators=(',',':'))+'\n';out.write(line);tile_span_handle.write(line)
   for (s,t),n in changed_tile.items():changed[(s,t)]=changed.get((s,t),0)+n
   summary['screened_water_cells']+=screened;summary['exact_nearest_checks']+=exact
   # Within-band support is diagnostic only for non-homogeneous tiles; the
   # homogeneous fastpath intentionally skips exact band-membership counts.
   unsupported={str(c):max(0,total_tile[c]-support_tile.get(c,0)) for c in range(1,7)}
   valid_core_end=(H-PADY if cy1==H else cy1)
   clearance_y=(min(cy0-y0,y1-valid_core_end)*111195*STEP)
   clearance_x=min((cx0-x0)*111195*cosx*STEP,(x1-cx1)*111195*cosx*STEP)
   clearance=min(clearance_y,clearance_x)-BAND
   if screened and clearance<=maxhalf+1:raise ValueError(f'uncertified tile crop {by},{tx} clearance {clearance}, maxhalf {maxhalf}')
   transition_summary={f'{s}->{t}':n for (s,t),n in sorted(changed_tile.items())}
   for (s,t),n in changed_tile.items():summary['counts']['ordinary_transition_cells_by_from_to'][f'{s}->{t}']=summary['counts']['ordinary_transition_cells_by_from_to'].get(f'{s}->{t}',0)+n
   tile_record={'algorithm_revision':ALGORITHM_REVISION,'tile':[by,tx],'core_rows':[cy0,cy1],'core_cols':[cx0,cx1],'crop_rows':[y0,y1],'crop_unwrapped_cols':[x0,x1],'core_water_by_code':{str(c):n for c,n in total_tile.items() if n},'south_cutoff_unresolved_by_code':{str(c):n for c,n in cutoff_tile.items() if n},'shore_categories':[int(c) for c in coast_categories],'shore_segments':len(edges['mids']),'max_half_segment_m':maxhalf,'midpoint_screen_survivors':screened,'exact_nearest_checks':exact,'exact_checked_supported_by_current_code_in_potential_mismatch_cells':support_tile,'changed_transitions':transition_summary,'nonuniform_tile_cells_not_exactly_counted_as_supported_by_code':unsupported,'exception_water_by_kind_code':{f'{k}:code{c}':n for (k,c),n in ex_tile.items()},'crop_clearance_after_band_m':clearance}
   tile_span_handle.flush();tile_span_handle.close();tmprec=recpath.with_suffix('.json.tmp');tmprec.write_text(json.dumps(tile_record,separators=(',',':'))+'\n');tmprec.replace(recpath)
   tout.write(json.dumps(tile_record,separators=(',',':'))+'\n');tout.flush();out.flush()
   if ti<3 or (ti+1)%10==0 or ti+1==len(candidate_tiles):print(f'main tile {ti+1}/{len(candidate_tiles)} {by},{tx}: nearshore={nwater:,} exact={exact:,} changed={sum(changed_tile.values()):,} edges={len(edges["mids"]):,} RSS={rss_mib():.0f} MiB elapsed={time.time()-start_time:.1f}s',flush=True)
   del edges,tree,corep,corel,wc,ys,xs
 summary['counts']['ordinary_transition_cells_by_from_to']={f'{a}->{b}':v for (a,b),v in sorted(changed.items())}
 summary['counts']['candidate_transition_exception_overlaps']={f'{kind}:{s}->{t}':v for (kind,s,t),v in sorted(trans_ex.items())}
 summary['complete_unsupported_outside_band_enumeration']=False
 summary['unsupported_followup_note']='Out-of-band ocean-default spans and their named-basin exception coverage were deliberately not merged or exhaustively enumerated in this mismatch pass.'
 summary['screened_water_cells_total']=summary['screened_water_cells'];summary['exact_nearest_checks_total']=summary['exact_nearest_checks'];summary['elapsed_seconds']=time.time()-start_time
 spans_tmp.replace(spans_file);tiles_tmp.replace(tiles_file)
 summary['candidate_spans_sha256']=sha(spans_file);summary['tile_coverage_sha256']=sha(tiles_file)
 p=run_dir/'global-audit-summary.json';p.write_text(json.dumps(summary,indent=2)+'\n')
 run_manifest=json.load(open(run_manifest_path));run_manifest['status']='complete';run_manifest['summary_sha256']=sha(p);run_manifest['completed_at_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());run_manifest_path.write_text(json.dumps(run_manifest,indent=2)+'\n')
 print('GLOBAL AUDIT COMPLETE',json.dumps({'total_water':summary['total_physical_water_code1_to6_by_code'],'transitions':summary['counts']['ordinary_transition_cells_by_from_to'],'exact_checks':summary['exact_nearest_checks_total'],'tiles':len(candidate_tiles),'fastpath_tiles':summary.get('certified_no_class_change_tiles',0),'elapsed_seconds':summary['elapsed_seconds'],'summary':str(p),'spans':str(spans_file)},indent=2),flush=True)
if __name__=='__main__':main()

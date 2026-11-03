#!/usr/bin/env python3
"""Fresh complete 22.224-km coastal-water assignments from final V6 land only.

The physical mask selects water centers; V6 codes are read only for assigned
land shoreline donors. Existing water codes never participate in target
selection. Output is a fresh band assignment layer, not a delta against V6.
"""
import argparse, gzip, hashlib, json, math, time
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
import sys
HELPER=Path(__file__).resolve().parents[1]/'global-current-shore-water-20261103'/'run_global_water_consistency.py'
sys.path.insert(0,str(HELPER.parent))
import run_global_water_consistency as geom

W,H=131072,54614; STEP=360.0/W; BAND=22224.0; R=6371008.8
V6=Path('/tmp/v6-aegean-final-publication-20261103/final-candidate-grid-root-approved-v3')
PH=Path('/tmp/worldatlas-v5-recovery/raw')
CACHE=HELPER.parent/'occupancy-census-cache.json'
TY,TX=3600,7200
Y85=int(math.ceil(5.0/STEP)); PADY=int(math.ceil((BAND+1500.0)/(111195.0*STEP)))+4
RULE='coastal-band-nearest-final-land-22.224km'
REV='fresh_band_all_physical_water_v4_cached_categories_subrow_tiles'
OUTBASE=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()

def rss_mib():
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmRSS:'):return int(line.split()[1])/1024
 except Exception:pass
 return -1.0

def write_json(path,obj):
 tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)

def coast_neighborhoods(coast):
 ntilesx=math.ceil(W/TX); nbands=math.ceil((H-Y85)/TY); out=set()
 for by,tx in coast:
  y0=Y85+by*TY; y1=min(H,y0+TY)
  latmax=max(abs(90-y0*STEP),abs(90-y1*STEP))
  rx=2 if latmax>=83 else 1
  for dy in (-1,0,1):
   by2=by+dy
   if by2<0 or by2>=nbands:continue
   for dx in range(-rx,rx+1):out.add((by2,(tx+dx)%ntilesx))
 return sorted(out)

def certified_bounds(points,edges,tree,maxhalf,k,workers=2):
 """Certified nearest-category and band bounds from segment-midpoint intervals."""
 n=len(points); q=min(k,len(edges['mids']))
 chord,idx=tree.query(points,k=q,workers=workers)
 if q==1:chord=chord[:,None];idx=idx[:,None]
 mid=2*R*np.arcsin(np.clip(chord/2,0,1))
 cats=edges['category'][idx];half=edges['half_lengths'][idx]
 lo=np.maximum(0.0,mid-half);hi=mid+half
 unseen=np.maximum(0.0,mid[:,-1]-maxhalf)
 all_lower=np.minimum(lo.min(axis=1),unseen)
 bestpos=np.argmin(hi,axis=1);bestcat=cats[np.arange(n),bestpos]
 upper=np.min(hi,axis=1)
 cats_unique=edges.get('_category_values')
 if cats_unique is None:cats_unique=np.unique(edges['category'])
 if len(cats_unique)==1:
  class_cert=np.ones(n,bool)
 else:
  other_lower=np.full(n,np.inf)
  for c in cats_unique:
   m=(bestcat[:,None]!=c)&(cats==c)
   if np.any(m):other_lower=np.minimum(other_lower,np.where(m,lo,np.inf).min(axis=1))
  other_lower=np.minimum(other_lower,unseen)
  class_cert=upper+1e-5<other_lower
 inband=upper<=BAND+1e-6
 outband=all_lower>BAND+1e-6
 return bestcat.astype(np.uint8),all_lower,upper,class_cert,inband,outband

def make_spans(xs,codes,lows,ups,exact):
 """Sorted row-local runs, coalesced where x and assigned code are contiguous."""
 if not len(xs):return []
 cuts=np.r_[0,np.flatnonzero((np.diff(xs)>1)|(codes[1:]!=codes[:-1]))+1,len(xs)]
 out=[]
 for a,b in zip(cuts[:-1],cuts[1:]):
  out.append({'start':int(xs[a]),'end':int(xs[b-1])+1,'code':int(codes[a]),
              'rule_id':RULE,'member_id':f'coastal-water-nearest-final-land-category-{int(codes[a])}',
              'distance_lower_min_m':float(np.min(lows[a:b])),
              'distance_upper_max_m':float(np.max(ups[a:b])),
              'exact_distance_cells':int(np.count_nonzero(exact[a:b])),
              'bound_certified_cells':int((b-a)-np.count_nonzero(exact[a:b]))})
 return out

def run_tile(tile_id, core_rows, core_cols, p, lab, crop_bounds, edges, tree, run_dir, row_stats, workers=2):
 by,tx=tile_id[:2]; cy0,cy1=core_rows;cx0,cx1=core_cols;y0,y1,x0,x1=crop_bounds
 tile_key=f'tile_{by:03d}_{tx:03d}'+(f'_rows_{cy0:05d}_{cy1:05d}' if len(tile_id)>2 else '')
 yyoff=cy0-y0;xxoff=cx0-x0
 corep=p[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)]
 corel=lab[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)]
 # Classification source is solely physical-water mask plus final assigned land.
 water=(corep==1)
 totalwater=int(np.count_nonzero(corep==1));valid_end=cy1
 edge_truncated_water=int(np.count_nonzero(water[max(0,H-PADY-cy0):])) if cy1==H else 0
 crop_latmax=max(abs(90-y0*STEP),abs(90-y1*STEP));cosx=max(1e-5,math.cos(math.radians(crop_latmax)))
 shore_segments=len(edges['mids']);categories=np.unique(edges['category']) if shore_segments else np.empty(0,np.uint8);edges['_category_values']=categories
 if not shore_segments:
  p=None;lab=None
  spanpath=run_dir/'completed-tiles'/f'{tile_key}.assignments.jsonl.gz'
  tmp=spanpath.with_suffix('.jsonl.gz.tmp')
  with gzip.open(tmp,'wt') as fh: pass
  tmp.replace(spanpath)
  rec={'algorithm_revision':REV,'tile':[by,tx],'core_rows':[cy0,cy1],'core_cols':[cx0,cx1],
       'crop_rows':[y0,y1],'crop_unwrapped_cols':[x0,x1],'physical_water_centers':totalwater,
       'screened_water_centers':0,'fresh_band_assigned_cells':0,'assigned_cells_by_code':{},'south_edge_truncated_water_centers':edge_truncated_water,
       'exact_nearest_checks':0,'certified_inband_cells':0,'certified_outband_cells':0,
       'shore_categories':[],'shore_segments':0,'class_fastpath':'no shoreline segment in the complete band halo',
       'span_file':spanpath.name,'span_sha256':sha(spanpath),'crop_halo_clearance_m':None,'peak_rss_mib':rss_mib()}
  rec['tile']=list(tile_id);write_json(run_dir/'completed-tiles'/f'{tile_key}.json',rec);return rec
 # Coastline cell-center EDT is only a conservative shortlist; never an in-band proof.
 dry=(p==17)&(lab>=17)&(lab<=22);wet=(p==1)
 if np.any((p==17)&((lab<17)|(lab>22))):raise ValueError(f'physical land lacks assigned V6 land code in tile {by},{tx}')
 shore=dry&(np.roll(wet,1,axis=1)|np.roll(wet,-1,axis=1));shore[1:]|=dry[1:]&wet[:-1];shore[:-1]|=dry[:-1]&wet[1:]
 pixel_dist=distance_transform_edt(~shore,sampling=(111195.0*STEP,111195.0*STEP*cosx))
 del shore,dry,wet
 dd=pixel_dist[yyoff:yyoff+(cy1-cy0),xxoff:xxoff+(cx1-cx0)]
 near=water&(dd<=BAND+1000.0)
 ys,xs=np.nonzero(near);del near,dd,pixel_dist
 nnear=len(xs);maxhalf=float(edges['half_lengths'].max());stats={c:{'assigned':0,'exact':0,'bounded':0,'lo_min':math.inf,'hi_max':0.0,'exact_min':math.inf,'exact_max':0.0} for c in range(1,7)}
 outcount=exactout=exactchecks=0
 spanpath=run_dir/'completed-tiles'/f'{tile_key}.assignments.jsonl.gz';tmp=spanpath.with_suffix('.jsonl.gz.tmp')
 span_count=0
 with gzip.open(tmp,'wt') as fh:
  for st in range(0,nnear,2000):
   en=min(st+2000,nnear);yy=ys[st:en];xx=xs[st:en]
   lat=90-(yy+cy0+.5)*STEP;lon=-180+(xx+cx0+.5)*STEP
   points=geom.unit(lat,lon)
   k=1 if len(categories)==1 else 16
   target,lower,upper,classcert,inband,outband=certified_bounds(points,edges,tree,maxhalf,k,workers)
   safein=classcert&inband;safeout=outband;need=~(safein|safeout)
   exact=np.zeros(en-st,bool);support=safein.copy();codes=target.copy();lo=lower.copy();up=upper.copy()
   amb=np.flatnonzero(need)
   if len(amb):
    d,j,qmax=geom.nearest(points[amb],lat[amb],lon[amb],edges,tree=tree,workers=workers)
    exactchecks+=len(amb);exact[amb]=True;good=d<=BAND+1e-6
    support[amb]=good;codes[amb]=edges['category'][j];lo[amb]=d;up[amb]=d
    exactout+=int(np.count_nonzero(~good))
   outcount+=int(np.count_nonzero(safeout))
   for c in range(1,7):
    pick=support&(codes==c)
    n=int(np.count_nonzero(pick))
    if n:
     s=stats[c];s['assigned']+=n;s['exact']+=int(np.count_nonzero(exact&pick));s['bounded']+=int(np.count_nonzero(~exact&pick))
     s['lo_min']=min(s['lo_min'],float(np.min(lo[pick])));s['hi_max']=max(s['hi_max'],float(np.max(up[pick])))
     if np.any(exact&pick):s['exact_min']=min(s['exact_min'],float(np.min(lo[exact&pick])));s['exact_max']=max(s['exact_max'],float(np.max(up[exact&pick])))
   # Emit fresh band assignments as row-local, sorted spans with distance support.
   good=np.flatnonzero(support)
   if len(good):
    rowids=yy[good]
    cuts=np.r_[0,np.flatnonzero(np.diff(rowids)!=0)+1,len(good)]
    for a,b in zip(cuts[:-1],cuts[1:]):
     idx=good[a:b];runs=make_spans(xx[idx]+cx0,codes[idx],lo[idx],up[idx],exact[idx])
     y=int(rowids[a]+cy0);fh.write(json.dumps({'row':y,'spans':runs},separators=(',',':'))+'\n')
     span_count+=len(runs)
  fh.flush()
 tmp.replace(spanpath)
 # Each span file is sorted by row/start; tile core coverage and full-assignment counts are explicit.
 clearance_y=min(cy0-y0,(y1-valid_end) if cy1<H else math.inf)*111195.0*STEP
 clearance_x=min((cx0-x0)*111195.0*cosx*STEP,(x1-cx1)*111195.0*cosx*STEP)
 clearance=min(clearance_y,clearance_x)-BAND
 if nnear and clearance<=maxhalf+1.0:raise ValueError(f'uncertified shore halo tile {by},{tx}: clearance={clearance}, maxhalf={maxhalf}')
 rec={'algorithm_revision':REV,'tile':[by,tx],'core_rows':[cy0,cy1],'core_cols':[cx0,cx1],
      'crop_rows':[y0,y1],'crop_unwrapped_cols':[x0,x1],'physical_water_centers':totalwater,
      'screened_water_centers':nnear,'fresh_band_assigned_cells':sum(s['assigned'] for s in stats.values()),
      'assigned_cells_by_code':{str(c):s['assigned'] for c,s in stats.items() if s['assigned']},'south_edge_truncated_water_centers':edge_truncated_water,
      'distance_support_by_code':{str(c):{'assigned_cells':s['assigned'],'certified_interval_cells':s['bounded'],'exact_distance_cells':s['exact'],
          'distance_lower_min_m':None if s['lo_min']==math.inf else s['lo_min'],'distance_upper_max_m':s['hi_max'],
          'exact_distance_min_m':None if s['exact_min']==math.inf else s['exact_min'],'exact_distance_max_m':None if s['exact_max']==0 else s['exact_max']} for c,s in stats.items() if s['assigned']},
      'exact_nearest_checks':exactchecks,'exact_outside_band_checks':exactout,'certified_outside_band_cells':outcount,
      'shore_categories':[int(c) for c in categories],'shore_segments':shore_segments,
      'class_fastpath':('one shoreline class; target category is fixed by final land shore' if len(categories)==1 else None),
      'span_count':span_count,'span_file':spanpath.name,'span_sha256':sha(spanpath),
      'crop_halo_clearance_m':clearance,'max_half_segment_m':maxhalf,'peak_rss_mib':rss_mib()}
 rec['tile']=list(tile_id);write_json(run_dir/'completed-tiles'/f'{tile_key}.json',rec)
 return rec

def run_polar_strip(pr,pu,vr,vu,run_dir):
 # Physical water north of 85N is screened against the complete nearby shoreline;
 # this strip avoids overlooking cells just north of the Y85 tile origin.
 y0=max(0,Y85-PADY);y1=min(H,Y85+PADY);core0=y0;core1=min(Y85,H)
 pp=np.empty((y1-y0,W),np.uint8);ll=np.empty_like(pp)
 for iy,y in enumerate(range(y0,y1)):pp[iy]=geom.expand_row(pr,pu,y);ll[iy]=geom.expand_row(vr,vu,y)
 edges=geom.extract_edges(pp,ll,0,y0,include_dateline=True);del pp,ll
 edges['_category_values']=np.unique(edges['category']) if len(edges['mids']) else np.empty(0,np.uint8)
 spanpath=run_dir/'completed-tiles'/'north-polar.assignments.jsonl.gz';tmp=spanpath.with_suffix('.jsonl.gz.tmp')
 pcore=np.empty((core1-core0,W),np.uint8)
 for iy,y in enumerate(range(core0,core1)):pcore[iy]=geom.expand_row(pr,pu,y)
 water=pcore==1;total=int(np.count_nonzero(water))
 if not len(edges['mids']) or not total:
  with gzip.open(tmp,'wt') as fh: pass
  tmp.replace(spanpath)
  rec={'algorithm_revision':REV,'tile':'north-polar','core_rows':[core0,core1],'core_cols':[0,W],'physical_water_centers':total,'screened_water_centers':0,'fresh_band_assigned_cells':0,'assigned_cells_by_code':{},'exact_nearest_checks':0,'span_count':0,'span_file':spanpath.name,'span_sha256':sha(spanpath),'shore_segments':len(edges['mids'])}
  write_json(run_dir/'completed-tiles'/'north-polar.json',rec);return rec
 cosx=max(1e-5,math.cos(math.radians(max(abs(90-y0*STEP),abs(90-y1*STEP)))))
 pband=np.empty((y1-y0,W),np.uint8);lband=np.empty_like(pband)
 for iy,y in enumerate(range(y0,y1)):pband[iy]=geom.expand_row(pr,pu,y);lband[iy]=geom.expand_row(vr,vu,y)
 dry=(pband==17)&(lband>=17)&(lband<=22);wet=pband==1;shore=dry&(np.roll(wet,1,axis=1)|np.roll(wet,-1,axis=1));shore[1:]|=dry[1:]&wet[:-1];shore[:-1]|=dry[:-1]&wet[1:]
 pd=distance_transform_edt(~shore,sampling=(111195.0*STEP,111195.0*STEP*cosx));del dry,wet,shore
 tree=cKDTree(edges['mids'],compact_nodes=True,balanced_tree=True);maxhalf=float(edges['half_lengths'].max());stats={c:{'n':0,'exact':0,'lo':math.inf,'hi':0.} for c in range(1,7)};cats_unique=edges['_category_values']
 span_count=0;exact_checks=0
 with gzip.open(tmp,'wt') as fh:
  for iy,y in enumerate(range(core0,core1)):
   xs=np.flatnonzero(water[iy]&(pd[iy]<=BAND+1000.0))
   for st in range(0,len(xs),2000):
    x=xs[st:st+2000];lat=np.full(len(x),90-(y+.5)*STEP);lon=-180+(x+.5)*STEP;points=geom.unit(lat,lon);target,lower,upper,classcert,inband,outband=certified_bounds(points,edges,tree,maxhalf,1 if len(cats_unique)==1 else 16);safein=classcert&inband;need=~(safein|outband);exact=np.zeros(len(x),bool);support=safein.copy();codes=target.copy();lo=lower.copy();up=upper.copy();amb=np.flatnonzero(need)
    if len(amb):
     d,j,_=geom.nearest(points[amb],lat[amb],lon[amb],edges,tree=tree,workers=2);exact_checks+=len(amb);exact[amb]=True;good=d<=BAND+1e-6;support[amb]=good;codes[amb]=edges['category'][j];lo[amb]=d;up[amb]=d
    good=np.flatnonzero(support)
    if len(good):
     runs=make_spans(x[good],codes[good],lo[good],up[good],exact[good]);fh.write(json.dumps({'row':y,'spans':runs},separators=(',',':'))+'\n');span_count+=len(runs)
     for r in runs:
      s=stats[int(r['code'])];n=r['end']-r['start'];s['n']+=n;s['exact']+=r['exact_distance_cells'];s['lo']=min(s['lo'],r['distance_lower_min_m']);s['hi']=max(s['hi'],r['distance_upper_max_m'])
 tmp.replace(spanpath)
 rec={'algorithm_revision':REV,'tile':'north-polar','core_rows':[core0,core1],'core_cols':[0,W],'physical_water_centers':total,'screened_water_centers':int(np.count_nonzero(water&(pd[:core1-y0]<=BAND+1000.0))),'fresh_band_assigned_cells':sum(s['n'] for s in stats.values()),'assigned_cells_by_code':{str(c):s['n'] for c,s in stats.items() if s['n']},'distance_support_by_code':{str(c):{'assigned_cells':s['n'],'exact_distance_cells':s['exact'],'distance_lower_min_m':None if s['lo']==math.inf else s['lo'],'distance_upper_max_m':s['hi']} for c,s in stats.items() if s['n']},'exact_nearest_checks':exact_checks,'span_count':span_count,'span_file':spanpath.name,'span_sha256':sha(spanpath),'shore_segments':len(edges['mids']),'peak_rss_mib':rss_mib()}
 write_json(run_dir/'completed-tiles'/'north-polar.json',rec);return rec

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run-dir',required=True);ap.add_argument('--resume',action='store_true');ap.add_argument('--tile-start',type=int,default=0);ap.add_argument('--tile-step',type=int,default=1);ap.add_argument('--skip-polar',action='store_true');ap.add_argument('--partial-shard',action='store_true');ap.add_argument('--max-core-rows',type=int,default=0);ap.add_argument('--kd-workers',type=int,default=2);args=ap.parse_args()
 run=Path(args.run_dir).resolve()
 if not run.is_relative_to(OUTBASE.resolve()):raise ValueError('run output must stay under this audit workspace')
 mf=run/'manifest.json'
 if run.exists() and not args.resume:raise FileExistsError(f'run exists; use --resume only for this same active input set: {run}')
 if not run.exists():
  if args.resume:raise FileNotFoundError(run)
  run.mkdir(parents=True)
 (run/'completed-tiles').mkdir(exist_ok=True)
 v6r=V6/'rows.u32le';v6u=V6/'runs.u32le';phr=PH/'physical-rows.u32';phu=PH/'physical-runs.u32'
 inputs={'v6_rows_sha256':sha(v6r),'v6_runs_sha256':sha(v6u),'physical_rows_sha256':sha(phr),'physical_runs_sha256':sha(phu),'physical_mask_sha256':'660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017','shore_helper_sha256':sha(HELPER),'algorithm_sha256':sha(Path(__file__)),'coast_census_cache_sha256':sha(CACHE)}
 cache=json.load(open(CACHE));ci=cache.get('inputs',{})
 expected={'v6_rows_sha256':inputs['v6_rows_sha256'],'v6_runs_sha256':inputs['v6_runs_sha256'],'physical_rows_sha256':inputs['physical_rows_sha256'],'physical_runs_sha256':inputs['physical_runs_sha256']}
 if any(ci.get(k)!=v for k,v in expected.items()):raise ValueError('coastal tile cache does not match final V6 land and physical mask')
 if args.resume:
  if not mf.exists():raise ValueError('resume needs a manifest')
  old=json.load(open(mf))
  if old.get('status')!='active' or old.get('inputs')!=inputs:raise ValueError('resume manifest/status/source hashes differ')
 else:
  if mf.exists():raise FileExistsError(mf)
  write_json(mf,{'schema':'worldatlas-full-coastal-band-rebuild-manifest-v1','status':'active','inputs':inputs,'run_dir':str(run)})
 vr=np.memmap(v6r,dtype='<u4',mode='r');vu=np.memmap(v6u,dtype='<u4',mode='r');pr=np.memmap(phr,dtype='<u4',mode='r');pu=np.memmap(phu,dtype='<u4',mode='r')
 coast={tuple(map(int,z)) for z in cache['main_coast']};all_tiles=coast_neighborhoods(coast)
 if args.tile_start<0 or args.tile_step<1 or args.tile_start>=max(1,len(all_tiles)):raise ValueError('invalid tile shard start/step')
 base_tiles=all_tiles[args.tile_start::args.tile_step]
 tiles=[]
 for by,tx in base_tiles:
  cy0=Y85+by*TY;cy1=min(H,cy0+TY);step=args.max_core_rows or TY
  if step<1:raise ValueError('max-core-rows must be >=1')
  for sy0 in range(cy0,cy1,step):tiles.append((by,tx,sy0,min(cy1,sy0+step)))
 if args.partial_shard and not args.skip_polar:raise ValueError('partial shards should pass --skip-polar to avoid duplicate polar ownership')
 print(f'Pinned final land and physical mask. Shore tiles={len(coast)}, candidate base tiles={len(all_tiles)}, shard base tiles={len(base_tiles)}, processed core slices={len(tiles)} starting at index {args.tile_start} step {args.tile_step}, max-core-rows={args.max_core_rows or TY}, KD workers={args.kd_workers}; polar strip rows={[max(0,Y85-PADY),Y85]}; {time.time():.0f}',flush=True)
 t0=time.time();done=[];cp=run/'completed-tiles'
 polar_json=cp/'north-polar.json';polar_spans=cp/'north-polar.assignments.jsonl.gz'
 if args.skip_polar:pass
 elif args.resume and polar_json.exists() and polar_spans.exists():done.append(json.load(open(polar_json)))
 else:done.append(run_polar_strip(pr,pu,vr,vu,run))
 ntilesx=math.ceil(W/TX)
 for i,(by,tx,cy0,cy1) in enumerate(tiles,1):
  tile_key=f'tile_{by:03d}_{tx:03d}'+(f'_rows_{cy0:05d}_{cy1:05d}' if args.max_core_rows else '')
  recpath=cp/f'{tile_key}.json';spanpath=cp/f'{tile_key}.assignments.jsonl.gz'
  if args.resume and recpath.exists() and spanpath.exists():
   rec=json.load(open(recpath))
   if rec.get('algorithm_revision')!=REV or rec.get('span_sha256')!=sha(spanpath):raise ValueError(f'checkpoint mismatch: {recpath}')
   done.append(rec);continue
  cx0=tx*TX;cx1=min(W,cx0+TX);y0=max(0,cy0-PADY);y1=min(H,cy1+PADY)
  latmax=max(abs(90-y0*STEP),abs(90-y1*STEP));cosx=max(1e-5,math.cos(math.radians(latmax)));padx=int(math.ceil((BAND+2000)/(111195*cosx*STEP)))+4;padx=min(padx,W//3);x0=cx0-padx;x1=cx1+padx;h=y1-y0;w=x1-x0
  p=np.empty((h,w),np.uint8);lab=np.empty_like(p)
  for iy,y in enumerate(range(y0,y1)):p[iy]=geom.crop(pr,pu,y,x0,x1);lab[iy]=geom.crop(vr,vu,y,x0,x1)
  edges=geom.extract_edges(p,lab,x0,y0);edges['_category_values']=np.unique(edges['category']) if len(edges['mids']) else np.empty(0,np.uint8);tree=cKDTree(edges['mids'],compact_nodes=True,balanced_tree=True) if len(edges['mids']) else None
  rec=run_tile((by,tx,cy0,cy1) if args.max_core_rows else (by,tx),(cy0,cy1),(cx0,cx1),p,lab,(y0,y1,x0,x1),edges,tree,run,None,args.kd_workers);done.append(rec)
  print(f'tile {i}/{len(tiles)} {by},{tx}: water={rec["physical_water_centers"]:,} screen={rec["screened_water_centers"]:,} assigned={rec["fresh_band_assigned_cells"]:,} exact={rec["exact_nearest_checks"]:,} RSS={rec.get("peak_rss_mib",0):.0f}MiB elapsed={time.time()-t0:.1f}s',flush=True)
  del p,lab,edges,tree
 # Rebuild aggregated gzip files solely from closed checkpoint spans.
 tmp=run/'coastal-band-assignments.jsonl.gz.tmp';final=run/'coastal-band-assignments.jsonl.gz';tile_manifest=[];counts={str(c):0 for c in range(1,7)};assigned=screened=exact=water=0;maxrss=0
 with gzip.open(tmp,'wt') as out:
  for rec in done:
   sp=cp/rec['span_file']
   with gzip.open(sp,'rt') as f:
    for line in f:
     out.write(line)
     d=json.loads(line)
     for span in d['spans']:counts[str(span['code'])]+=span['end']-span['start']
   assigned+=rec['fresh_band_assigned_cells'];screened+=rec.get('screened_water_centers',0);exact+=rec.get('exact_nearest_checks',0);water+=rec.get('physical_water_centers',0);maxrss=max(maxrss,float(rec.get('peak_rss_mib',0)))
   tile_manifest.append({'tile':rec['tile'],'y_start':rec['core_rows'][0],'y_end_exclusive':rec['core_rows'][1],
       'x_start':rec.get('core_cols',[0,W])[0],'x_end_exclusive':rec.get('core_cols',[0,W])[1],
       'path':'completed-tiles/'+rec['span_file'],'sha256':rec['span_sha256'],'span_count':rec.get('span_count',0),
       'assigned_cells':rec['fresh_band_assigned_cells'],'code_counts':rec['assigned_cells_by_code'],
       'screened_water_centers':rec.get('screened_water_centers',0),'exact_nearest_checks':rec.get('exact_nearest_checks',0)})
 tmp.replace(final)
 edge_water=0
 for y in range(max(0,H-PADY),H):edge_water+=int(np.count_nonzero(geom.expand_row(pr,pu,y)==1))
 v6land_fingerprint=hashlib.sha256((inputs['v6_rows_sha256']+':'+inputs['v6_runs_sha256']).encode()).hexdigest()
 summary={'schema':'worldatlas-full-water-assignment-tiles-v1','layer_id':'coastal_band_nearest_final_shore','status':'partial_shard' if args.partial_shard else 'complete_full_stored_grid_with_edge_domain_note_no_grid_mutation',
  'grid':{'width':W,'height':H,'step_deg':STEP,'cell_center_lon':'-180+(x+0.5)*360/W','cell_center_lat':'90-(y+0.5)*360/W','coordinate_rule':'lon=-180+(x+0.5)*360/W; lat=90-(y+0.5)*360/W','south_limit':'60S'},
 'coverage':{'kind':'physical-water-centers-within-22.224km-final-shore','physical_mask_sha256':inputs['physical_mask_sha256'],'v6_land_rle_sha256':v6land_fingerprint,'complete':not args.partial_shard,'complete_within_domain':not args.partial_shard,
      'domain':'All physical-water cell centers in the stored V6/physical grid; nearest-shore support is evaluated within that declared model domain.','edge_truncation':{'south_rows':[max(0,H-PADY),H],'physical_water_centers':edge_water,'note':'The model grid ends at 60S. In-domain nearest-shore results are used for every stored cell; no external geography beyond the raster is inferred.'},
      'outside_band':'Omitted for downstream named-basin, ocean, and inland-water composition.'},
  'source_hashes':{'v6_rows_u32le_sha256':inputs['v6_rows_sha256'],'v6_runs_u32le_sha256':inputs['v6_runs_sha256'],'v6_land_rle_sha256':v6land_fingerprint,'physical_rows_u32_sha256':inputs['physical_rows_sha256'],'physical_runs_u32_sha256':inputs['physical_runs_sha256'],'physical_mask_sha256':inputs['physical_mask_sha256'],'algorithm_sha256':inputs['algorithm_sha256'],'shore_helper_sha256':inputs['shore_helper_sha256'],'coast_census_cache_sha256':inputs['coast_census_cache_sha256']},
  'assignment_rule':{'rule_id':RULE,'list2_reason':'final-continent-nearest-shore-within-22.224km','water_input':'physical-mask code 1 only; ignore all existing V6 water codes 1..10','land_input':'final V6 assigned land codes 17..22 only where physical mask code is 17; destination water code is land_code−16','band_m':BAND,'source_geometry':'exact nearest exposed physical-land grid-edge segment','earth_radius_m':R,'support_method':'Spherical midpoint half-segment lower/upper intervals certify nearest category and band membership; exact spherical segment-distance fallback for class/band ambiguity; EDT serves only as conservative shortlist.'},
  'coverage_semantics':'Each output span is one physical-water cell-center within 22,224 m of its nearest final assigned land shore. All supported centers in the declared domain are assigned once to the nearest shore continent, irrespective of legacy V6 water class. Cells outside the band are deliberately omitted for later basin/ocean/inland composition.',
  'tile_height':TY,'coast_tiles':len(coast),'candidate_core_tiles':len(tiles),'tile_count_including_polar':len(done),'physical_water_centers_across_candidate_cores':water,'screened_water_centers':screened,'fresh_band_assigned_cells':assigned,'fresh_band_assigned_cells_by_code':counts,'exact_nearest_checks':exact,'peak_tile_rss_mib':maxrss,'elapsed_seconds':time.time()-t0,'span_count':sum(int(t.get('span_count',0)) for t in done),'assignment_file':final.name,'assignment_sha256':sha(final),'water_code_legend':{'1':'Africa','2':'Asia','3':'Europe','4':'North America','5':'South America','6':'Oceania'},'member_ids_by_code':{str(c):f'coastal-water-nearest-final-land-category-{c}' for c in range(1,7)},'source_rule_refs':['source-verified final V6 land assignment codes 17–22','pinned physical OSM mask code 1 water / 17 land','approved 22.224 km nearest-final-shore rule'],'legacy_comparison':'Existing V6 water codes may be compared only after this output is complete; they are not inputs to target assignments.',
  'shard':{'tile_start':args.tile_start,'tile_step':args.tile_step,'partial':args.partial_shard,'skipped_polar':args.skip_polar},'tiles':tile_manifest}
 summary['manifest_sha256_excluding_self']=hashlib.sha256(json.dumps(summary,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 write_json(run/'manifest.json',summary)
 # Mark complete in the same manifest after the aggregate and digest are stable.
 print(json.dumps({k:summary[k] for k in ('status','candidate_core_tiles','tile_count_including_polar','fresh_band_assigned_cells','fresh_band_assigned_cells_by_code','screened_water_centers','exact_nearest_checks','peak_tile_rss_mib','elapsed_seconds','assignment_sha256')},indent=2),flush=True)
if __name__=='__main__':main()

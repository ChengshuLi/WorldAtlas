#!/usr/bin/env python3
"""Fresh full-source named-basin continent assignment spans, using final land shore only."""
import argparse,gzip,hashlib,json,math,os,time
from pathlib import Path
from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path('/workspace/scratch/127991fc8b8e')
BASE=Path(__file__).resolve().parent
INV=ROOT/'water_rebuild_input_inventory_20261103.json'
OUT=BASE/'named-basin-assignments'
BY=OUT/'by-source';BY.mkdir(parents=True,exist_ok=True)
W,H=131072,54614;STEP=360.0/W;R=6371008.8;PAD_DEG=8.0
PH=ROOT/'recovered-tmp/worldatlas-v5-recovery/raw'
V6=Path('/tmp/v6-aegean-final-publication-20261103/final-candidate-grid-root-approved-v3')
import sys
COAST=ROOT/'worldatlas-v6-satellite-fix-20261102/audit/full-coastal-band-regen-20261103/rebuild_full_coastal_band.py'
sys.path.insert(0,str(COAST.parent))
import rebuild_full_coastal_band as coastal
geom=coastal.geom

CONT={1:'africa',2:'asia',3:'europe',4:'north-america',5:'south-america',6:'oceania'}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def read_blob(p):
 b=Path(p).read_bytes()
 return json.loads(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b),b

def source_records(inv):
 out=[]
 for b in inv['seavox_named_basins']:
  a=b['full_source_mask_artifacts'][0]
  codes=sorted({int(p['water_code']) for p in b['participants']})
  out.append({'id':str(b['source_id']),'name':b['source_name'],'participants':codes,'policy':b['assignment_policy'],'path':a['path'],'sha256':a['sha256'],'family':'SeaVoX v19','source':b})
 other={z['source_id']:z for z in inv['other_named_basin_sources']}
 for key,slug,sourceid in [('cenderawasih','cenderawasih','teluk-cenderawasih-water-to-oceania-v2'),('gulf-of-carpentaria','gulf_of_carpentaria','ga-topographic-base-map:other-waters:gulf-carpentaria-413')]:
  d=other[sourceid];a=inv['custom_basin_source_masks'][slug]['source_mask_artifact']
  out.append({'id':d['source_id'],'name':d['source_name'],'participants':[int(p['water_code']) for p in d['participants']],'policy':d['assignment_policy'],'path':a['path'],'sha256':a['sha256'],'family':'approved custom basin','source':d})
 return out

def read_spans(source):
 payload,raw=read_blob(source['path'])
 if hashlib.sha256(raw).hexdigest()!=source['sha256']:raise ValueError(f'{source["id"]}: source mask SHA mismatch')
 spans=payload.get('spans')
 out=defaultdict(list);cells=0
 for q in spans:
  if isinstance(q,dict): y=int(q['row']);a=int(q.get('start',q.get('start_x')));b=int(q.get('end',q.get('end_x')))
  else:y,a,b=map(int,q[:3])
  if not(0<=y<H and 0<=a<b<=W):raise ValueError(f'{source["id"]}: bad span {q}')
  out[y].append((a,b));cells+=b-a
 for y in out:
  out[y].sort()
 return out,cells,payload

def circ_bbox(span_maps):
 allints=[];ys=[]
 for sm in span_maps:
  for y,ints in sm.items():
   ys.append(y);allints.extend(ints)
 if not allints:raise ValueError('empty source masks')
 allints.sort();merged=[]
 for a,b in allints:
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
  else:merged.append((a,b))
 if len(merged)==1 and merged[0]==(0,W):return 0,W,min(ys),max(ys)+1
 gaps=[]
 for i,(a,b) in enumerate(merged[:-1]):gaps.append((merged[i+1][0]-b,i))
 gaps.append((merged[0][0]+W-merged[-1][1],len(merged)-1))
 gap,i=max(gaps)
 width=W-gap
 if width>=W-1:return 0,W,min(ys),max(ys)+1
 if i==len(merged)-1:xs=merged[0][0];xe=merged[-1][1]
 else:xs=merged[i+1][0];xe=merged[i][1]+W
 return xs,xe,min(ys),max(ys)+1

def crop_for_group(srcs,spanmaps,pad_deg=PAD_DEG):
 xa,xb,ya,yb=circ_bbox(spanmaps);pad=math.ceil(pad_deg/STEP)
 x0=xa-pad;x1=xb+pad
 if x1-x0>=W:x0,x1=0,W
 y0=max(0,ya-pad);y1=min(H,yb+pad)
 return x0,x1,y0,y1

def add_part(parts,la0,lo0,la1,lo1,kind,cats):
 n=len(cats)
 if n:parts.append((np.asarray(la0,dtype=np.float64),np.asarray(lo0,dtype=np.float64),np.asarray(la1,dtype=np.float64),np.asarray(lo1,dtype=np.float64),np.full(n,kind,dtype=np.uint8),np.asarray(cats,dtype=np.uint8)))

def grouped_intervals(indices,cats):
 if not len(indices):return []
 cuts=np.r_[0,np.flatnonzero((np.diff(indices)>1)|(cats[1:]!=cats[:-1]))+1,len(indices)]
 return [(int(indices[a]),int(indices[b-1])+1,int(cats[a])) for a,b in zip(cuts[:-1],cuts[1:])]

def build_edges(x0,x1,y0,y1,codes,pr,pu,lr,lu):
 parts=[];w=x1-x0;wanted=np.asarray(sorted(codes),dtype=np.uint8);prevp=prevl=None;ns=0
 for y in range(max(0,y0-1),min(H,y1+1)):
  p=geom.crop(pr,pu,y,x0,x1);lab=geom.crop(lr,lu,y,x0,x1)
  dry=(p==17)&(lab>=17)&(lab<=22);cat=(lab-16).astype(np.uint8)
  top=90-y*STEP;bot=top-STEP
  if y<y1:
   # Meridional shoreline edges inside each row.
   m=np.zeros(w,dtype=bool);m[1:]=dry[1:]&(p[:-1]==1)&np.isin(cat[1:],wanted)
   ix=np.flatnonzero(m);c=cat[ix]
   if len(ix):
    lon=-180+(x0+ix)*STEP;add_part(parts,np.full(len(ix),top),lon,np.full(len(ix),bot),lon,0,c);ns+=len(ix)
   m=np.zeros(w,dtype=bool);m[:-1]=dry[:-1]&(p[1:]==1)&np.isin(cat[:-1],wanted)
   ix=np.flatnonzero(m);c=cat[ix]
   if len(ix):
    lon=-180+(x0+ix+1)*STEP;add_part(parts,np.full(len(ix),top),lon,np.full(len(ix),bot),lon,0,c);ns+=len(ix)
  # Parallel edge between previous row and y.
  if prevp is not None:
   lat=90-y*STEP
   mask=(prevp==17)&(p==1)&np.isin((prevl-16).astype(np.uint8),wanted)
   idx=np.flatnonzero(mask);cats=(prevl[idx]-16).astype(np.uint8)
   for a,b,c in grouped_intervals(idx,cats):
    lo=-180+(x0+a)*STEP;hi=-180+(x0+b)*STEP
    add_part(parts,[lat],[lo],[lat],[hi],1,[c]);ns+=1
   mask=(prevp==1)&(p==17)&np.isin((lab-16).astype(np.uint8),wanted)
   idx=np.flatnonzero(mask);cats=(lab[idx]-16).astype(np.uint8)
   for a,b,c in grouped_intervals(idx,cats):
    lo=-180+(x0+a)*STEP;hi=-180+(x0+b)*STEP
    add_part(parts,[lat],[lo],[lat],[hi],1,[c]);ns+=1
  prevp,prevl=p,lab
 edges=geom.edge_data(parts)
 cats=np.unique(edges['category']) if len(edges['mids']) else np.empty(0,np.uint8)
 edges['_category_values']=cats
 return edges,ns

def boundary_lower(lat,lon,x0,x1,y0,y1):
 latr=np.deg2rad(lat);lonr=np.deg2rad(lon);d=np.full(len(lat),np.inf,dtype=np.float64)
 if y0>0:
  north=90-y0*STEP;d=np.minimum(d,np.abs(lat-north)*(math.pi/180)*R)
 if y1<H:
  south=90-y1*STEP;d=np.minimum(d,np.abs(lat-south)*(math.pi/180)*R)
 if x1-x0<W:
  west=-180+x0*STEP;east=-180+x1*STEP
  # Lower bound to any point on each omitted meridian plane; crop width is <180°.
  for lam in (west,east):
   dot=np.abs(np.cos(latr)*np.sin(lonr-math.radians(lam)))
   d=np.minimum(d,R*np.arcsin(np.clip(dot,0,1)))
 return d

def classify(points,lat,lon,bd,edges,tree,codes,class_edges,class_trees,exact_batch=512):
 n=len(points);upper_by={};lower_by={};maxhalf={c:float(class_edges[c]['half_lengths'].max()) for c in codes}
 # Each participant class has its own shoreline index. The nearest midpoint
 # gives a valid upper bound using that selected segment's half length; the
 # class-wide maximum half length gives a conservative lower bound for every
 # segment of that class. This avoids global-k class omission and limits exact
 # work to unresolved class bisectors.
 for c in codes:
  data=class_edges[c];ct=class_trees[c]
  chord,idx=ct.query(points,k=1,workers=1)
  mid=2*R*np.arcsin(np.clip(chord/2,0,1));half=data['half_lengths'][idx]
  upper=mid+half
  lower=np.maximum(0.0,mid-maxhalf[c])
  lower=np.minimum(lower,bd)
  upper_by[c]=upper;lower_by[c]=lower
 u=np.column_stack([upper_by[c] for c in codes]);l=np.column_stack([lower_by[c] for c in codes])
 best=np.argmin(u,axis=1);target=np.asarray(codes,dtype=np.uint8)[best];best_u=u[np.arange(n),best]
 other=l.copy();other[np.arange(n),best]=np.inf;other_l=other.min(axis=1)
 cert=(best_u+1e-5<other_l)&(best_u+1e-5<bd)
 out=target.copy();exact=np.zeros(n,dtype=bool);dist_upper=best_u.copy();bad=~cert
 if np.any(bad):
  badix=np.flatnonzero(bad);nclass=len(codes)
  for st in range(0,len(badix),exact_batch):
   sel=badix[st:st+exact_batch];pd=points[sel];la=lat[sel];lo0=lon[sel]
   distances=np.empty((len(sel),nclass),dtype=np.float64)
   for ci,c in enumerate(codes):
    d,_,_=geom.nearest(pd,la,lo0,class_edges[c],tree=class_trees[c],maxhalf=maxhalf[c],workers=1)
    distances[:,ci]=d
   mins=distances.min(axis=1);eligible=distances<=mins[:,None]+1e-5
   ranks=np.where(eligible,np.asarray(codes,dtype=np.uint8)[None,:],255)
   chosen=ranks.argmin(axis=1);out[sel]=np.asarray(codes,dtype=np.uint8)[chosen];dist_upper[sel]=mins;exact[sel]=True
  invalid=dist_upper[bad]+1e-5>=bd[bad]
  if np.any(invalid):
   return out,exact,dist_upper,int(np.count_nonzero(invalid)),int(np.count_nonzero(cert))
 return out,exact,dist_upper,0,int(np.count_nonzero(cert))

def assigned_member(source,code):
 if source['family']=='approved custom basin':return source['id']
 if source['policy']=='shared_nearest_assigned_shore':return f"seavox-v19-mrgid-sr-{source['id']}-nearest-{CONT[code]}"
 return f"seavox-v19-mrgid-sr-{source['id']}"
def rule_for(source):
 if source['id']=='teluk-cenderawasih-water-to-oceania-v2':return 'approved-cenderawasih-source-bounded-component-v1'
 if source['id']=='ga-topographic-base-map:other-waters:gulf-carpentaria-413':return 'approved-gulf-carpentaria-whole-source-v1'
 if len(source['participants'])>1:return 'approved-named-basin-nearest-final-shore-v1'
 return 'approved-named-basin-direct-continent-v1'

def write_source_direct(source,sm,out_path):
 code=source['participants'][0];rule=rule_for(source);member=assigned_member(source,code);n=0;rows=0
 with gzip.open(out_path,'wt',encoding='utf8',compresslevel=6) as f:
  for y,ints in sorted(sm.items()):
   spans=[]
   for a,b in ints:
    if spans and spans[-1]['end']==a and spans[-1]['code']==code and spans[-1]['member_id']==member:spans[-1]['end']=b
    else:spans.append({'start':a,'end':b,'code':code,'rule_id':rule,'member_id':member})
    n+=b-a
   if spans:f.write(json.dumps({'row':int(y),'spans':spans},separators=(',',':'))+'\n');rows+=1
 return {'source_id':source['id'],'source_name':source['name'],'method':'direct-fill single approved participant','assigned_cells_by_code':{str(code):n},'assigned_cells':n,'output_path':str(out_path),'output_sha256':sha(out_path),'output_bytes':out_path.stat().st_size,'row_count':rows,'span_count':sum(len(v) for v in sm.values())}

def unwrapped_rows(sm,x0,x1):
 for y,ints in sorted(sm.items()):
  vals=[]
  for a,b in ints:
   for k in (-1,0,1):
    aa,bb=a+k*W,b+k*W;lo=max(aa,x0);hi=min(bb,x1)
    if hi>lo:vals.append((lo,hi))
  vals.sort()
  if vals:yield y,vals

def write_shared(source,sm,x0,x1,y0,y1,edges,tree,codes,class_edges,class_trees,out_path,chunk=5000):
 rule=rule_for(source);cell_counts=defaultdict(int);exactn=certn=badn=rows=spanc=0;worst=0.0;maxbd=0.0
 tmp=out_path.with_suffix(out_path.suffix+'.tmp')
 with gzip.open(tmp,'wt',encoding='utf8',compresslevel=6) as f:
  for y,ints in unwrapped_rows(sm,x0,x1):
   latc=90-(y+.5)*STEP;latrow=np.empty(0);rowsp=[]
   for a,b in ints:
    for st in range(a,b,chunk):
     en=min(st+chunk,b);xx=np.arange(st,en,dtype=np.float64)
     lat=np.full(len(xx),latc);lon=-180+(xx+.5)*STEP
     bd=boundary_lower(lat,lon,x0,x1,y0,y1);pts=geom.unit(lat,lon)
     codes_out,exact,dist,invalid,certn0=classify(pts,lat,lon,bd,edges,tree,codes,class_edges,class_trees)
     badn+=invalid;certn+=certn0;exactn+=int(exact.sum())
     if invalid:
      raise RuntimeError(f'{source["id"]}: local-shore crop cannot certify {invalid} cells (pad={PAD_DEG}); expand crop before assignment')
     if len(dist):worst=max(worst,float(dist.max()));maxbd=max(maxbd,float(bd.max()))
     # Emit code-coalesced intervals. Wrap unwrapped columns back to the native cyclic grid.
     cuts=np.r_[0,np.flatnonzero((np.diff(codes_out)!=0))+1,len(codes_out)]
     for ia,ib in zip(cuts[:-1],cuts[1:]):
      code=int(codes_out[ia]);start=int(st+ia);end=int(st+ib);cell_counts[code]+=ib-ia
      parts=[]
      cur=start
      while cur<end:
       boundary=((cur//W)+1)*W;stop=min(end,boundary)
       gx=cur%W;ge=gx+(stop-cur)
       parts.append((gx,ge,code))
       cur=stop
      for gx,ge,c in parts:
       member=assigned_member(source,c)
       if rowsp and rowsp[-1]['end']==gx and rowsp[-1]['code']==c and rowsp[-1]['member_id']==member:rowsp[-1]['end']=ge
       else:rowsp.append({'start':gx,'end':ge,'code':c,'rule_id':rule,'member_id':member})
   if rowsp:
    rowsp.sort(key=lambda z:z['start'])
    # Merge any same-code contiguous runs after cyclic split; reject overlapping output spans.
    merged=[]
    for z in rowsp:
     if merged and z['start']<merged[-1]['end']:raise ValueError(f'{source["id"]}: duplicate/unwrapped overlap row {y}: {z}')
     if merged and z['start']==merged[-1]['end'] and z['code']==merged[-1]['code'] and z['member_id']==merged[-1]['member_id']:merged[-1]['end']=z['end']
     else:merged.append(z)
    f.write(json.dumps({'row':int(y),'spans':merged},separators=(',',':'))+'\n');rows+=1;spanc+=len(merged)
 tmp.replace(out_path)
 return {'source_id':source['id'],'source_name':source['name'],'method':'nearest final assigned shore among approved participant classes; segment-midpoint interval bounds with exact spherical segment checks for unresolved cells','participant_codes':codes,'assigned_cells_by_code':{str(k):int(v) for k,v in sorted(cell_counts.items())},'assigned_cells':int(sum(cell_counts.values())),'certified_cells':int(certn),'exact_nearest_cells':exactn,'crop_boundary_uncertified_cells':badn,'max_candidate_distance_m':worst,'max_crop_boundary_lower_bound_m':maxbd,'crop_bounds':[x0,x1,y0,y1],'shore_segments':len(edges['mids']),'max_half_segment_m':float(edges['half_lengths'].max()),'output_path':str(out_path),'output_sha256':sha(out_path),'output_bytes':out_path.stat().st_size,'output_rows':rows,'output_spans':spanc}

def merge_source_files(sources,stats,out_dir):
 import heapq
 files=[]
 for s in sources:
  path=BY/f'source-{s["id"].replace(":","_")}.jsonl.gz'
  if not path.exists():raise FileNotFoundError(path)
  files.append((s,path))
 def gen(src,path):
  with gzip.open(path,'rt',encoding='utf8') as f:
   for line in f:
    q=json.loads(line);yield (int(q['row']),src['id'],q['spans'])
 streams=[gen(s,p) for s,p in files]
 merged=heapq.merge(*streams,key=lambda z:(z[0],z[1]))
 priority=lambda sid: 2 if sid=='ga-topographic-base-map:other-waters:gulf-carpentaria-413' else 1
 output=out_dir/'named-basin-assignment-rows.jsonl.gz';tmp=output.with_suffix('.jsonl.gz.tmp')
 byid=defaultdict(lambda:defaultdict(int));codecounts=defaultdict(int);covered=overwritten=0;conflict_rows=[];rowcount=span_count=0;cur_y=None;row_sources=[]
 def flush(y,row_sources,fh):
  nonlocal covered,overwritten,span_count,rowcount
  # Turn intervals into winner events, preserving stable source ownership.
  events=defaultdict(lambda:[[],[]]);items=[]
  for sid,spans in row_sources:
   for z in spans:
    a,b,c=int(z['start']),int(z['end']),int(z['code'])
    events[a][1].append((sid,z));events[b][0].append((sid,z))
  if not events:return
  xs=sorted(events);active={};out=[]
  for k,x in enumerate(xs[:-1]):
   for sid,z in events[x][0]:active.pop((sid,id(z)),None)
   for sid,z in events[x][1]:active[(sid,id(z))]=(sid,z)
   en=xs[k+1]
   if en<=x or not active:continue
   vals=list(active.values());chosen=max(vals,key=lambda t:(priority(t[0]),t[0]))
   sid,z=chosen;code=int(z['code']);member=z['member_id'];rule=z['rule_id']
   if len(vals)>1:
    losers=[(u,v) for u,v in vals if u!=sid or v is not z]
    if any(priority(u)==priority(sid) and int(v['code'])!=code for u,v in losers):raise ValueError(f'ambiguous source overlap row={y} x={x}:{en}: {[(u,v["code"]) for u,v in vals]}')
    overwritten+=en-x
   covered+=en-x;byid[sid][code]+=en-x;codecounts[code]+=en-x
   if out and out[-1]['end']==x and out[-1]['code']==code and out[-1]['member_id']==member:out[-1]['end']=en
   else:out.append({'start':x,'end':en,'code':code,'rule_id':rule,'member_id':member})
  # Ensure final intervals are non-overlapping.
  for aa,bb in zip(out,out[1:]):
   if aa['end']>bb['start']:raise ValueError(f'compositor produced overlap row={y}')
  fh.write(json.dumps({'row':y,'spans':out},separators=(',',':'))+'\n');span_count+=len(out);rowcount+=1
 with gzip.open(tmp,'wt',encoding='utf8',compresslevel=6) as fh:
  for y,sid,spans in merged:
   if cur_y is None:cur_y=y
   if y!=cur_y:flush(cur_y,row_sources,fh);cur_y=y;row_sources=[]
   row_sources.append((sid,spans))
  if cur_y is not None:flush(cur_y,row_sources,fh)
 tmp.replace(output)
 # Recompute source cell counts before overlap to report overwritten cells accurately.
 pre_counts=defaultdict(int)
 for s,path in files:
  with gzip.open(path,'rt',encoding='utf8') as fh:
   for line in fh:
    q=json.loads(line)
    for z in q['spans']:pre_counts[s['id']]+=int(z['end'])-int(z['start'])
 report={'schema':'worldatlas-named-basin-assignment-audit-v1','status':'completed_candidate_not_published','grid':{'width':W,'height':H,'step_degrees':STEP,'row_convention':'north-to-south; cell centers; spans half-open'},'input_manifest_path':str(INV),'input_manifest_sha256':sha(INV),'physical_mask_sha256':'660ac7608f72b447c95eb8820979951fe589f25c70303efe732b374049127017','final_land_rows_path':str(V6/'rows.u32le'),'final_land_rows_sha256':sha(V6/'rows.u32le'),'final_land_runs_path':str(V6/'runs.u32le'),'final_land_runs_sha256':sha(V6/'runs.u32le'),'prior_water_labels_read':'none','source_layers':stats,'overlap_precedence':[{'winner':'ga-topographic-base-map:other-waters:gulf-carpentaria-413','loser':'seavox-v19-mrgid-sr-24065','rule':'approved full Gulf of Carpentaria source polygon is more specific; code 6 wins only within the measured 1,176-cell intersection'}],'pre_resolved_source_overlap_cells':overwritten,'assigned_unique_named_basin_water_cells':covered,'assigned_cells_by_code':{str(k):int(v) for k,v in sorted(codecounts.items())},'unique_source_cells_before_overlap_precedence':sum(pre_counts.values()),'source_assignments_before_overlap':{sid:{str(c):n for c,n in d.items()} for sid,d in pre_counts.items()},'output':{'path':str(output),'sha256':sha(output),'bytes':output.stat().st_size,'sparse_rows':True,'row_count':rowcount,'span_count':span_count},'sources_count':len(sources),'shore_method':'Per participant-class shoreline indexes are built from physical code-17 land adjacent to physical code-1 water, labeled by final V6 land codes 17–22 only. Segment midpoint lower/upper bounds certify the nearest participant class; unresolved bisector cells use exact spherical point-to-segment distances. Crop boundary lower bounds prove the local shore index contains the global nearest shore for every assignment; any failure aborts.'}
 return report

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--only-group',default=None);ap.add_argument('--skip-direct',action='store_true');ap.add_argument('--skip-merge',action='store_true');ap.add_argument('--merge-only',action='store_true');ap.add_argument('--pad-deg',type=float,default=8.0);ap.add_argument('--chunk',type=int,default=5000);a=ap.parse_args()
 PAD_DEG=float(a.pad_deg)
 inv=json.load(open(INV));srcs=source_records(inv)
 prp=PH/'physical-rows.u32';pup=PH/'physical-runs.u32';lrp=V6/'rows.u32le';lup=V6/'runs.u32le'
 pr=np.memmap(prp,dtype='<u4',mode='r',shape=(H+1,));pu=np.memmap(pup,dtype='<u4',mode='r');lr=np.memmap(lrp,dtype='<u4',mode='r',shape=(H+1,));lu=np.memmap(lup,dtype='<u4',mode='r')
 print(json.dumps({'phase':'loaded','sources':len(srcs),'direct':sum(len(s['participants'])==1 for s in srcs),'shared':sum(len(s['participants'])>1 for s in srcs),'mask_hash':sha(INV)}),flush=True)
 masks={};cells={}
 for s in srcs:masks[s['id']],cells[s['id']],_=read_spans(s)
 stats=[]
 if not a.skip_direct:
  for s in srcs:
   if len(s['participants'])==1:
    path=BY/f'source-{s["id"].replace(":","_")}.jsonl.gz'
    q=write_source_direct(s,masks[s['id']],path);stats.append(q);print(json.dumps({'phase':'direct-done',**{k:q[k] for k in ('source_id','assigned_cells','output_sha256')}}),flush=True)
 groups=defaultdict(list)
 for s in srcs:
  if len(s['participants'])>1:groups[tuple(s['participants'])].append(s)
 group_stats={}
 for codes,gs in sorted(groups.items()):
  if a.merge_only: break
  key=','.join(map(str,codes))
  if a.only_group and key!=a.only_group:continue
  x0,x1,y0,y1=crop_for_group(gs,[masks[s['id']] for s in gs],PAD_DEG)
  print(json.dumps({'phase':'build-group-index','codes':codes,'basins':[s['id'] for s in gs],'crop':[x0,x1,y0,y1],'pad_deg':PAD_DEG}),flush=True)
  edges,added=build_edges(x0,x1,y0,y1,set(codes),pr,pu,lr,lu)
  if not len(edges['mids']) or not set(codes).issubset(set(map(int,edges['_category_values']))):
   have=list(map(int,edges['_category_values']));raise RuntimeError(f'group {codes} missing participant shoreline categories {set(codes)-set(have)}; have={have}, crop={x0,x1,y0,y1}')
  tree=None
  class_edges={};class_trees={}
  for c in codes:
   mask=edges['category']==c
   class_edges[c]={k:edges[k][mask] for k in ('mids','lat0','lon0','lat1','lon1','kind','half_lengths','category')}
   class_trees[c]=cKDTree(class_edges[c]['mids'],compact_nodes=True,balanced_tree=True)
  gstat={'participant_codes':list(codes),'crop_bounds':[x0,x1,y0,y1],'shore_segments':len(edges['mids']),'edge_runs_added':added,'max_half_by_code':{str(c):float(edges['half_lengths'][edges['category']==c].max()) for c in codes},'basins':[]}
  for s in gs:
   path=BY/f'source-{s["id"].replace(":","_")}.jsonl.gz'
   q=write_shared(s,masks[s['id']],x0,x1,y0,y1,edges,tree,codes,class_edges,class_trees,path,a.chunk);gstat['basins'].append(q);stats.append(q)
   print(json.dumps({'phase':'shared-done','source_id':s['id'],'assigned_cells':q['assigned_cells'],'certified':q['certified_cells'],'exact':q['exact_nearest_cells'],'boundary_fail':q['crop_boundary_uncertified_cells'],'output_sha256':q['output_sha256']}),flush=True)
  group_stats[key]=gstat
  del tree,class_trees,class_edges,edges
 if a.only_group:
  Path(OUT/f'partial-group-stats-{a.only_group.replace(",","_")}.json').write_text(json.dumps({'input_inventory_sha256':sha(INV),'group_stats':group_stats,'basin_stats':stats},indent=2)+'\n')
  return
 if a.skip_merge:return
 if a.merge_only:
  # Rehydrate per-basin run statistics and shared-index QA from completed group sidecars.
  for sf in sorted(OUT.glob('partial-group-stats-*.json')):
   z=json.loads(sf.read_text());group_stats.update(z.get('group_stats',{}));stats.extend(z.get('basin_stats',[]))
  stat_ids={x['source_id'] for x in stats}
  # Direct sources are cheap to summarize from their completed output spans.
  for ss in srcs:
   if ss['id'] in stat_ids: continue
   if len(ss['participants'])!=1: continue
   fp=BY/f'source-{ss["id"].replace(":","_")}.jsonl.gz'; counts=defaultdict(int); rows_n=spans_n=0
   with gzip.open(fp,'rt',encoding='utf8') as fh:
    for line in fh:
     q=json.loads(line);rows_n+=1;spans_n+=len(q['spans'])
     for zz in q['spans']:counts[int(zz['code'])]+=int(zz['end'])-int(zz['start'])
   stats.append({'source_id':ss['id'],'source_name':ss['name'],'method':'direct-fill single approved participant','assigned_cells_by_code':{str(k):int(v) for k,v in counts.items()},'assigned_cells':int(sum(counts.values())),'output_path':str(fp),'output_sha256':sha(fp),'output_bytes':fp.stat().st_size,'row_count':rows_n,'span_count':spans_n})
 # Ensure every source generated assignment files.
 if len(list(BY.glob('source-*.jsonl.gz')))!=len(srcs):raise RuntimeError('not all per-source assignment rows are present')
 report=merge_source_files(srcs,stats,OUT)
 report['shore_index_groups']=group_stats
 qa_path=BASE/'source-mask-integrity-qa.json';overlap_path=ROOT/'water-rebuild-source-masks/full-approved-mask-overlaps.json'
 report['source_mask_integrity_qa']={'path':str(qa_path),'sha256':sha(qa_path)}
 report['source_mask_overlap_audit']={'path':str(overlap_path),'sha256':sha(overlap_path)}
 report['approved_source_inventory']=[{'source_id':s['id'],'source_name':s['name'],'family':s['family'],'participants':s['participants'],'assignment_policy':s['policy'],'full_source_mask_path':s['path'],'full_source_mask_sha256':s['sha256'],'source_geometry_path':(s['source'].get('full_source_geometry_candidates',[{}])[0].get('path') if s['family']=='SeaVoX v19' else s['source'].get('full_source_geometry',{}).get('path')),'source_geometry_file_sha256':(s['source'].get('full_source_geometry_candidates',[{}])[0].get('file_sha256') if s['family']=='SeaVoX v19' else s['source'].get('full_source_geometry',{}).get('file_sha256')),'source_geometry_sha256':(s['source'].get('full_source_geometry_candidates',[{}])[0].get('geometry_sha256_canonical_json') if s['family']=='SeaVoX v19' else s['source'].get('full_source_geometry',{}).get('geometry_sha256') or s['source'].get('full_source_geometry',{}).get('geojson_geometry_sha256'))} for s in srcs]
 report['direct_or_single_participant_sources']=sum(1 for s in srcs if len(s['participants'])==1)
 report['multi_participant_shared_sources']=sum(1 for s in srcs if len(s['participants'])>1)
 report['algorithm_script_sha256']=sha(Path(__file__))
 report['final_candidate_water_codes_read']='land only (17–22); no V6 water labels read or inherited.'
 outman=OUT/'assignment-audit.json';outman.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
 tile=report['output']['path'];rel=Path(tile).name
 layer={'schema':'worldatlas-full-water-assignment-tiles-v1','status':'completed_candidate_not_published','grid':{'width':W,'height':H,'angular_step_deg':STEP,'row_convention':'north-to-south; cell centers; half-open [start,end) x spans'},'coverage':{'complete':True,'meaning':'complete set of assignments for the union of the 91 approved SeaVoX basin source-water masks plus approved Cenderawasih and whole Carpentaria source-water masks; rows omitted from sparse JSONL have no named-basin assignment'},'precedence':{'before_coastal_and_ocean_fill':True,'internal_source_overlap':'Carpentaria source code 6 overrides Arafura only at the measured 1,176-cell overlap; no other source-polygon mask overlaps found.'},'source_assignment_rules':{'single_participant':'fill directly to the sole approved continent water code','shared_participant':'nearest final assigned continental shore among only the approved participant classes; final V6 code 17–22 on physical land 17 only; midpoint interval bounds with exact spherical segment checks for unresolved points','nearest_tie':'exact equal-distance/10-micrometre tie follows existing spherical_shore deterministic lower stable category code'},'input_pins':{'inventory_sha256':report['input_manifest_sha256'],'physical_mask_sha256':report['physical_mask_sha256'],'final_land_rows_sha256':report['final_land_rows_sha256'],'final_land_runs_sha256':report['final_land_runs_sha256']},'provenance':{'assignment_audit':'assignment-audit.json','assignment_audit_sha256':sha(outman),'input_inventory_path':str(INV),'input_inventory_sha256':sha(INV),'physical_mask_sha256':report['physical_mask_sha256'],'source_mask_integrity_qa_path':report['source_mask_integrity_qa']['path'],'source_mask_integrity_qa_sha256':report['source_mask_integrity_qa']['sha256'],'source_overlap_audit_path':report['source_mask_overlap_audit']['path'],'source_overlap_audit_sha256':report['source_mask_overlap_audit']['sha256'],'prior_water_labels_read':'none'},'source_layers':report['approved_source_inventory'],'tiles':[{'core_rows':[0,H],'span_file':{'path':rel,'sha256':report['output']['sha256']},'core_cols':[0,W]}]}
 layerp=OUT/'layer-manifest.json';layerp.write_text(json.dumps(layer,indent=2)+'\n')
 print(json.dumps({'phase':'complete','layer_manifest':str(layerp),'layer_sha256':sha(layerp),'assignment_audit':str(outman),'audit_sha256':sha(outman),'unique_cells':report['assigned_unique_named_basin_water_cells'],'overwritten_overlap_cells':report['pre_resolved_source_overlap_cells'],'code_counts':report['assigned_cells_by_code'],'file_sha256':report['output']['sha256']}),flush=True)
if __name__=='__main__':main()

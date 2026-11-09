#!/usr/bin/env python3
"""Run-segment flood fill for fresh ocean labels, independent of old labels.

Eligibility is supplied as row-wise half-open intervals of physical marine water
remaining after authoritative coast/continental/named-basin/inland exclusions.
Barriers are cuts between adjacent cell centers, never unassigned cells. The
engine is proportional to interval count, not grid-cell count; it stores node
intervals to a binary spool and uses compact uint32 union-find arrays.
"""
from __future__ import annotations
from array import array
from bisect import bisect_left, bisect_right
from collections import defaultdict, Counter
from pathlib import Path
from exclusive_outputs import create_binary_exclusive, create_directory_exclusive, create_gzip_text_exclusive, create_text_exclusive, create_run_directory, write_json_exclusive
import hashlib, json, math, struct

class CutEdges:
    """Blocked four-neighbor graph edges. H: (row,x)-(row,x+1); V: (row,x)-(row+1,x)."""
    def __init__(self):
        self.horizontal=defaultdict(set)
        self.vertical=defaultdict(set)
        self.wrap=set()  # blocks (x=W-1) <-> (x=0) on this row
    def add_h(self,y,x):self.horizontal[int(y)].add(int(x))
    def add_v(self,y,x):self.vertical[int(y)].add(int(x))
    def add_wrap(self,y):self.wrap.add(int(y))
    def as_dict(self):
        return {'horizontal':{str(y):sorted(xs) for y,xs in sorted(self.horizontal.items()) if xs},
                'vertical':{str(y):sorted(xs) for y,xs in sorted(self.vertical.items()) if xs},
                'wrap':sorted(self.wrap)}

    def write_u32le(self,path):
        """Serialize unique cut edges as (kind,row,x) uint32 triples."""
        records=[]
        for y,xs in self.horizontal.items():records.extend((0,y,x) for x in xs)
        for y,xs in self.vertical.items():records.extend((1,y,x) for x in xs)
        records.extend((2,y,0) for y in self.wrap)
        records.sort()
        with create_binary_exclusive(path) as f:
            for k,y,x in records:f.write(struct.pack('<III',k,y,x))
        return len(records)
    @classmethod
    def read_u32le(cls,path):
        cuts=cls();data=Path(path).read_bytes()
        if len(data)%12:raise ValueError('cut edge file length is not a multiple of 12 bytes')
        for k,y,x in struct.iter_unpack('<III',data):
            if k==0:cuts.add_h(y,x)
            elif k==1:cuts.add_v(y,x)
            elif k==2:cuts.add_wrap(y)
            else:raise ValueError(f'unknown cut edge kind {k}')
        return cuts

CLASS_LABELS={1:'Africa water',2:'Asia water',3:'Europe water',4:'North America water',5:'South America water',6:'Oceania water',
  17:'Africa land',18:'Asia land',19:'Europe land',20:'North America land',21:'South America land',22:'Oceania land'}

def _cross(ax,ay,bx,by):return ax*by-ay*bx

def _point_on_segment(p,a,b,eps=1e-10):
    px,py=p;ax,ay=a;bx,by=b;dx=bx-ax;dy=by-ay
    if abs(_cross(dx,dy,px-ax,py-ay))>eps*max(1.0,abs(dx)+abs(dy)):return False
    dot=(px-ax)*dx+(py-ay)*dy;ll=dx*dx+dy*dy
    return -eps<=dot<=ll+eps

def _intersection_nonvertex(p,q,a,b,eps=1e-10):
    """True iff line segment pq intersects edge ab away from a/b graph vertices.

    Intersections at cell-center graph vertices are handled by the deterministic
    tie rule in rasterize_barriers. A source edge overlapping an entire graph
    edge is also assigned by those endpoint ties, so it is not cut here.
    """
    px,py=p;qx,qy=q;ax,ay=a;bx,by=b
    rx,ry=qx-px,qy-py;sx,sy=bx-ax,by-ay
    den=_cross(rx,ry,sx,sy);apx,apy=ax-px,ay-py
    if abs(den)<=eps:
        if abs(_cross(apx,apy,rx,ry))>eps*max(1.0,abs(rx)+abs(ry)):return False
        rr=rx*rx+ry*ry
        if rr==0:return False
        t0=(apx*rx+apy*ry)/rr;t1=((bx-px)*rx+(by-py)*ry)/rr
        lo=max(0.0,min(t0,t1));hi=min(1.0,max(t0,t1))
        if hi<lo-eps:return False
        # If both edge endpoints are on the source route, use the vertex tie.
        if _point_on_segment(a,p,q,eps) and _point_on_segment(b,p,q,eps):return False
        # Any positive-length partial overlap or a touch of edge interior is a cut.
        return hi-lo>eps or (lo>=-eps and lo<=1+eps and
          (eps < min(abs(lo),abs(1-lo)) or _point_on_segment(p,a,b,eps) or _point_on_segment(q,a,b,eps)))
    t=_cross(apx,apy,sx,sy)/den;u=_cross(apx,apy,rx,ry)/den
    if t < -eps or t > 1+eps or u < -eps or u > 1+eps:return False
    ix=px+t*rx;iy=py+t*ry
    # A graph-center endpoint hit is deferred to the tie handler.
    if (math.hypot(ix-ax,iy-ay)<=eps or math.hypot(ix-bx,iy-by)<=eps):return False
    return True

def rasterize_barriers(paths,width,height,eps=1e-10):
    """Convert polyline paths in grid-edge (x,y) coordinates into blocked graph edges.

    At a source-line hit on a cell-center graph vertex, the tie cell is assigned
    to the left side of the oriented route; only edges to its right-side
    neighbors are blocked. This prevents diagonal leakage without dropping any
    cell. Shared boundary-aligned cell-center edges stay connected on that same
    tie side. Paths are expected to be longitude-unwrapped and may not cross the
    antimeridian; no supplied ocean partition barrier does so.
    """
    cuts=CutEdges();tie_vectors=defaultdict(lambda:[0.0,0.0])
    for path in paths:
        pts=[(float(x),float(y)) for x,y in path]
        for p,q in zip(pts,pts[1:]):
            x0,y0=p;x1,y1=q;dx=x1-x0;dy=y1-y0
            if abs(dx)+abs(dy)<=eps:continue
            # Collect graph-center vertices on the route; store oriented tangents.
            ix0=math.ceil(min(x0,x1)-.5-eps);ix1=math.floor(max(x0,x1)-.5+eps)
            iy0=math.ceil(min(y0,y1)-.5-eps);iy1=math.floor(max(y0,y1)-.5+eps)
            for iy in range(iy0,iy1+1):
                cy=iy+.5
                for ix in range(ix0,ix1+1):
                    cx=ix+.5
                    if _point_on_segment((cx,cy),p,q,eps):
                        v=tie_vectors[(ix,iy)];v[0]+=dx;v[1]+=dy
            # Candidate east/west graph edges, endpoints at cell centers.
            j0=max(0,math.ceil(min(y0,y1)-.5-eps));j1=min(height-1,math.floor(max(y0,y1)-.5+eps))
            i0=max(0,math.floor(min(x0,x1)-1.5));i1=min(width-2,math.ceil(max(x0,x1)-.5))
            for j in range(j0,j1+1):
                yy=j+.5
                for i in range(i0,i1+1):
                    a=(i+.5,yy);b=(i+1.5,yy)
                    if _intersection_nonvertex(p,q,a,b,eps):cuts.add_h(j,i)
            # Candidate north/south graph edges.
            i0=max(0,math.ceil(min(x0,x1)-.5-eps));i1=min(width-1,math.floor(max(x0,x1)-.5+eps))
            j0=max(0,math.floor(min(y0,y1)-1.5));j1=min(height-2,math.ceil(max(y0,y1)-.5))
            for i in range(i0,i1+1):
                xx=i+.5
                for j in range(j0,j1+1):
                    a=(xx,j+.5);b=(xx,j+1.5)
                    if _intersection_nonvertex(p,q,a,b,eps):cuts.add_v(j,i)
    # Deterministic graph-vertex tie handling after tangents have been combined.
    for (ix,iy),(dx,dy) in tie_vectors.items():
        if abs(dx)+abs(dy)<=eps:continue
        cx,cy=ix+.5,iy+.5
        for ox,oy in ((-1,0),(1,0),(0,-1),(0,1)):
            nx,ny=cx+ox,cy+oy
            side=_cross(dx,dy,nx-cx,ny-cy)
            if side>=-eps:continue  # keep left/on-line neighbors in same tie class
            if ox==1 and 0<=ix<width-1:cuts.add_h(iy,ix)
            elif ox==-1 and 0<=ix-1<width-1:cuts.add_h(iy,ix-1)
            elif oy==1 and 0<=iy<height-1:cuts.add_v(iy,ix)
            elif oy==-1 and 0<=iy-1<height-1:cuts.add_v(iy-1,ix)
    return cuts

def split_eligible(intervals,blocked_edges,width):
    """Split [x0,x1) eligible intervals wherever a horizontal neighbor is cut."""
    out=[]
    for a,b in intervals:
        if not (0<=a<b<=width):raise ValueError(f'invalid eligible interval {(a,b)}')
        i=bisect_left(blocked_edges,a);j=bisect_left(blocked_edges,b-1)
        start=a
        for edge in blocked_edges[i:j]:
            out.append((start,edge+1));start=edge+1
        if start<b:out.append((start,b))
    return out

class _DSU:
    def __init__(self):self.parent=array('I');self.size=array('I')
    def add(self):
        i=len(self.parent)
        if i>=0xffffffff:raise OverflowError('run-node count exceeds uint32 DSU capacity')
        self.parent.append(i);self.size.append(1);return i
    def find(self,x):
        p=self.parent
        while p[x]!=x:
            p[x]=p[p[x]];x=p[x]
        return x
    def union(self,a,b):
        ra=self.find(a);rb=self.find(b)
        if ra==rb:return
        if self.size[ra]<self.size[rb]:ra,rb=rb,ra
        self.parent[rb]=ra;self.size[ra]+=self.size[rb]

def _blocked_count(sorted_x,lo,hi):return bisect_left(sorted_x,hi)-bisect_left(sorted_x,lo)

def floodfill_run_graph(eligible_rows,width,height,cuts,seeds,workdir,*,manifest_inputs=None,unassigned_policy='report-only',required_seed_codes=(7,8,9,10),classification_rows=None,seed_metadata=None):
    """Flood fill eligible RLE intervals and emit sparse fresh ocean spans.

    `eligible_rows(y)` returns sorted, disjoint `[x_start,x_end)` intervals for
    residual marine water. `seeds` maps ocean code to `(x,y)`. Writes:
      node_intervals.bin: (x_start,x_end,node_id) uint32 records, row-major
      node_rows.u64le: row offset indices into node_intervals.bin, length H+1
      ocean_assignment_spans.u32le: (x_start,x_end,ocean_code) uint32 records
      ocean_rows.u64le: row offset indices into ocean spans, length H+1
      unseeded_component_spans.u32le: (x_start,x_end,component_root) records
      unseeded_rows.u64le: row offsets
      manifest.json: counts and unseeded-component summaries.
    No source ocean-label raster is read; each eligible component gets its code
    only from a supplied verified seed. Unseeded components are left separate.
    """
    if set(seeds)!=set(required_seed_codes):raise ValueError(f'expected seed codes {sorted(required_seed_codes)}; got {sorted(seeds)}')
    workdir=Path(workdir);create_directory_exclusive(workdir)
    dsu=_DSU();row_offsets=array('Q',[0]);prev=[];seed_nodes={};eligible_cells=0
    node_path=workdir/'node_intervals.bin'
    with create_binary_exclusive(node_path) as nf:
        for y in range(height):
            raw=list(eligible_rows(y))
            if raw!=sorted(raw) or any(raw[i][1]>raw[i+1][0] for i in range(len(raw)-1)):
                raise ValueError(f'eligible intervals not sorted/disjoint on row {y}')
            hcuts=sorted(cuts.horizontal.get(y,()))
            pieces=split_eligible(raw,hcuts,width)
            cur=[]
            for a,b in pieces:
                nid=dsu.add();cur.append((a,b,nid));eligible_cells+=b-a
                for code,(sx,sy) in seeds.items():
                    if sy==y and a<=sx<b:
                        if code in seed_nodes:raise ValueError(f'seed {code} occurs in more than one node')
                        seed_nodes[code]=nid
            if prev:
                ycuts=sorted(cuts.vertical.get(y-1,()))
                i=j=0
                while i<len(prev) and j<len(cur):
                    pa,pb,pid=prev[i];ca,cb,cid=cur[j];lo=max(pa,ca);hi=min(pb,cb)
                    if lo<hi and hi-lo>_blocked_count(ycuts,lo,hi):dsu.union(pid,cid)
                    if pb<=cb:i+=1
                    if cb<=pb:j+=1
            if cur and cur[0][0]==0 and cur[-1][1]==width and y not in cuts.wrap:
                dsu.union(cur[0][2],cur[-1][2])
            for a,b,nid in cur:nf.write(struct.pack('<III',a,b,nid))
            row_offsets.append(len(dsu.parent));prev=cur
    if set(seed_nodes)!=set(seeds):
        missing=sorted(set(seeds)-set(seed_nodes));raise ValueError(f'seed cells are not in eligible marine mask: {missing}')
    seed_roots={}
    for code,nid in seed_nodes.items():
        root=dsu.find(nid)
        if root in seed_roots and seed_roots[root]!=code:
            raise ValueError(f'different ocean seeds share one connected component: {seed_roots[root]} and {code}')
        seed_roots[root]=code
    # Root-level component summary and sizes; no grid expansion.
    comp=defaultdict(lambda:{'cell_count':0,'node_count':0,'row_min':height,'row_max':-1,'x_min':width,'x_max':0,'adjacent_class_cells':Counter(),
                             'source_barrier_contact_edge_count':0,'adjacent_seeded_ocean_codes_across_source_barriers':Counter()})
    class_cache={}
    def class_row(y):
        if classification_rows is None or not (0<=y<height):return ([],[])
        if y not in class_cache:
            runs=list(classification_rows(y));class_cache[y]=(runs,[e for e,_ in runs])
        return class_cache[y]
    def add_class_overlap(root,row_data,lo,hi):
        if lo>=hi:return
        runs,ends=row_data;i=bisect_right(ends,lo);pos=ends[i-1] if i else 0
        while i<len(runs):
            end,code=runs[i]
            n=max(0,min(hi,end)-max(lo,pos))
            if n and code!=0:comp[root]['adjacent_class_cells'][str(code)]+=n
            pos=end
            if pos>=hi:break
            i+=1
    def class_at(row_data,x):
        if x<0 or x>=width:return None
        runs,ends=row_data;i=bisect_right(ends,x)
        return runs[i][1] if i<len(runs) else None
    with node_path.open('rb') as nf:
        rec_idx=0;previous_nodes=[]
        for y in range(height):
            class_cache.clear()
            nf.seek(row_offsets[y]*12)
            nrow=row_offsets[y+1]-row_offsets[y]
            current_nodes=[]
            for _ in range(nrow):
                a,b,nid=struct.unpack('<III',nf.read(12));root=dsu.find(nid);s=comp[root]
                current_nodes.append((a,b,nid,root))
                s['cell_count']+=b-a;s['node_count']+=1;s['row_min']=min(s['row_min'],y);s['row_max']=max(s['row_max'],y);s['x_min']=min(s['x_min'],a);s['x_max']=max(s['x_max'],b)
                if classification_rows is not None and root not in seed_roots:
                    add_class_overlap(root,class_row(y-1),a,b);add_class_overlap(root,class_row(y+1),a,b)
                    for xx in (a-1,b):
                        if xx<0:
                            if y not in cuts.wrap:xx=width-1
                            else:continue
                        elif xx>=width:
                            if y not in cuts.wrap:xx=0
                            else:continue
                        cc=class_at(class_row(y),xx)
                        if cc is not None and cc!=0:comp[root]['adjacent_class_cells'][str(cc)]+=1
                rec_idx+=1
            # Retain diagnostic adjacency across source cuts. These are separate
            # graph components by design, not automatically inland pockets.
            def note_cut_contact(root_a,root_b):
                if root_a==root_b:return
                for root,other in ((root_a,root_b),(root_b,root_a)):
                    s=comp[root];s['source_barrier_contact_edge_count']+=1
                    other_code=seed_roots.get(other)
                    if other_code is not None:s['adjacent_seeded_ocean_codes_across_source_barriers'][str(other_code)]+=1
            hcuts=set(cuts.horizontal.get(y,()))
            for left,right in zip(current_nodes,current_nodes[1:]):
                if left[1]==right[0] and left[1]-1 in hcuts:note_cut_contact(left[3],right[3])
            if y:
                ycuts=sorted(cuts.vertical.get(y-1,()))
                i=j=0
                while i<len(previous_nodes) and j<len(current_nodes):
                    pa,pb,_,pr=previous_nodes[i];ca,cb,_,cr=current_nodes[j];lo=max(pa,ca);hi=min(pb,cb)
                    if lo<hi and pr!=cr:
                        k=bisect_left(ycuts,lo)
                        while k<len(ycuts) and ycuts[k]<hi:note_cut_contact(pr,cr);k+=1
                    if pb<=cb:i+=1
                    if cb<=pb:j+=1
            if y in cuts.wrap and previous_nodes is not None and current_nodes:
                if current_nodes[0][0]==0 and current_nodes[-1][1]==width:
                    note_cut_contact(current_nodes[0][3],current_nodes[-1][3])
            previous_nodes=current_nodes
    # Emit sparse row spans for seeded ocean components and separate residual components.
    ocean_rows=array('Q',[0]);residual_rows=array('Q',[0]);counts=Counter();out_spans=0;res_spans=0
    with node_path.open('rb') as nf,create_binary_exclusive(workdir/'ocean_assignment_spans.u32le') as of,create_binary_exclusive(workdir/'unseeded_component_spans.u32le') as uf:
        for y in range(height):
            nf.seek(row_offsets[y]*12);nrow=row_offsets[y+1]-row_offsets[y]
            ocean_row=[];res_row=[]
            for _ in range(nrow):
                a,b,nid=struct.unpack('<III',nf.read(12));root=dsu.find(nid);code=seed_roots.get(root)
                if code is None:res_row.append((a,b,root))
                else:ocean_row.append((a,b,code));counts[code]+=b-a
            # Merge adjacent output spans when the class/component is the same.
            for rowspans,fobj in ((ocean_row,of),(res_row,uf)):
                merged=[]
                for s in rowspans:
                    if merged and merged[-1][1]==s[0] and merged[-1][2]==s[2]:merged[-1]=(merged[-1][0],s[1],s[2])
                    else:merged.append(s)
                for a,b,c in merged:fobj.write(struct.pack('<III',a,b,c))
                if fobj is of:out_spans+=len(merged)
                else:res_spans+=len(merged)
            ocean_rows.append(out_spans);residual_rows.append(res_spans)
    def write_u64le(path,values):
        with create_binary_exclusive(path) as f:
            for v in values:f.write(struct.pack('<Q',int(v)))
    write_u64le(workdir/'node_rows.u64le',row_offsets)
    write_u64le(workdir/'ocean_rows.u64le',ocean_rows)
    write_u64le(workdir/'unseeded_rows.u64le',residual_rows)
    comps=[]
    for root,s in comp.items():
        adjacent_seeded=sorted(map(int,s['adjacent_seeded_ocean_codes_across_source_barriers']))
        adjacent_classes=sorted(map(int,s['adjacent_class_cells']))
        if len(adjacent_seeded)==1 and not adjacent_classes:
            resolution_hint='source-cut-isolated-ocean-parent-candidate'
        elif len(adjacent_seeded)>1:
            resolution_hint='source-cut-isolated-multiple-ocean-adjacencies-review'
        elif len(adjacent_seeded)==1:
            resolution_hint='source-cut-isolated-ocean-with-shore-contact-review'
        elif s['source_barrier_contact_edge_count']:
            resolution_hint='source-cut-contact-without-seeded-parent-review'
        elif not adjacent_seeded and adjacent_classes:
            resolution_hint='shore-or-continental-water-adjacency-pocket-review'
        else:
            resolution_hint='unresolved-component-review'
        s.update({'component_root':root,'ocean_code':seed_roots.get(root),'ocean_label':{7:'Atlantic',8:'Pacific',9:'Indian',10:'Arctic'}.get(seed_roots.get(root)),
                  'longitude_bounds_edges':[-180+s['x_min']*360/width,-180+s['x_max']*360/width],
                  'latitude_bounds_centers':[90-(s['row_min']+.5)*360/width,90-(s['row_max']+.5)*360/width],
                  'adjacent_class_cells':dict(sorted(s['adjacent_class_cells'].items())),
                  'adjacent_class_label_counts':{CLASS_LABELS.get(int(k),f'code-{k}'):v for k,v in sorted(s['adjacent_class_cells'].items(),key=lambda kv:int(kv[0]))},
                  'adjacent_noneligible_class_edge_counts':dict(sorted(s['adjacent_class_cells'].items())),
                  'adjacent_noneligible_class_edge_label_counts':{CLASS_LABELS.get(int(k),f'code-{k}'):v for k,v in sorted(s['adjacent_class_cells'].items(),key=lambda kv:int(kv[0]))},
                  'adjacent_seeded_ocean_codes_across_source_barriers':dict(sorted(s['adjacent_seeded_ocean_codes_across_source_barriers'].items())),
                  'source_barrier_contact_edge_count':s['source_barrier_contact_edge_count'],
                  'resolution_hint':resolution_hint,
                  'provisional_ocean_parent_code':adjacent_seeded[0] if len(adjacent_seeded)==1 else None})
        comps.append(s)
    comps.sort(key=lambda x:(x['ocean_code'] is None,-x['cell_count'],x['component_root']))
    assigned_total=sum(counts.values());unseeded_total=sum(s['cell_count'] for s in comps if s['ocean_code'] is None)
    if assigned_total+unseeded_total!=eligible_cells:raise AssertionError(f'cell conservation failed: assigned {assigned_total} + residual {unseeded_total} != eligible {eligible_cells}')
    manifest={'schema':'fresh-ocean-run-partition-v1','status':'proposal-only','grid':{'W':width,'H':height,'angular_step_degrees':360/width,'rows_included':[0,height-1]},
      'inputs':manifest_inputs or {},'method':'Run-segment four-neighbor connected components over residual physical marine mask. Source boundaries block crossed cell-center adjacency edges. Longitude wrap is enabled except where an explicit barrier blocks it. Only the four verified seed cells assign ocean codes; no previous ocean-label raster is used.',
      'seed_cells':{str(code):{'x':xy[0],'y':xy[1],'longitude_center':-180+(xy[0]+.5)*360/width,'latitude_center':90-(xy[1]+.5)*360/width,**(seed_metadata or {}).get(code,{})} for code,xy in seeds.items()},
      'physical_class_code_labels':{str(k):v for k,v in CLASS_LABELS.items()},
      'barrier_edge_counts':{'horizontal':sum(map(len,cuts.horizontal.values())),'vertical':sum(map(len,cuts.vertical.values())),'wrap':len(cuts.wrap)},
      'eligible_water_cells':eligible_cells,'assigned_cells_by_ocean_code':{str(k):counts[k] for k in (7,8,9,10)},'assigned_cells_total':sum(counts.values()),
      'ocean_assignment_span_count':out_spans,'unseeded_cell_count':sum(s['cell_count'] for s in comps if s['ocean_code'] is None),'unseeded_span_count':res_spans,
      'unseeded_component_policy':unassigned_policy,'components':comps,
      'outputs':{'node_intervals':'node_intervals.bin','node_rows':'node_rows.u64le','ocean_spans':'ocean_assignment_spans.u32le','ocean_rows':'ocean_rows.u64le','unseeded_spans':'unseeded_component_spans.u32le','unseeded_rows':'unseeded_rows.u64le'}}
    write_json_exclusive(workdir/'manifest.json',manifest)
    return manifest

def export_jsonl_tiles(workdir,width,height,*,tile_height=256,manifest_inputs=None,rule_id='fresh-ocean-seed-floodfill-v1'):
    """Stream complete row-interval JSONL tiles from the sparse binary spans.

    Each tile has one JSON line per row including empty rows. Span end is
    exclusive. This is an interchange/export layer; binary row spans remain the
    compact authoritative candidate.
    """
    workdir=Path(workdir);offset_bytes=(workdir/'ocean_rows.u64le').read_bytes()
    offsets=struct.unpack('<%dQ'%(height+1),offset_bytes)
    out_manifest={'schema':'fresh-ocean-jsonl-tiles-v1','grid':{'W':width,'H':height,'row_start':0,'row_end_exclusive':height},
      'inputs':manifest_inputs or {},'rule_id':rule_id,'member_ids':{'7':'ocean-seed-7-atlantic','8':'ocean-seed-8-pacific','9':'ocean-seed-9-indian','10':'ocean-seed-10-arctic'},'tiles':[]}
    span_path=workdir/'ocean_assignment_spans.u32le'
    with span_path.open('rb') as sf:
        for y0 in range(0,height,tile_height):
            y1=min(height,y0+tile_height);path=workdir/f'ocean-assignment-rows-{y0:06d}-{y1:06d}.jsonl';counts=Counter();nspans=0;ncells=0
            with create_text_exclusive(path,encoding='utf-8',newline='\n') as out:
                for y in range(y0,y1):
                    out_spans=[];a=offsets[y];b=offsets[y+1]
                    sf.seek(a*12)
                    for _ in range(b-a):
                        x0,x1,code=struct.unpack('<III',sf.read(12));n=x1-x0;counts[code]+=n;ncells+=n;nspans+=1
                        out_spans.append({'start':x0,'end':x1,'code':code,'rule_id':rule_id,'member_id':out_manifest['member_ids'][str(code)]})
                    out.write(json.dumps({'row':y,'spans':out_spans},separators=(',',':'))+'\n')
            digest=hashlib.sha256(path.read_bytes()).hexdigest()
            out_manifest['tiles'].append({'path':path.name,'sha256':digest,'row_start':y0,'row_end_exclusive':y1,'row_count':y1-y0,'span_count':nspans,'cell_count':ncells,'cell_counts_by_code':{str(k):counts[k] for k in sorted(counts)}})
    out_manifest['row_coverage_complete']=sum(t['row_count'] for t in out_manifest['tiles'])==height
    out_manifest['tile_count']=len(out_manifest['tiles'])
    mpath=workdir/'tile_manifest.json';write_json_exclusive(mpath,out_manifest)
    return out_manifest

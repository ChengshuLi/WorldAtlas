"""Correct source-verified sea limits without replacing native coastlines.

Only overhangs connected to the existing surrounding ocean are removed. Interior
shoreline-source differences remain bounded water. Inputs are research artifacts.
"""
import argparse,gzip,hashlib,json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
import shapefile
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.spatial import cKDTree
from shapely.geometry import shape,mapping,box
from correct_suez import xyz
from sea_families import child_rules,OPEN_WATERS

def ocean_connected_overhang(points,seeds,width):
    """Four-edge flood on changed cells only; unrelated inland gaps are retained."""
    pending=set(points);connected=set();stack=list(seeds&pending)
    for p in stack:pending.remove(p)
    while stack:
        p=stack.pop();connected.add(p);y,x=divmod(p,width)
        for q in (p-width,p+width,y*width+(x-1)%width,y*width+(x+1)%width):
            if q in pending:pending.remove(q);stack.append(q)
    return connected

def build(parent,output,source,references,coasts,proposal_id):
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((parent/'proposal.json').read_text());w,h,s=m['width'],m['height'],m['step']
    R=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');V=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
    @lru_cache(maxsize=8)
    def row(y):
        z=V[R[y]:R[y+1]];return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
    c=np.load(coasts);tree=cKDTree(xyz(*c['coordinates'].T));groups=c['groups'];limit=2*np.sin(22.224/(2*6371.0088))
    marine={f.record.as_dict()['name']:shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(source)).iterShapeRecords()}
    active=(set(m['shared_seas'])|{n for a in m['continent_seas'].values() for n in a}|set(child_rules()))-OPEN_WATERS
    config=json.loads(references.read_text());rules=config['rules'];new={};hashes={}
    for rule in rules:
        p=references.parent/rule['file'];raw=p.read_bytes();new[rule['name']]=shape(json.loads(raw)['geometry']);hashes[rule['name']]=hashlib.sha256(raw).hexdigest()
    changes={};audits=[]
    for rule in rules:
        name=rule['name'];old=marine[name];g=new[name];we,so,ea,no=old.union(g).bounds
        if name=='Bering Sea':no=min(no,60) # The northern gateway is separately verified.
        x0=max(0,int((we+180)/s)-1);x1=min(w,int((ea+180)/s)+2);y0=max(0,int((90-no)/s)-1);y1=min(h,int((90-so)/s)+2)
        xs=np.arange(x0,x1);lo=-180+(xs+.5)*s;others=[new.get(n,z) for n,z in marine.items() if n in active and n!=name and z.intersects(box(we,so,ea,no))]
        removed=set();added={}
        for y in range(y0,y1,64):
            end=min(y+64,y1);a=np.array([row(yy)[xs] for yy in range(y,end)]);tf=from_origin(-180+x0*s,90-y*s,s,s)
            def mask(shapes):
                return rasterize(shapes,out_shape=a.shape,transform=tf,dtype='uint8')>0 if shapes else np.zeros_like(a,dtype=bool)
            om=mask([(mapping(old),1)]);nm=mask([(mapping(g),1)]);other=mask([(mapping(z),1) for z in others if z.bounds[3]>=90-end*s and z.bounds[1]<=90-y*s])
            take=(a>=7)&(a<=10)&nm;drop=(a>=1)&(a<=6)&om&~nm&~other;rr,cc=np.where(take|drop)
            if not len(rr):continue
            q=xyz(lo[cc],90-(y+rr+.5)*s);d,ix=tree.query(q,workers=4);far=d>limit;rr,cc,ix=rr[far],cc[far],ix[far]
            for yy,xx,ii in zip(rr,cc,ix):
                key=int((y+yy)*w+xs[xx])
                if drop[yy,xx]:removed.add(key)
                else:added[key]=int(groups[ii]) if rule['group']==99 else rule['group']
        seeds=set();wrong_seeds=set();byrow=defaultdict(list)
        for p in removed:y,x=divmod(p,w);byrow[y].append(x)
        for y,xx in sorted(byrow.items()):
            xx=np.array(xx);neighbors=np.array([row(y)[(xx-1)%w],row(y)[(xx+1)%w],row(max(0,y-1))[xx],row(min(h-1,y+1))[xx]])
            expected=(neighbors==rule['outside_ocean']).any(axis=0);wrong=((neighbors>=7)&(neighbors<=10)&(neighbors!=rule['outside_ocean'])).any(axis=0)
            seeds.update(int(y*w+x) for x in xx[expected]);wrong_seeds.update(int(y*w+x) for x in xx[wrong])
        connected=ocean_connected_overhang(removed,seeds,w)
        assert not (connected&wrong_seeds),(name,'overhang touches a different ocean')
        updates={p:rule['outside_ocean'] for p in connected};updates.update(added)
        for p,value in updates.items():
            assert p not in changes or changes[p]==value,(name,p,'conflicting sea corrections')
            changes[p]=value
        audit={'name':name,'published_limit':rule['limit'],'section':rule['section'],'reference_sha256':hashes[name],'ocean_connected_overhang_cells':len(connected),'interior_source_mismatch_cells_retained':len(removed-connected),'ocean_cells_added_to_bounded_sea':len(added)};audits.append(audit);print(json.dumps(audit),flush=True)
    byrow=defaultdict(list)
    for p,value in changes.items():y,x=divmod(p,w);byrow[y].append((x,value))
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        old=row(y);a=old.copy()
        for x,value in byrow[y]:a[x]=value
        assert np.array_equal(a>=16,old>=16);assert np.array_equal(a[old>=16],old[old>=16])
        sha.update((a&15).tobytes());display.update(a.tobytes());counts+=np.bincount(a&15,minlength=11)
        ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for n,data in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
    m.update(proposal_id=proposal_id,sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['published_sea_limits_refinement']={'reference':config['reference'],'source_urls':config.get('source_urls',[]),'boundaries':audits,'changed_water_cells':len(changes),'land_changes':0,'raw_source_not_redistributed':True}
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'published-sea-limits-audit.json').write_text(json.dumps(m['published_sea_limits_refinement'],indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','source','references','coasts']:p.add_argument(n,type=Path)
    p.add_argument('--proposal-id',required=True);a=p.parse_args();build(a.parent,a.output,a.source,a.references,a.coasts,a.proposal_id)

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
from shapely.geometry import shape,mapping,box,GeometryCollection
from shapely.ops import unary_union
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
        geometries=[];pins=[]
        for filename in rule.get('files',[rule.get('file')]):
            p=references.parent/filename;raw=p.read_bytes();geometries.append(shape(json.loads(raw)['geometry']));pins.append(hashlib.sha256(raw).hexdigest())
        # Rasterizing equal-valued geometries gives their union without an
        # expensive vector overlay of every detailed shoreline vertex.
        new[rule['name']]=geometries[0] if len(geometries)==1 else GeometryCollection(geometries)
        hashes[rule['name']]=pins[0] if len(pins)==1 else pins
        print('Loaded published reference:',rule['name'],len(geometries),'parts',flush=True)
    changes={};audits=[]
    for rule in rules:
        name=rule['name'];members=set(rule.get('old_members',[name]));old=unary_union([marine[n] for n in members]);g=new[name]
        ob,nb=old.bounds,g.bounds;we,so,ea,no=min(ob[0],nb[0]),min(ob[1],nb[1]),max(ob[2],nb[2]),max(ob[3],nb[3])
        old_mapped,new_mapped=mapping(old),mapping(g)
        if name=='Bering Sea':no=min(no,60) # The northern gateway is separately verified.
        x0=max(0,int((we+180)/s)-1);x1=min(w,int((ea+180)/s)+2);y0=max(0,int((90-no)/s)-1);y1=min(h,int((90-so)/s)+2)
        xs=np.arange(x0,x1);lo=-180+(xs+.5)*s;others=[new.get(n,z) for n,z in marine.items() if n in active and n not in members and z.intersects(box(we,so,ea,no))]
        removed=set();added={}
        for y in range(y0,y1,64):
            end=min(y+64,y1);a=np.array([row(yy)[xs] for yy in range(y,end)]);tf=from_origin(-180+x0*s,90-y*s,s,s)
            def mask(shapes):
                return rasterize(shapes,out_shape=a.shape,transform=tf,dtype='uint8')>0 if shapes else np.zeros_like(a,dtype=bool)
            om=mask([(old_mapped,1)]);nm=mask([(new_mapped,1)]);other=mask([(mapping(z),1) for z in others if z.bounds[3]>=90-end*s and z.bounds[1]<=90-y*s])
            take=(a>=7)&(a<=10)&nm;drop=(a>=1)&(a<=6)&om&~nm&~other;rr,cc=np.where(take|drop)
            if not len(rr):continue
            q=xyz(lo[cc],90-(y+rr+.5)*s);d,ix=tree.query(q,workers=4);far=d>limit;rr,cc,ix=rr[far],cc[far],ix[far]
            for yy,xx,ii in zip(rr,cc,ix):
                key=int((y+yy)*w+xs[xx])
                if drop[yy,xx]:removed.add(key)
                else:added[key]=int(groups[ii]) if rule['group']==99 else rule['group']
            if (y-y0)%512==0:print(name,'row',end,'of',y1,'candidate removals',len(removed),'additions',len(added),flush=True)
        oceans=rule.get('outside_oceans',[rule.get('outside_ocean')]);seeds={o:set() for o in oceans};wrong_seeds=set();byrow=defaultdict(list)
        for p in removed:y,x=divmod(p,w);byrow[y].append(x)
        for y,xx in sorted(byrow.items()):
            xx=np.array(xx);neighbors=np.array([row(y)[(xx-1)%w],row(y)[(xx+1)%w],row(max(0,y-1))[xx],row(min(h-1,y+1))[xx]])
            for ocean in oceans:seeds[ocean].update(int(y*w+x) for x in xx[(neighbors==ocean).any(axis=0)])
            wrong=((neighbors>=7)&(neighbors<=10)&~np.isin(neighbors,oceans)).any(axis=0);wrong_seeds.update(int(y*w+x) for x in xx[wrong])
        connected=set();updates={}
        for ocean in oceans:
            part=ocean_connected_overhang(removed,seeds[ocean],w)
            assert not (part&connected),(name,'one changed component touches multiple parent oceans')
            connected.update(part);updates.update({p:ocean for p in part})
        assert not (connected&wrong_seeds),(name,'overhang touches a different ocean')
        updates.update(added)
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
    if 'published_sea_limits_refinement' in m:m.setdefault('published_sea_limits_batches',[]).append(m['published_sea_limits_refinement'])
    m['published_sea_limits_refinement']={'reference':config['reference'],'source_urls':config.get('source_urls',[]),'boundaries':audits,'changed_water_cells':len(changes),'land_changes':0,'raw_source_not_redistributed':True}
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'published-sea-limits-audit.json').write_text(json.dumps(m['published_sea_limits_refinement'],indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','source','references','coasts']:p.add_argument(n,type=Path)
    p.add_argument('--proposal-id',required=True);a=p.parse_args();build(a.parent,a.output,a.source,a.references,a.coasts,a.proposal_id)

"""Add reviewed dry-land source polygons using the unchanged native center rule.

No minimum-size painting or polygon dilation. Refresh ordinary coastal water and
shared-sea affiliation only where an added land cell becomes the nearest coast.
"""
import argparse, gzip, hashlib, json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
import shapefile
from scipy.spatial import cKDTree
from shapely import contains_xy
from shapely.geometry import shape, box, mapping
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz

def contained_cells(g,w,h,s):
    we,so,ea,no=g.bounds
    xs=np.arange(max(0,int((we+180)/s)-1),min(w,int((ea+180)/s)+2))
    ys=np.arange(max(0,int((90-no)/s)-1),min(h,int((90-so)/s)+2))
    xx,yy=np.meshgrid(xs,ys)
    hit=contains_xy(g,-180+(xx+.5)*s,90-(yy+.5)*s)
    return xx[hit],yy[hit]

def build(parent, output, sources, coasts, marine_source, proposal_id):
    output.mkdir(parents=True, exist_ok=False)
    m=json.loads((parent/'proposal.json').read_text());w,h,s=m['width'],m['height'],m['step'];base_proposal_id=m['proposal_id']
    rb=gzip.decompress((parent/'rows.u32.gz').read_bytes());vb=gzip.decompress((parent/'runs.u32.gz').read_bytes())
    R=np.frombuffer(rb,'<u4');V=np.frombuffer(vb,'<u4').reshape(-1,2)
    @lru_cache(maxsize=16)
    def row(y):
        z=V[R[y]:R[y+1]]
        return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
    land={};records=[];polygons=[]
    source_bytes=sources.read_bytes()
    for f in json.loads(source_bytes)['features']:
        p=f['properties'];g=shape(f['geometry']);group=int(p['atlas_group'])
        assert g.is_valid and g.geom_type in ('Polygon','MultiPolygon') and 1<=group<=6
        xx,yy=contained_cells(g,w,h,s)
        cells=[];existing=0
        for x,y in zip(xx,yy):
            old=int(row(int(y))[x]);key=int(y*w+x)
            if old>=16:
                existing+=1;continue
            assert 1<=old<=10 and (key not in land or land[key]==16+group)
            land[key]=16+group;cells.append([int(x),int(y),old])
        assert cells, (p['name'],'no new source-contained centers; keep as exception or represented')
        records.append({'name':p['name'],'continent':group,'source_url':p['source_url'],
                        'source_contained_centers':len(xx),'already_land':existing,'added_cells':cells})
        polygons.append(g)
    c=np.load(coasts);old_tree=cKDTree(xyz(*c['coordinates'].T))
    keys=np.array(list(land),dtype='int64');ny,nx=np.divmod(keys,w)
    new_xyz=xyz(-180+(nx+.5)*s,90-(ny+.5)*s)
    new_groups=np.array([land[int(k)]&15 for k in keys],dtype='uint8')
    new_tree=cKDTree(new_xyz);limit=2*np.sin(22.224/(2*6371.0088))
    marine={f.record.as_dict()['name']:shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(marine_source)).iterShapeRecords()}
    shared=[g for n,g in marine.items() if n in m['shared_seas'] and any(g.distance(p)<.3 for p in polygons)]
    regions=[]
    for g in polygons:
        we,so,ea,no=g.bounds;dy=22.224/111.195+s;dx=dy/max(.01,np.cos(np.deg2rad(max(abs(so),abs(no))+dy)))
        regions.append((box(we-dx,so-dy,ea+dx,no+dy),False))
    regions.extend((g,True) for g in shared)
    changes=dict(land);water_changes={}
    for g,is_shared in regions:
        we,so,ea,no=g.bounds;x0=max(0,int((we+180)/s)-1);x1=min(w,int((ea+180)/s)+2)
        y0=max(0,int((90-no)/s)-1);y1=min(h,int((90-so)/s)+2);xs=np.arange(x0,x1)
        for y in range(y0,y1,64):
            end=min(y+64,y1);a=np.array([row(yy)[xs] for yy in range(y,end)])
            eligible=(a>=1)&(a<=6 if is_shared else a<=10)
            if is_shared:
                part=g.intersection(box(-180+x0*s,90-end*s,-180+x1*s,90-y*s))
                if part.is_empty:continue
                mask=rasterize([(mapping(part),1)],out_shape=a.shape,transform=from_origin(-180+x0*s,90-y*s,s,s),dtype='uint8')>0
                eligible &= mask
            rr,cc=np.where(eligible)
            if not len(rr):continue
            q=xyz(-180+(xs[cc]+.5)*s,90-(y+rr+.5)*s)
            dn,ix=new_tree.query(q,workers=2);do,io=old_tree.query(q,workers=2)
            win=(dn<do)&((dn<=limit)|is_shared)&(new_groups[ix]!=a[rr,cc])
            for yy,xx,ii in zip(rr[win],xs[cc[win]],ix[win]):
                key=int((y+yy)*w+xx)
                if key not in land:water_changes[key]=int(new_groups[ii])
    changes.update(water_changes);byrow=defaultdict(list)
    for k,v in changes.items():y,x=divmod(k,w);byrow[y].append((x,v))
    offsets=[0];chunks=[];count=0;sha=hashlib.sha256();display=hashlib.sha256();groups=np.zeros(11,dtype='int64')
    for y in range(h):
        old=row(y);a=old.copy()
        for x,v in byrow[y]:a[x]=v
        assert np.array_equal(a[old>=16],old[old>=16])
        assert all(int(y*w+x) in land for x in np.flatnonzero((old<16)&(a>=16)))
        sha.update((a&15).tobytes());display.update(a.tobytes());groups+=np.bincount(a&15,minlength=11)
        ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32')
        pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());count+=len(ends);offsets.append(count)
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,data in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
    m.update(proposal_id=proposal_id,sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=count,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    for g in m['groups']:g['cells']=int(groups[g['id']])
    audit={'proposal_id':proposal_id,'base_proposal_id':base_proposal_id,'source_sha256':hashlib.sha256(source_bytes).hexdigest(),'islands':records,'added_land_cells':len(land),'changed_water_cells':len(water_changes),'rule':'Unchanged center sampling. No dilation or forced cells. Existing land unchanged. Water changes only where new land is the nearest coast, within 22.224 km or an existing shared sea.'}
    if 'important_island_source_additions' in m:
        previous=m['important_island_source_additions'];previous.setdefault('proposal_id',base_proposal_id)
        if previous.get('published_source_file'):previous.setdefault('published_source_uri','/review/'+base_proposal_id+'/'+previous['published_source_file'])
        m.setdefault('important_island_source_batches',[]).append(previous)
    m['important_island_source_additions']=audit
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n')
    (output/'important-island-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'islands':len(records),'added_land_cells':len(land),'changed_water_cells':len(water_changes)}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','sources','coasts','marine_source']:p.add_argument(n,type=Path)
    p.add_argument('--proposal-id',required=True);a=p.parse_args();build(a.parent,a.output,a.sources,a.coasts,a.marine_source,a.proposal_id)

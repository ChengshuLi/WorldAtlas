"""Apply reviewed island groups and regional water corrections to a native grid."""
import argparse, gzip, hashlib, json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from matplotlib.path import Path as PolygonPath
import shapefile

# These boxes select isolated island groups, not surrounding water.
ISLAND_GROUPS = {
    'Mapia': (134.1, .65, 134.5, 1.1),
    'Asia and Ayau islands': (130.7, .15, 131.4, 1.25),
    'Marcus Island': (153.7, 24.1, 154.2, 24.5),
}
# A basin separator through continental land; only ocean-coded cells are changed.
AMERICAS = [(-100,66.55),(-100,25),(-98,19),(-92,17),(-89,15.5),
    (-86,14),(-85,11),(-84,10),(-83,9),(-82.5,8.5),(-81,8.5),
    (-80,8.8),(-79.5,9.1),(-78.5,8.8),(-77.5,7.5),(-76,5),
    (-74,0),(-70,-15),(-68,-30),(-70,-45),(-69,-52),(-67.25,-55.95),(-67.25,-60.01)]
ATLANTIC = PolygonPath(AMERICAS+[(20,-60.01),(20,66.55),AMERICAS[0]])
from correct_suez import SINAI, patch_suez

def xyz(lon,lat):
    lo=np.deg2rad(lon); la=np.deg2rad(lat)
    return np.column_stack((np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)))

def build(parent,source,output):
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((parent/'proposal.json').read_text()); w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),dtype='<u4')
    runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),dtype='<u4').reshape(-1,2)
    def decode(y):
        r=runs[rows[y]:rows[y+1]]
        return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
    def region(bounds):
        west,south,east,north=bounds
        x0,x1=int((west+180)/step),int((east+180)/step)+1
        y0,y1=int((90-north)/step),int((90-south)/step)+1
        a=np.array([decode(y)[x0:x1] for y in range(y0,y1)])
        return x0,y0,a
    patches=[]; audit={'island_land_changes':{},'water_changes':{},'egypt_land_changes':0}
    # Correct land first, then build coast searches from the corrected groups.
    x0,y0,a=region((118,-12,160,33)); before=a.copy()
    lon=-180+(x0+np.arange(a.shape[1])+.5)*step
    lat=90-(y0+np.arange(a.shape[0])+.5)*step
    for name,(west,south,east,north) in ISLAND_GROUPS.items():
        mask=(lat[:,None]>=south)&(lat[:,None]<=north)&(lon[None,:]>=west)&(lon[None,:]<=east)&(a==18)
        audit['island_land_changes'][name]=int(mask.sum());a[mask]=22
    edge=(a>=16)&~binary_erosion(a>=16)
    rr,cc=np.where(edge&np.isin(a&15,[2,6]))
    shore_groups=a[rr,cc]&15;tree=cKDTree(xyz(lon[cc],lat[rr]))
    seas=[]
    for sr in shapefile.Reader(str(source/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():
        if sr.record.as_dict()['name'] not in ['Philippine Sea','Banda Sea','Arafura Sea']:continue
        starts=list(sr.shape.parts)+[len(sr.shape.points)]
        seas.extend(PolygonPath(sr.shape.points[s:e]) for s,e in zip(starts,starts[1:]))
    for start in range(0,a.shape[0],64):
        end=min(start+64,a.shape[0]);xx,yy=np.meshgrid(lon,lat[start:end]);band=a[start:end]
        # Core scope stays away from the regional coast-search boundaries.
        eligible=np.isin(band,[2,6,8,9])&(xx>=120)&(xx<=158)&(yy>=-10)&(yy<=30)
        rr,cc=np.where(eligible)
        if not len(rr):continue
        p=np.column_stack((xx[rr,cc],yy[rr,cc]));q=xyz(p[:,0],p[:,1])
        distance,index=tree.query(q,workers=4)
        nearest=shore_groups[index]
        near=distance<=2*np.sin(100/(2*6371.0088))
        shared=np.zeros(len(p),dtype=bool)
        for sea in seas:
            bounds=sea.get_extents()
            inside=(p[:,0]>=bounds.x0)&(p[:,0]<=bounds.x1)&(p[:,1]>=bounds.y0)&(p[:,1]<=bounds.y1)
            shared[inside]|=sea.contains_points(p[inside])
        use=near|shared;band[rr[use],cc[use]]=nearest[use]
        if start%640==0:print('Pacific rows',end,'/',len(a),flush=True)
    audit['water_changes']['asia_oceania']=int(np.count_nonzero((before<16)&(before!=a)))
    assert np.array_equal(before>=16,a>=16)
    patches.append((x0,y0,a));del before,edge,tree
    # Remove offshore African remnants east of Socotra, preserving near shore.
    x0,y0,a=region((43,5,64,23));before=a.copy();lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    rr,cc=np.where((a==17)&~binary_erosion(a==17));tree=cKDTree(xyz(lon[cc],lat[rr]))
    rr,cc=np.where((a==1)&(lon[None,:]>=54.5))
    d,_=tree.query(xyz(lon[cc],lat[rr]),workers=4);far=d>2*np.sin(100/(2*6371.0088));a[rr[far],cc[far]]=9
    audit['water_changes']['east_socotra']=int(np.count_nonzero(before!=a));patches.append((x0,y0,a))
    suez_patch,suez_audit=patch_suez(region,step)
    patches.append(suez_patch)
    audit['egypt_land_changes']=suez_audit['land_cells_changed']
    audit['water_changes']['gulf_suez']=suez_audit['water_cells_changed']
    audit['suez']=suez_audit
    # Stream the complete native grid, preserving all cells outside reviewed patches.
    offsets=[0];chunks=[];total=0;counts=np.zeros(11,dtype='int64');sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();atl=0
    longitude=-180+(np.arange(w)+.5)*step
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes());oldland=row>=16;lat=90-(y+.5)*step
        for px,py,patch in patches:
            if py<=y<py+len(patch):row[px:px+patch.shape[1]]=patch[y-py]
        if -60.01<lat<66.55 and np.any((row==8)&(longitude>-101)&(longitude<20)):
            wrong=(row==8)&ATLANTIC.contains_points(np.column_stack((longitude,np.full(w,lat))))
            atl+=int(wrong.sum());row[wrong]=7
        assert np.array_equal(oldland,row>=16)
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    audit['water_changes']['atlantic']=atl
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v9',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['regional_review_corrections']=audit
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.parent,a.source,a.output)

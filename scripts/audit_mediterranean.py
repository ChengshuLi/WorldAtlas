"""Recompute connected Mediterranean waters against native, padded coastline cells."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion,label
from scipy.spatial import cKDTree
from correct_suez import xyz

BASIN=(-6.5,30,37,46)
COAST=(-12,24,44,52)
SOURCE='https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/seaname/details/117'

def gates(lon,lat):
    """Close Gibraltar, Dardanelles and Suez entrances before connected-water fill."""
    # Trafalgar–Spartel: Mediterranean is east of this line.
    west=-5.923333+(-6.033333+5.923333)*(lat-35.793333)/(36.183333-35.793333)
    allowed=lon>=west
    # Cape Helles–Kum Kale: exclude northeast side in a window whose sides
    # terminate on land. Coordinates follow NOAA's Mediterranean definition.
    ax,ay=26.175,40.044444;bx,by=26.198611,40.009722
    cross=(bx-ax)*(lat-ay)-(by-ay)*(lon-ax)
    local=(lon>=26.08)&(lon<=26.30)&(lat>=39.94)&(lat<=40.12)
    allowed &= ~(local&(cross>0))
    # Keep the canal/lakes out of the sea audit, preserving their canal-side rule.
    allowed &= ~((lon>=32.25)&(lon<=32.45)&(lat<31.28)&(lat>31.1))
    return allowed

def build(parent,output):
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4')
    runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
    def decode(y,x0=0,x1=None):
        r=runs[rows[y]:rows[y+1]]
        if x1 is None:x1=w
        return r[np.searchsorted(r[:,0],np.arange(x0,x1),side='right'),1].astype('uint8')
    def extent(bounds):
        west,south,east,north=bounds
        return int((west+180)/step),int((90-north)/step),int((east+180)/step)+1,int((90-south)/step)+1
    cx0,cy0,cx1,cy1=extent(COAST);coords=[];groups=[]
    for y in range(cy0,cy1,256):
        ya=max(cy0,y-1);yb=min(cy1,y+257)
        a=np.array([decode(yy,cx0,cx1) for yy in range(ya,yb)])
        land=a>=16;edge=land&~binary_erosion(land);edge[[0,-1]]=False;edge[:,[0,-1]]=False
        rr,cc=np.where(edge&np.isin(a&15,[1,2,3]))
        coords.append(np.column_stack((-180+(cx0+cc+.5)*step,90-(ya+rr+.5)*step)));groups.append(a[rr,cc]&15)
    coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]))
    x0,y0,x1,y1=extent(BASIN)
    a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);old=a.copy()
    lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    water=a<16;allowed=gates(lon[None,:],lat[:,None]);components,_=label(water&allowed)
    seed=(int((90-35)/step)-y0,int((15+180)/step)-x0);basin=components==components[seed]
    assert components[seed]>0
    print(f'Mediterranean basin: {int(basin.sum())} water cells',flush=True)
    del components,allowed
    def inside(lo,la):return bool(basin[int((90-la)/step)-y0,int((lo+180)/step)-x0])
    for point in [(0,38),(6.05,38.74),(15,35),(17,42),(25,36),(34,34),(26.1,40.0)]:assert inside(*point),point
    for point in [(28,40.7),(32.35,31.2),(-6.3,36),(34,43)]:
        if BASIN[0]<point[0]<BASIN[2] and BASIN[1]<point[1]<BASIN[3]:assert not inside(*point),point
    max_km=0.;minimum_margin=1e9;audited=0;transitions=np.zeros((11,11),dtype='int64')
    for start in range(0,a.shape[0],64):
        end=min(start+64,a.shape[0]);rr,cc=np.where(basin[start:end]);rr+=start
        if not len(rr):continue
        d,i=tree.query(xyz(lon[cc],lat[rr]),workers=4);km=2*6371.0088*np.arcsin(np.minimum(d/2,1))
        # No omitted coast outside COAST can be closer: distance to every edge
        # of the padded search region exceeds the selected coast distance.
        angular=np.deg2rad(np.minimum(lon[cc]-COAST[0],COAST[2]-lon[cc]))
        side=np.arcsin(np.cos(np.deg2rad(lat[rr]))*np.sin(angular))*6371.0088
        vertical=np.minimum(lat[rr]-COAST[1],COAST[3]-lat[rr])*np.pi/180*6371.0088
        margin=np.minimum(side,vertical)-km;assert np.all(margin>0)
        new=groups[i];np.add.at(transitions,(a[rr,cc]&15,new),1);a[rr,cc]=new
        max_km=max(max_km,float(km.max()));minimum_margin=min(minimum_margin,float(margin.min()));audited+=len(rr)
    assert np.array_equal(a[~basin],old[~basin]);assert np.array_equal(a>=16,old>=16)
    audit={'water_cells_audited':audited,'water_cells_changed':int(np.count_nonzero(a!=old)),
      'land_cells_changed':0,'outside_basin_cells_changed':0,'coast_cells_searched':len(coords),
      'max_nearest_coast_km':max_km,'minimum_omitted_coast_distance_margin_km':minimum_margin,
      'transitions':{f'{i}->{j}':int(transitions[i,j]) for i,j in zip(*np.where(transitions))},
      'method':'All connected Mediterranean water cell centers use nearest native coastal land-cell center on a sphere, including islands; current land continent IDs retained. Padded coastline extent certified for every query. Entrances closed at Trafalgar–Spartel, Helles–Kum Kale and Suez.',
      'scope_source':SOURCE,'grid_width':w,'coast_bounds':COAST,'basin_bounds':BASIN}
    # Independent exhaustive verification uses separate continent trees, not the
    # combined tree used to assign cells, and compares distance to each group.
    trees={g:cKDTree(xyz(coords[groups==g,0],coords[groups==g,1])) for g in [1,2,3]}
    mismatches=0
    for start in range(0,a.shape[0],64):
        rr,cc=np.where(basin[start:start+64]);rr+=start
        if not len(rr):continue
        q=xyz(lon[cc],lat[rr]);ds=np.stack([trees[g].query(q,workers=4)[0] for g in [1,2,3]])
        assigned=ds[a[rr,cc]-1,np.arange(len(rr))];mismatches+=int(np.count_nonzero(assigned>ds.min(axis=0)+1e-12))
    audit['independent_nearest_coast_mismatches']=mismatches;assert mismatches==0
    print(f'Independent verification: {audited} cells, zero mismatches',flush=True)
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes())
        if y0<=y<y1:row[x0:x1]=a[y-y0]
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v11',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['mediterranean_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'mediterranean-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    np.savez_compressed(output/'mediterranean-preview.npz',old=old[::8,::8],new=a[::8,::8],basin=basin[::8,::8],bounds=[lon[0],lon[-1],lat[-1],lat[0]])
    print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)

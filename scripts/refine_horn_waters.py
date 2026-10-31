"""Refine Horn/Aden waters from native coast distances, preserving every land cell."""
import argparse,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from matplotlib.path import Path as PolygonPath
import shapefile

def xyz(lon,lat):
    lo=np.deg2rad(lon);la=np.deg2rad(lat)
    return np.column_stack((np.cos(la)*np.cos(lo),np.cos(la)*np.sin(lo),np.sin(la)))
def main(parent,source,output):
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((parent/'proposal.json').read_text());step=m['step'];width=m['width'];height=m['height']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),dtype='<u4')
    runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),dtype='<u4').reshape(-1,2)
    x0,x1=int((35+180)/step),int((80+180)/step)+1;y0,y1=int((90-30)/step),int((90+5)/step)+1
    xs=np.arange(x0,x1);patch=np.empty((y1-y0,x1-x0),dtype='uint8')
    for j,y in enumerate(range(y0,y1)):
        r=runs[rows[y]:rows[y+1]];patch[j]=r[np.searchsorted(r[:,0],xs,side='right'),1]
    original=patch.copy();land=patch>=16;edge=land & ~binary_erosion(land)
    trees={}
    for group in [1,2]:
        rr,cc=np.where(edge & ((patch&15)==group));trees[group]=cKDTree(xyz(-180+(x0+cc+.5)*step,90-(y0+rr+.5)*step))
    polygons={}
    for sr in shapefile.Reader(str(source/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():
        name=sr.record.as_dict()['name']
        if name in ['Gulf of Aden','Arabian Sea']:
            starts=list(sr.shape.parts)+[len(sr.shape.points)]
            polygons[name]=[PolygonPath(sr.shape.points[a:b]) for a,b in zip(starts,starts[1:])]
    longitude=-180+(xs+.5)*step
    for start in range(0,patch.shape[0],96):
        end=min(patch.shape[0],start+96);lat=90-(y0+np.arange(start,end)+.5)*step
        lon2,lat2=np.meshgrid(longitude,lat);points=np.column_stack((lon2.ravel(),lat2.ravel()))
        in_gulf=np.zeros(len(points),dtype=bool);in_arabian=in_gulf.copy()
        for p in polygons['Gulf of Aden']:in_gulf |= p.contains_points(points)
        for p in polygons['Arabian Sea']:in_arabian |= p.contains_points(points)
        in_gulf=in_gulf.reshape(lon2.shape);in_arabian=in_arabian.reshape(lon2.shape)
        coast_scope=(lon2>=40)&(lon2<=60)&(lat2>=7)&(lat2<=20)
        band=patch[start:end];eligible=(band<16)&np.isin(band,[1,2,9])&(in_gulf|in_arabian|coast_scope|((band==2)&(lon2>=50)&(lat2<=18)))
        rr,cc=np.where(eligible)
        if not len(rr):continue
        q=xyz(lon2[rr,cc],lat2[rr,cc]);d1,i1=trees[1].query(q,workers=4);d2,i2=trees[2].query(q,workers=4)
        nearest=np.where(d1<=d2,1,2).astype('uint8');distance=2*6371.0088*np.arcsin(np.minimum(np.minimum(d1,d2)/2,1))
        values=band[rr,cc].copy()
        # Remove the whole-sea Asia override on the Africa-facing offshore side.
        offshore=(in_arabian[rr,cc]|((lon2[rr,cc]>=50)&(lat2[rr,cc]<=18)&(values==2)))&(nearest==1)&(distance>100)
        values[offshore]=9
        near=coast_scope[rr,cc]&(distance<=100)
        values[near]=nearest[near]
        opposing=np.sum((trees[1].data[i1]-q)*(trees[2].data[i2]-q),axis=1)<=0
        shared=coast_scope[rr,cc]&opposing&(np.maximum(d1,d2)<=2*np.sin(450/(2*6371.0088)))
        values[shared]=nearest[shared]
        band[rr,cc]=values
        if start%480==0:print(f'Region rows {end}/{patch.shape[0]}',flush=True)
    assert np.array_equal(patch[land],original[land])
    changed=patch!=original
    transitions={f'{a}->{b}':int(np.count_nonzero(changed&(original==a)&(patch==b))) for a in [1,2,9] for b in [1,2,9] if a!=b}
    audit={'changed_water_cells':int(changed.sum()),'land_cells_changed':0,'transitions':transitions,'method':'Coastal proximity takes precedence within 100 km; Aden/Socotra waters between opposing shores within 450 km of each are shared by nearest coast; Africa-facing offshore Arabian Sea is Indian Ocean. Other regional groupings retained.'}
    # Re-encode the complete uniform grid without allocating a dense world bitmap.
    offsets=[0];chunks=[];count=0;sha=hashlib.sha256();display_sha=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(height):
        r=runs[rows[y]:rows[y+1]];row=np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
        if y0<=y<y1:row[x0:x1]=patch[y-y0]
        display_sha.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,width].astype('uint32');pairs=np.empty((len(ends),2),dtype='<u4');pairs[:,0]=ends;pairs[:,1]=row[ends-1]
        chunks.append(pairs.tobytes());count+=len(ends);offsets.append(count)
    rowbytes=np.array(offsets,dtype='<u4').tobytes();runbytes=b''.join(chunks)
    for name,raw in [('rows',rowbytes),('runs',runbytes)]: (output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v7',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display_sha.hexdigest())
    m['local_grid'].update(run_count=count,rows_sha256=hashlib.sha256(rowbytes).hexdigest(),runs_sha256=hashlib.sha256(runbytes).hexdigest(),decoded_bytes=len(rowbytes)+len(runbytes),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['horn_water_correction']=audit;m['caveats'][1]='Horn of Africa and Gulf of Aden waters use coast proximity; broader marine allocations elsewhere remain provisional.'
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'horn-audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();main(a.parent,a.source,a.output)

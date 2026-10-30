"""Repair explicit ocean-basin mismatches without changing land or island groups."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_fill_holes,distance_transform_edt

def repair(parent,output):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h=m['width'],m['height'];step=m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),dtype='<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),dtype='<u4').reshape(-1,2)
    def decode(y):
        r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
    x0,x1=int((45+180)/step),int((56+180)/step)+1;y0,y1=int((90-16)/step),int((90-9)/step)+1
    patch=np.array([decode(y)[x0:x1] for y in range(y0,y1)])
    continental=(patch&15)<=6;holes=binary_fill_holes(continental)&~continental
    if holes.any():
        _,indices=distance_transform_edt(~continental,return_indices=True);patch[holes]=patch[indices[0][holes],indices[1][holes]]&15
    counts=np.zeros(11,dtype='int64');sha=hashlib.sha256();display_sha=hashlib.sha256();base_sha=hashlib.sha256();offsets=[0];chunks=[];total=0
    longitude=-180+(np.arange(w)+.5)*step;atl_count=tas_count=0
    for y in range(h):
        row=decode(y);original=row.copy();base_sha.update((row&15).tobytes());lat=90-(y+.5)*step
        if y0<=y<y1:row[x0:x1]=patch[y-y0]
        if 24<=lat<66.55:
            wrong=(longitude>=-100)&(longitude<=20)&(row==8);atl_count+=int(wrong.sum());row[wrong]=7
        if lat<-(43+38/60):
            marine=(longitude>=100)&np.isin(row,[8,9]);desired=np.where(longitude<146+55/60,9,8).astype('uint8');tas_count+=int(np.count_nonzero(marine&(row!=desired)));row[marine]=desired[marine]
        assert np.array_equal(original[original>=16],row[original>=16]);assert np.array_equal(original>=16,row>=16)
        display_sha.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.empty((len(ends),2),dtype='<u4');pairs[:,0]=ends;pairs[:,1]=row[ends-1];chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base_sha.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v8',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display_sha.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for group in m['groups']:group['cells']=int(counts[group['id']])
    m['ocean_basin_repairs']={'north_atlantic_pacific_cells_corrected':atl_count,'south_tasmania_meridian_cells_corrected':tas_count,'horn_residual_ocean_hole_cells_closed':int(holes.sum()),'land_cells_changed':0,'tasmania_boundary_meridian_east':146+55/60,'source':'https://iho.int/uploads/user/pubs/standards/s-23/S-23_Ed3_1953_EN.pdf'}
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');print(json.dumps(m['ocean_basin_repairs']),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);a=p.parse_args();repair(a.parent,a.output)

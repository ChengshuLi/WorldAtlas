"""Correct Spain's African mainland possessions and adjacent coastal waters."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion
from scipy.spatial import cKDTree
from correct_suez import xyz

def build(parent,output):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),dtype='<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),dtype='<u4').reshape(-1,2)
    def decode(y):
        r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
    x0,x1=int(172/step),int(182/step)+1;y0,y1=int(52/step),int(57/step)+1
    a=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);old=a.copy()
    lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    xx,yy=np.meshgrid(lon,lat)
    # This scope includes Ceuta, Melilla, Perejil, Velez, Alhucemas and Chafarinas;
    # it stays south of the Iberian mainland and excludes Gibraltar.
    changed=(a==19)&(xx>=-6)&(xx<=-2)&(yy>=35)&(yy<=35.95);a[changed]=17
    land=a>=16;edge=land&~binary_erosion(land);rr,cc=np.where(edge&np.isin(a&15,[1,3]));groups=a[rr,cc]&15;tree=cKDTree(xyz(lon[cc],lat[rr]))
    rr,cc=np.where(np.isin(a,[1,3]));_,ii=tree.query(xyz(lon[cc],lat[rr]),workers=4);a[rr,cc]=groups[ii]
    assert np.array_equal(old>=16,a>=16)
    audit={'land_cells_changed':int(changed.sum()),'water_cells_changed':int(np.count_nonzero((old<16)&(a!=old))),
           'method':'Spanish possessions on the North African coast belong to Africa; nearby continental water follows the nearest corrected coast. Iberia and Gibraltar remain Europe.',
           'source':'https://www.spain.info/export/sites/segtur/.content/Folletos/folletos/spain-muslim-travellers-EN.pdf'}
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes())
        if y0<=y<y1:row[x0:x1]=a[y-y0]
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v10',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['north_africa_correction']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);a=p.parse_args();build(a.parent,a.output)

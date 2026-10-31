"""Replace Nordic Atlantic/Arctic patchwork with one cape-based divider."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from arctic_atlantic_boundary import ANCHORS,CURVE,arctic_side,SOURCES

def build(parent,output):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
    def decode(y):
        r=runs[rows[y]:rows[y+1]];return np.repeat(r[:,1],np.diff(np.r_[0,r[:,0]])).astype('uint8')
    x0,x1=int(135/step),int(230/step)+1;y0,y1=int(5/step),int(32/step)+1
    a=np.array([decode(y)[x0:x1] for y in range(y0,y1)]);old=a.copy();lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    basin=np.isin(a,[7,10]);boundary=np.interp(lon,CURVE[:,0],CURVE[:,1]);target=np.where(arctic_side(lon[None,:],lat[:,None]),10,7).astype('uint8');a[basin]=target[basin]
    assert np.array_equal(a[~basin],old[~basin])
    # Land and all continental coastal/bounded-sea cells are unchanged.
    assert np.array_equal(a[a>=16],old[old>=16])
    audit={'changed_ocean_cells':int(np.count_nonzero(a!=old)),'land_cells_changed':0,'continental_water_cells_changed':0,
      'atlantic_to_arctic':int(np.count_nonzero((old==7)&(a==10))),'arctic_to_atlantic':int(np.count_nonzero((old==10)&(a==7))),
      'convention':'Norwegian Sea remains Atlantic; Greenland and Barents seas Arctic. Cape Nansen–Straumnes; Gerpir–Jan Mayen–Sorkapp–Bear Island–North Cape. Great-circle sea segments; computational land links are invisible because land/coastal groups are preserved.',
      'anchors':ANCHORS,'sources':SOURCES,'scope':[-45,58,50,85]}
    (output/'arctic-atlantic-boundary.geojson').write_text(json.dumps({'type':'Feature','properties':{'sources':SOURCES,'convention':audit['convention']},'geometry':{'type':'LineString','coordinates':CURVE.tolist()}}))
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes())
        if y0<=y<y1:row[x0:x1]=a[y-y0]
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261031-v15',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['arctic_atlantic_boundary_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'arctic-atlantic-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    np.savez_compressed(output/'arctic-atlantic-preview.npz',old=old[::8,::8],new=a[::8,::8],basin=basin[::8,::8],bounds=[lon[0],lon[-1],lat[-1],lat[0]])
    print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)

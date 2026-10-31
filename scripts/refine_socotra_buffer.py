"""Bound shared Gulf of Aden waters; retain 100-km African island/coast buffers."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
from scipy.ndimage import binary_erosion,label
from scipy.spatial import cKDTree
from correct_suez import xyz

SOURCE='https://www.dco.uscg.mil/Portals/9/DCO/Documents/5p/CG-5PC/CG-CVC/Marpol/sdoc/MEPC%20117%2852%29.pdf'

def gulf_gates(lon,lat):
    # Geographic Cape Asir–Cape Fartak entrance, also used by IMO's Aden area.
    east=51+(16.9/60)+(52+13.8/60-(51+16.9/60))*(lat-(11+50/60))/((15+35/60)-(11+50/60))
    ax,ay=43+19.6/60,12+28.5/60;bx,by=43+30.2/60,12+40.4/60
    return (lon<=east)&((bx-ax)*(lat-ay)-(by-ay)*(lon-ax)<=0)

def build(parent,output):
    output.mkdir(parents=True,exist_ok=True)
    m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4')
    runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
    def decode(y,x0=0,x1=None):
        r=runs[rows[y]:rows[y+1]]
        if x1 is None:x1=w
        return r[np.searchsorted(r[:,0],np.arange(x0,x1),side='right'),1].astype('uint8')
    x0,x1=int(218/step),int(242/step)+1;y0,y1=int(64/step),int(87/step)+1
    a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);old=a.copy()
    lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    land=a>=16;edge=land&~binary_erosion(land);edge[[0,-1]]=False;edge[:,[0,-1]]=False
    components,_=label(land)
    mainland_ids=[]
    for lo,la in [(46,10),(48,17)]:mainland_ids.append(components[int((90-la)/step)-y0,int((lo+180)/step)-x0])
    assert all(i>0 for i in mainland_ids) and mainland_ids[0]!=mainland_ids[1]
    mainland=edge&np.isin(components,mainland_ids);del components
    rr,cc=np.where(mainland);main_groups=a[rr,cc]&15;main_tree=cKDTree(xyz(lon[cc],lat[rr]))
    rr,cc=np.where(edge&np.isin(a&15,[1,2]));coast_groups=a[rr,cc]&15;coast_tree=cKDTree(xyz(lon[cc],lat[rr]))
    components,_=label((~land)&gulf_gates(lon[None,:],lat[:,None]));seed=components[int(77/step)-y0,int(228/step)-x0];assert seed>0
    basin=components==seed;del components
    # Gulf mask must not leak into Red Sea, Socotra waters, or the open ocean.
    for lo,la in [(43,15),(54,14),(54.48,14.78),(52,8),(58,20)]:assert not basin[int((90-la)/step)-y0,int((lo+180)/step)-x0]
    assert basin[int(76/step)-y0,int(228/step)-x0]
    changes=np.zeros((11,11),dtype='int64');checked=0
    for start in range(0,a.shape[0],64):
        end=min(start+64,a.shape[0]);yy=lat[start:end,None];xx=lon[None,:];band=a[start:end];bg=basin[start:end]
        scope=(xx>=40)&(xx<=60)&(yy>=7)&(yy<=20)&(band<16)&np.isin(band,[1,2,9])
        # Outside the Gulf, revise the African extension east of the Horn only.
        eligible=scope&(bg|((xx>=50)&(band==1))|((xx>=50)&(xx<=56)&(yy>=10)&(yy<=15)))
        rr,cc=np.where(eligible)
        if not len(rr):continue
        q=xyz(lon[cc],lat[start+rr]);d,idx=coast_tree.query(q,workers=4);km=2*6371.0088*np.arcsin(np.minimum(d/2,1));nearest=coast_groups[idx]
        new=band[rr,cc].copy();in_gulf=bg[rr,cc]
        if in_gulf.any():
            _,idx=main_tree.query(q[in_gulf],workers=4);new[in_gulf]=main_groups[idx]
        # African waters outside the bounded Gulf have a 100-km coast limit.
        new[(~in_gulf)&(new==1)&(km>100)]=9
        # Native islands and coasts retain their local buffer; closer Asian shore wins.
        close=km<=100;new[close]=nearest[close]
        np.add.at(changes,(band[rr,cc],new),1);band[rr,cc]=new;checked+=len(rr)
        assert not np.any((~in_gulf)&(new==1)&(km>100))
        assert np.all(new[close]==nearest[close])
    assert np.array_equal(a[land],old[land]);assert np.array_equal(a>=16,old>=16)
    for x,y,expected in [(42593,13816,9),(42685,13692,9),(42953,13885,9),(43243,13816,9)]:assert a[y-y0,x-x0]==expected
    audit={'water_cells_checked':checked,'shared_gulf_cells':int(basin.sum()),'changed_water_cells':int(np.count_nonzero(a!=old)),
      'land_cells_changed':0,'transitions':{f'{i}->{j}':int(changes[i,j]) for i,j in zip(*np.where(changes)) if i!=j},
      'method':'Bounded Gulf of Aden split by nearest mainland coast. Local coast/island buffers use nearest shoreline within 100 km. Outside the Gulf, African-water extensions east of the Horn beyond 100 km become Indian Ocean. Distant Asian Arabian Sea grouping retained pending review.',
      'gulf_entrance_source':SOURCE,'buffer_km':100,'grid_width':w}
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes())
        if y0<=y<y1:row[x0:x1]=a[y-y0]
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v12',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['socotra_buffer_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'socotra-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    np.savez_compressed(output/'socotra-preview.npz',old=old[::8,::8],new=a[::8,::8],basin=basin[::8,::8],bounds=[lon[0],lon[-1],lat[-1],lat[0]])
    print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)

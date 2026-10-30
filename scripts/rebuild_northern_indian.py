"""Unified native coastal-water rule for Arabian Sea and Bay of Bengal."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
import shapefile
from scipy.ndimage import binary_erosion,label
from scipy.spatial import cKDTree
from matplotlib.path import Path as PolygonPath
from correct_suez import xyz
from refine_socotra_buffer import gulf_gates

SOURCE=Path(__file__).resolve().parents[2]/'worldatlas-continent-review/sources'

def oman_side(lon,lat):
    ax,ay=59+47/60,22+32/60;bx,by=61+44/60+15/3600,25+1/60+10/3600
    return (bx-ax)*(lat-ay)-(by-ay)*(lon-ax)>=0

def malacca_side(lon,lat):
    ax,ay=95+26/60,5+39/60+20/3600;bx,by=98+18/60+30/3600,7+45/60+30/3600
    return (bx-ax)*(lat-ay)-(by-ay)*(lon-ax)>=0

def build(parent,output):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
    def decode(y,x0=0,x1=None):
        r=runs[rows[y]:rows[y+1]]
        if x1 is None:x1=w
        return r[np.searchsorted(r[:,0],np.arange(x0,x1),side='right'),1].astype('uint8')
    # Coast search padding exceeds 100 km everywhere; no local target rectangle
    # truncates candidate shores. Inland lakes are excluded by connected sea mask.
    cx0,cx1=int(212/step),int(290/step)+1;cy0,cy1=int(52/step),int(106/step)+1
    coords=[];groups=[]
    for y in range(cy0,cy1,256):
        ya=max(cy0,y-1);yb=min(cy1,y+257);a=np.array([decode(yy,cx0,cx1) for yy in range(ya,yb)])
        land=a>=16;edge=land&~binary_erosion(land);edge[[0,-1]]=False;edge[:,[0,-1]]=False
        rr,cc=np.where(edge&np.isin(a&15,[1,2]));coords.append(np.column_stack((-180+(cx0+cc+.5)*step,90-(ya+rr+.5)*step)));groups.append(a[rr,cc]&15)
    coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));limit=2*np.sin(100/(2*6371.0088))
    x0,x1=int(222/step),int(280/step)+1;y0,y1=int(58/step),int(100/step)+1
    a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);old=a.copy();lon=-180+(x0+np.arange(a.shape[1])+.5)*step;lat=90-(y0+np.arange(a.shape[0])+.5)*step
    water=a<16
    allowed=np.ones(a.shape,dtype=bool)
    for start in range(0,a.shape[0],128):
        yy=lat[start:start+128,None];xx=lon[None,:]
        # Across Bab el Mandeb, retain only its Aden side.
        ax,ay=43+19.6/60,12+28.5/60;bx,by=43+30.2/60,12+40.4/60
        allowed[start:start+128] &= ~((xx<44)&((bx-ax)*(yy-ay)-(by-ay)*(xx-ax)>0))
        # Southern scope excludes the unrelated East African/Mozambique coast.
        allowed[start:start+128] &= ~((xx<47)&(yy<10))
        # Do not enter Malacca Strait; this gate ends on its mainland shores.
        allowed[start:start+128] &= ~((xx>=95.4333)&(yy>=5.6555)&~malacca_side(xx,yy))
    components,_=label(water&allowed);seed=components[int(75/step)-y0,int(245/step)-x0];assert seed>0;basin=components==seed;del components,allowed
    # South of the equator include only the Maldives/Chagos corridor; unrelated
    # Seychelles and southern Indonesian coasts are outside this review.
    basin &= (lat[:,None]>=0)|((lon[None,:]>=65)&(lon[None,:]<=80))
    def atmask(mask,lo,la):return bool(mask[int((90-la)/step)-y0,int((lo+180)/step)-x0])
    for point in [(65,15),(88,14),(58,24.5),(51,27),(48,13),(96,11),(81,5),(73,-5)]:assert atmask(basin,*point),point
    assert not atmask(basin,43,15)
    protected=np.zeros(a.shape,dtype='uint8')
    # Persian Gulf and Gulf of Oman are one connected Asian-water area.
    components,_=label(water&oman_side(lon[None,:],lat[:,None]));seed=components[int(65/step)-y0,int(238/step)-x0];assert seed>0
    protected[basin&(components==seed)]=2;del components
    # Gulf of Aden uses the same explicit entrance and mainland split as v12.
    components,_=label(water&gulf_gates(lon[None,:],lat[:,None]));seed=components[int(77/step)-y0,int(228/step)-x0];assert seed>0
    aden=basin&(components==seed);del components
    # Mainland coast candidates for Aden exclude Socotra and smaller islands.
    # Within this southern crop Africa and Arabia are disconnected by the sea.
    ry0,ry1=int(64/step),int(87/step)+1;rx0,rx1=int(218/step),int(242/step)+1
    reg=np.array([decode(y,rx0,rx1) for y in range(ry0,ry1)]);land=reg>=16;components,_=label(land);ids=[components[int((90-la)/step)-ry0,int((lo+180)/step)-rx0] for lo,la in [(46,10),(48,17)]]
    edge=land&~binary_erosion(land);rr,cc=np.where(edge&np.isin(components,ids));main_groups=reg[rr,cc]&15;main_tree=cKDTree(xyz(-180+(rx0+cc+.5)*step,90-(ry0+rr+.5)*step));del reg,land,components
    for start in range(0,a.shape[0],128):
        rr,cc=np.where(aden[start:start+128]);rr+=start
        if len(rr):
            _,i=main_tree.query(xyz(lon[cc],lat[rr]),workers=4);protected[rr,cc]=main_groups[i]
    # Andaman's western limit follows its island-arc source outline. Its southern
    # entrance is clipped to the explicit Cape Phra Chao–Pedropunt line.
    parts=[]
    for sr in shapefile.Reader(str(SOURCE/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():
        if sr.record.as_dict()['name']=='Andaman Sea':
            starts=list(sr.shape.parts)+[len(sr.shape.points)];parts += [PolygonPath(sr.shape.points[i:j]) for i,j in zip(starts,starts[1:])]
    for start in range(0,a.shape[0],128):
        end=min(start+128,a.shape[0]);rr,cc=np.where(basin[start:end]&(lon[None,:]>=91)&(lon[None,:]<=100)&(lat[start:end,None]>=5)&(lat[start:end,None]<=17));rr+=start
        if not len(rr):continue
        pts=np.column_stack((lon[cc],lat[rr]));inside=np.zeros(len(rr),dtype=bool)
        for path in parts:inside |= path.contains_points(pts)
        inside &= malacca_side(lon[cc],lat[rr]);protected[rr[inside],cc[inside]]=2
    assert atmask(protected,96,11);assert atmask(protected,58,24.5)
    assert not atmask(protected,65,15);assert not atmask(protected,88,14)
    transitions=np.zeros((11,11),dtype='int64');checked=0;near_count=0
    for start in range(0,a.shape[0],64):
        rr,cc=np.where(basin[start:start+64]);rr+=start
        if not len(rr):continue
        q=xyz(lon[cc],lat[rr]);d,i=tree.query(q,distance_upper_bound=limit,workers=4);near=np.isfinite(d)
        new=np.full(len(rr),9,dtype='uint8');fixed=protected[rr,cc]>0;new[fixed]=protected[rr[fixed],cc[fixed]]
        # In Aden, nearby island coasts retain the approved local priority.
        use_near=near&(~fixed|aden[rr,cc]);new[use_near]=groups[i[use_near]]
        np.add.at(transitions,(a[rr,cc]&15,new),1);a[rr,cc]=new;checked+=len(rr);near_count+=int(near.sum())
        assert np.all(new[~fixed&~near]==9)
        assert np.all(new[~fixed&near]==groups[i[~fixed&near]])
    assert np.array_equal(a[~basin],old[~basin]);assert np.array_equal(a>=16,old>=16)
    # Independent full-cell verification, querying per-continent trees within100km.
    trees={g:cKDTree(xyz(coords[groups==g,0],coords[groups==g,1])) for g in [1,2]};mismatches=0
    for start in range(0,a.shape[0],64):
        rr,cc=np.where(basin[start:start+64]);rr+=start
        if not len(rr):continue
        q=xyz(lon[cc],lat[rr]);ds=np.stack([trees[g].query(q,distance_upper_bound=limit,workers=4)[0] for g in [1,2]])
        near=np.isfinite(ds.min(axis=0));expected=np.full(len(rr),9,dtype='uint8');fixed=protected[rr,cc]>0;expected[fixed]=protected[rr[fixed],cc[fixed]];use=near&(~fixed|aden[rr,cc]);expected[use]=ds[:,use].argmin(axis=0)+1
        mismatches+=int(np.count_nonzero(a[rr,cc]!=expected))
    assert mismatches==0
    audit={'water_cells_audited':checked,'water_cells_changed':int(np.count_nonzero(a!=old)),'coastal_water_cells':near_count,
      'land_cells_changed':0,'outside_scope_cells_changed':0,'independent_rule_mismatches':mismatches,
      'transitions':{f'{i}->{j}':int(transitions[i,j]) for i,j in zip(*np.where(transitions)) if i!=j},
      'method':'Single native rule: protected Gulf of Aden (shared mainland coasts), Persian/Gulf of Oman and Andaman waters; otherwise nearest coastal continent within 100 km, Indian Ocean beyond. Includes islands and mainland. Replaces previous whole Arabian Sea/Bay of Bengal overrides and local offshore exceptions.',
      'buffer_km':100,'coast_search_bounds':[32,-16,110,38],'scope_bounds':[42,-10,100,32],
      'sources':['https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/seaname/details/35','https://iho.int/uploads/user/pubs/standards/s-23/S-23_Ed3_1953_EN.pdf'],
      'remaining_source_limit':'Andaman western island-arc boundary uses generalized Natural Earth marine outline; native coast buffers cover the islands.'}
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        row=decode(y);base.update((row&15).tobytes())
        if y0<=y<y1:row[x0:x1]=a[y-y0]
        display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
        ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v13',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['northern_indian_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'northern-indian-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    np.savez_compressed(output/'northern-indian-preview.npz',old=old[::8,::8],new=a[::8,::8],basin=basin[::8,::8],bounds=[lon[0],lon[-1],lat[-1],lat[0]])
    print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);v=p.parse_args();build(v.parent,v.output)

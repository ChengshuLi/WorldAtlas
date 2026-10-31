"""Uniform 12-nautical-mile native coastal buffers, retaining bounded seas."""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
import shapefile
from scipy.ndimage import binary_erosion,label
from scipy.spatial import cKDTree
from rasterio.features import rasterize
from rasterio.transform import from_origin
from matplotlib.path import Path as PolygonPath
from correct_suez import xyz
from audit_mediterranean import gates as med_gates
from refine_socotra_buffer import gulf_gates
from rebuild_northern_indian import oman_side,malacca_side
from refine_review_regions import ATLANTIC
from north_sea_limits import NORTH_SEA

BUFFER_KM=22.224
SOURCE=Path(__file__).resolve().parents[2]/'worldatlas-continent-review/sources'

def build(parent,output,open_runs_path):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,step=m['width'],m['height'],m['step']
    rows=np.frombuffer(gzip.decompress((parent/m['local_grid']['rows']).read_bytes()),'<u4');runs=np.frombuffer(gzip.decompress((parent/m['local_grid']['runs']).read_bytes()),'<u4').reshape(-1,2)
    opened=np.load(open_runs_path);assert len(opened)==len(runs)
    def decode(y,x0=0,x1=None,opening=False):
        rr=runs[rows[y]:rows[y+1]]
        if x1 is None:x1=w
        ix=np.searchsorted(rr[:,0],np.arange(x0,x1),side='right')
        return opened[rows[y]+ix] if opening else rr[ix,1].astype('uint8')
    # Build shoreline from represented land only. Longitude wraps at the dateline.
    coords=[];groups=[]
    for y in range(0,h,128):
        ya=max(0,y-1);yb=min(h,y+129);a=np.array([decode(yy) for yy in range(ya,yb)])
        land=a>=16;pad=np.pad(land,((0,0),(1,1)),mode='wrap');edge=land&~binary_erosion(pad)[:,1:-1];edge[[0,-1]]=False
        rr,cc=np.where(edge);coords.append(np.column_stack((-180+(cc+.5)*step,90-(rr+ya+.5)*step)));groups.append(a[rr,cc]&15)
    coords=np.concatenate(coords);groups=np.concatenate(groups);tree=cKDTree(xyz(coords[:,0],coords[:,1]));limit=2*np.sin(BUFFER_KM/(2*6371.0088));outer=2*np.sin((BUFFER_KM+4)/(2*6371.0088))
    print('Represented coast cells',len(coords),flush=True)
    # Explicit complete bounded-water masks for areas already audited at native resolution.
    specials=[]
    def connected(bounds,seed,gate):
        west,south,east,north=bounds;x0,x1=int((west+180)/step),int((east+180)/step)+1;y0,y1=int((90-north)/step),int((90-south)/step)+1
        a=np.array([decode(y,x0,x1) for y in range(y0,y1)]);lo=-180+(np.arange(x0,x1)+.5)*step;la=90-(np.arange(y0,y1)+.5)*step
        mask=a<16
        if gate is not None:mask &= gate(lo[None,:],la[:,None])
        comp,_=label(mask);root=comp[int((90-seed[1])/step)-y0,int((seed[0]+180)/step)-x0];assert root>0
        specials.append((x0,y0,comp==root))
    connected((-6.5,30,37,46),(15,35),med_gates)
    connected((26,40.4,42,47.6),(34,43),None)
    connected((40,9,54,18),(48,13),gulf_gates)
    connected((46,20,63,32),(58,25),oman_side)
    # Baltic and its enclosed arms are bounded to the west through Danish land.
    # Source polygons below also cover the straits and named adjacent gulfs.
    protected_names=set(m.get('shared_seas',[]))
    fixed={}
    for code,names in m.get('continent_seas',{}).items():
        for name in names:protected_names.add(name);fixed[name]=int(code)
    protected_names -= {'Arabian Sea','Bay of Bengal','Bay of Biscay','Mediterranean Sea','Gulf of Aden','Gulf of Oman','Persian Gulf','North Sea'}
    protected_names |= {'Sea of Marmara','Bosporus','Dardanelles','Gulf of Bothnia','Gulf of Finland','Gulf of Riga','Skagerrak','Kattegat','Øresund','Bristol Channel','Inner Seas','Waddenzee','Stettiner Haff','Mecklenburger Bucht'}
    for name in ['Gulf of Bothnia','Gulf of Finland','Gulf of Riga','Skagerrak','Kattegat','Øresund','Bristol Channel','Inner Seas','Waddenzee','Stettiner Haff','Mecklenburger Bucht']:fixed[name]=3
    oceans={'Arctic Ocean':10,'North Atlantic Ocean':7,'South Atlantic Ocean':7,'North Pacific Ocean':8,'South Pacific Ocean':8,'INDIAN OCEAN':9}
    arctic={'Chukchi Sea','Beaufort Sea','East Siberian Sea','Laptev Sea','Kara Sea','Barents Sea','Greenland Sea','Lincoln Sea'}
    marine=[]
    for sr in shapefile.Reader(str(SOURCE/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords():
        name=sr.record.as_dict()['name'];geom=sr.shape.__geo_interface__;bbox=sr.shape.bbox
        marine.append((name,geom,bbox))
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();base=hashlib.sha256();counts=np.zeros(11,dtype='int64');transitions=np.zeros((11,11),dtype='int64');changed=land_changes=coastal_cells=0;examined=0
    longitudes=-180+(np.arange(w)+.5)*step
    for y in range(0,h,64):
        end=min(y+64,h);a=np.array([decode(yy) for yy in range(y,end)]);old=a.copy();water=a<16;openwater=np.array([decode(yy,opening=True) for yy in range(y,end)]);lat=90-(np.arange(y,end)+.5)*step
        transform=from_origin(-180,90-y*step,step,step)
        shapes=[(geom,fixed.get(name,99)) for name,geom,b in marine if name in protected_names and b[3]>=lat[-1]-step and b[1]<=lat[0]+step]
        protected=rasterize(shapes,out_shape=a.shape,transform=transform,fill=0,dtype='uint8') if shapes else np.zeros_like(a)
        if lat[-1]<=61 and lat[0]>=50:
            rr,cc=np.where((lat[:,None]>=50)&(lat[:,None]<=61)&(longitudes[None,:]>=-4)&(longitudes[None,:]<=12))
            inside=NORTH_SEA.contains_points(np.column_stack((longitudes[cc],lat[rr])))
            protected[rr[inside],cc[inside]]=3
        # The Andaman/Malacca entrance uses its actual named cape line.
        if lat[-1]<8 and lat[0]>5:
            xx=longitudes[None,:];yy=lat[:,None];bad=(xx>=95.4333)&(xx<=100)&(yy>=5.6555)&(yy<=8)&~malacca_side(xx,yy);protected[bad]=0
        for sx,sy,mask in specials:
            ay=max(y,sy);by=min(end,sy+mask.shape[0])
            if ay<by:
                v=protected[ay-y:by-y,sx:sx+mask.shape[1]];v[mask[ay-sy:by-sy]]=99
        keep=water&((protected>0)|~openwater)
        # Every ordinary open-water cell has an ocean baseline before shore buffering.
        ordinary=water&~keep
        rr,cc=np.where(ordinary&(a<=6))
        if len(rr):
            lon=longitudes[cc];la=lat[rr];fallback=np.where((lon>=20)&(lon<147),9,8).astype('uint8');fallback[ATLANTIC.contains_points(np.column_stack((lon,la)))]=7;fallback[la>=66.55]=10
            # Authoritative source ocean/parent-sea extents override longitude fallback.
            ocean_shapes=[(geom,oceans.get(name,10 if name in arctic else 7)) for name,geom,b in marine if (name in oceans or name in arctic or name in {'Norwegian Sea','Bay of Biscay'}) and b[3]>=lat[-1]-step and b[1]<=lat[0]+step]
            basin_codes=rasterize(ocean_shapes,out_shape=a.shape,transform=transform,fill=0,dtype='uint8') if ocean_shapes else np.zeros_like(a)
            labels=basin_codes[rr,cc];fallback[labels>0]=labels[labels>0]
            # Preserve reviewed Atlantic-side basin separator and southern Tasmania meridian.
            atl=ATLANTIC.contains_points(np.column_stack((lon,la)));fallback[(fallback==8)&atl]=7
            south=(la<-(43+38/60))&(lon>=100)&(lon<=180);fallback[south]=np.where(lon[south]<146+55/60,9,8)
            a[rr,cc]=fallback
        # Fill source-bounded sea slivers only where parent map was ocean-coded.
        rr,cc=np.where(keep&(a>=7)&(a<16)&(protected>0))
        if len(rr):
            codes=protected[rr,cc];shared=codes==99
            if shared.any():_,ii=tree.query(xyz(longitudes[cc[shared]],lat[rr[shared]]),workers=4);codes[shared]=groups[ii]
            a[rr,cc]=codes
        # Conservative 8x8 screen: no point in a block is farther than4km from
        # its query point. Therefore no <=22.224km native candidate is discarded.
        cy=np.arange(y,end,8);cx=np.arange(0,w,8);lo,la=np.meshgrid(-180+(cx+4.5)*step,90-(np.minimum(cy+4,h-1)+.5)*step)
        d,_=tree.query(xyz(lo.ravel(),la.ravel()),distance_upper_bound=outer,workers=4)
        candidate=np.repeat(np.repeat(np.isfinite(d).reshape(len(cy),len(cx)),8,axis=0),8,axis=1)[:end-y,:w]&ordinary
        rr,cc=np.where(candidate)
        if len(rr):
            q=xyz(longitudes[cc],lat[rr]);d,ii=tree.query(q,distance_upper_bound=limit,workers=4);hit=np.isfinite(d);a[rr[hit],cc[hit]]=groups[ii[hit]];coastal_cells+=int(hit.sum())
            # The KD query certifies all candidates outside the radius are ocean.
            assert np.all(a[rr[~hit],cc[~hit]]>=7)
        assert np.array_equal(a[~water],old[~water]);assert np.array_equal(a>=16,old>=16)
        changed+=int(np.count_nonzero(a!=old));examined+=int(ordinary.sum());np.add.at(transitions,((old[water]&15),(a[water]&15)),1)
        for j in range(end-y):
            row=a[j];base.update((old[j]&15).tobytes());display.update(row.tobytes());ids=row&15;sha.update(ids.tobytes());counts+=np.bincount(ids,minlength=11)
            ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
        if y%1024==0:print('rows',end,'changed',changed,flush=True)
    assert base.hexdigest()==m['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,raw in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(proposal_id='continent-20261030-v14',sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{x}.u32.gz').stat().st_size for x in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    audit={'buffer_km':BUFFER_KM,'ordinary_water_cells_audited':examined,'coastal_water_cells':coastal_cells,'changed_water_cells':changed,'land_cells_changed':0,'represented_coast_cells':len(coords),'protected_sea_names':sorted(protected_names),'transitions':{f'{i}->{j}':int(transitions[i,j]) for i,j in zip(*np.where(transitions)) if i!=j},'method':'12 nautical miles from represented native coastal land cells on a sphere, with no source-only island buffers. Named bounded/shared seas and inland waters retained. Open Biscay/Atlantic approaches follow ordinary buffer; Arctic coasts use the same distance. This borrows a distance, not legal maritime boundaries.'}
    m['global_coastal_buffer_audit']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'coastal-buffer-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('open_runs',type=Path);args=p.parse_args();build(args.parent,args.output,args.open_runs)

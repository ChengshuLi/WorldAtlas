"""Apply the agreed ordinary coastal rule to open Tasman/Bight waters."""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np,shapefile
from scipy.spatial import cKDTree
from shapely.geometry import shape,mapping,box
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz
from sea_families import child_rules,OPEN_WATERS

OPENED={'Tasman Sea':8,'Great Australian Bight':9}

def parent_ocean(name,lon,lat):
    result=np.full(np.broadcast(lon,lat).shape,OPENED[name],dtype='uint8')
    if name=='Tasman Sea':result[(lat<-(43+38/60))&(lon<146+55/60)]=9
    return result

def build(parent,output,source,coasts):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,s=m['width'],m['height'],m['step']
    R=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');V=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
    def row(y):
        z=V[R[y]:R[y+1]];return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
    c=np.load(coasts);tree=cKDTree(xyz(*c['coordinates'].T));limit=2*np.sin(22.224/(2*6371.0088))
    marine={f.record.as_dict()['name']:shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(source/'ne_10m_geography_marine_polys/ne_10m_geography_marine_polys.shp')).iterShapeRecords()}
    lakes=[shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(source/'ne_10m_lakes/ne_10m_lakes.shp')).iterShapeRecords()]
    active=(set(m['shared_seas'])|{n for a in m['continent_seas'].values() for n in a}|set(child_rules()))-OPEN_WATERS
    patches=[];audit=[]
    for name in OPENED:
        g=marine[name];we,so,ea,no=g.bounds;x0=max(0,int((we+180)/s)-1);x1=min(w,int((ea+180)/s)+2);y0=max(0,int((90-no)/s)-1);y1=min(h,int((90-so)/s)+2);xs=np.arange(x0,x1);lon=-180+(xs+.5)*s
        a=np.array([row(y)[xs] for y in range(y0,y1)]);before=a.copy();protected=[z for n,z in marine.items() if n in active and z.intersects(box(we,so,ea,no))]+[z for z in lakes if z.intersects(box(we,so,ea,no))]
        examined=0
        for start in range(0,len(a),64):
            end=min(len(a),start+64);y=y0+start;band=a[start:end];tf=from_origin(-180+x0*s,90-y*s,s,s)
            target=rasterize([(mapping(g),1)],out_shape=band.shape,transform=tf,dtype='uint8')>0
            selected=[(mapping(z),1) for z in protected if z.bounds[3]>=90-(y0+end)*s and z.bounds[1]<=90-y*s]
            keep=rasterize(selected,out_shape=band.shape,transform=tf,dtype='uint8')>0 if selected else np.zeros_like(target)
            rr,cc=np.where(target&~keep&(band<16));la=90-(y+rr+.5)*s
            if not len(rr):continue
            d,ix=tree.query(xyz(lon[cc],la),distance_upper_bound=limit,workers=4);near=np.isfinite(d);values=parent_ocean(name,lon[cc],la);values[near]=c['groups'][ix[near]];band[rr,cc]=values;examined+=len(rr)
        assert np.array_equal(a>=16,before>=16);assert np.array_equal(a[before>=16],before[before>=16]);record={'name':name,'water_cells_audited':examined,'changed_water_cells':int(np.count_nonzero(a!=before)),'buffer_km':22.224,'bounded_neighbors_and_inland_lakes_preserved':True};audit.append(record);patches.append((x0,y0,a));print(json.dumps(record),flush=True)
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        old=row(y);a=old.copy()
        for x0,y0,patch in patches:
            if y0<=y<y0+len(patch):a[x0:x0+patch.shape[1]]=patch[y-y0]
        assert np.array_equal(a>=16,old>=16);assert np.array_equal(a[old>=16],old[old>=16]);sha.update((a&15).tobytes());display.update(a.tobytes());counts+=np.bincount(a&15,minlength=11)
        ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for n,raw in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    for group,names in m['continent_seas'].items():m['continent_seas'][group]=[n for n in names if n not in OPENED]
    m['australasian_open_water_refinement']={'decision':'User approved normal22.224km coastal treatment for Tasman Sea and Great Australian Bight on2026-10-31. This is atlas grouping, not legal maritime ownership.','bodies':audit,'land_changes':0,'tasmania_ocean_meridian':146+55/60}
    (output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'australasian-open-water-audit.json').write_text(json.dumps(m['australasian_open_water_refinement'],indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','source','coasts']:p.add_argument(n,type=Path)
    a=p.parse_args();build(a.parent,a.output,a.source,a.coasts)

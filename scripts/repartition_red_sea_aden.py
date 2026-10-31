"""Recompute native shared-water dividers under the existing Red Sea/Aden rules."""
import argparse,gzip,json,hashlib
from pathlib import Path
import numpy as np,shapefile
from scipy.ndimage import label
from scipy.spatial import cKDTree
from shapely.geometry import shape,mapping
from rasterio.features import rasterize
from rasterio.transform import from_origin
from correct_suez import xyz
from refine_socotra_buffer import gulf_gates

def aden_groups(near,coastal,mainland):
    return np.where(near,coastal,mainland)

def build(parent,output,source,coasts):
    output.mkdir(parents=True,exist_ok=True);m=json.loads((parent/'proposal.json').read_text());w,h,s=m['width'],m['height'],m['step']
    R=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4');V=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
    def row(y):
        z=V[R[y]:R[y+1]];return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
    c=np.load(coasts);tree=cKDTree(xyz(*c['coordinates'].T));limit=2*np.sin(22.224/(2*6371.0088));patches=[];audits=[]
    marine={f.record.as_dict()['name']:shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(source)).iterShapeRecords()}
    for name,bounds in [('Red Sea',(32,12,44,30.6)),('Gulf of Aden',(38,3,62,26))]:
        we,so,ea,no=bounds;x0,x1=int((we+180)/s),int((ea+180)/s)+1;y0,y1=int((90-no)/s),int((90-so)/s)+1;xs=np.arange(x0,x1);lon=-180+(xs+.5)*s;lat=90-(np.arange(y0,y1)+.5)*s;a=np.array([row(y)[xs] for y in range(y0,y1)]);before=a.copy()
        if name=='Red Sea':
            shapes=[(mapping(marine[n]),1) for n in ['Red Sea','Gulf of Suez','Gulf of Aqaba','Bab el Mandeb'] if n in marine]
            mask=(rasterize(shapes,out_shape=a.shape,transform=from_origin(-180+x0*s,90-y0*s,s,s),dtype='uint8')>0)&np.isin(a,[1,2])
            rr,cc=np.where(mask);_,ix=tree.query(xyz(lon[cc],lat[rr]),workers=4);expected=c['groups'][ix];assert np.isin(expected,[1,2]).all()
        else:
            components,_=label(a>=16);main_ids=[components[int((90-la)/s)-y0,int((lo+180)/s)-x0] for lo,la in [(46,10),(48,17)]];assert all(main_ids)
            cells=c['cells'];inside=(cells[:,0]>=x0)&(cells[:,0]<x1)&(cells[:,1]>=y0)&(cells[:,1]<y1);ix=np.flatnonzero(inside);cx,cy=cells[ix].T;ix=ix[np.isin(components[cy-y0,cx-x0],main_ids)];main_tree=cKDTree(xyz(*c['coordinates'][ix].T));main_groups=c['groups'][ix];del components
            components,_=label((a<16)&gulf_gates(lon[None,:],lat[:,None]));seed=components[int((90-13)/s)-y0,int((48+180)/s)-x0];assert seed;rr,cc=np.where(components==seed);del components
            q=xyz(lon[cc],lat[rr]);distance,gi=tree.query(q,workers=4);_,mi=main_tree.query(q,workers=4);expected=aden_groups(distance<=limit,c['groups'][gi],main_groups[mi]);assert np.isin(a[rr,cc],[1,2]).all()
        a[rr,cc]=expected;assert np.array_equal(a>=16,before>=16);assert np.array_equal(a[before>=16],before[before>=16]);audits.append({'name':name,'water_cells_examined':len(rr),'changed_water_cells':int(np.count_nonzero(a!=before)),'coast_scope':'all represented native coasts' if name=='Red Sea' else 'bordering African/Arabian mainland, with native22.224km coast/island priority'});patches.append((x0,y0,a));print(json.dumps(audits[-1]),flush=True)
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        old=row(y);a=old.copy()
        for x0,y0,patch in patches:
            if y0<=y<y0+len(patch):
                # Regions overlap near Bab el Mandeb; apply only cells actually changed.
                patch_row=patch[y-y0];base=old[x0:x0+len(patch_row)];changed=patch_row!=base;view=a[x0:x0+len(patch_row)];view[changed]=patch_row[changed]
        assert np.array_equal(a>=16,old>=16);assert np.array_equal(a[old>=16],old[old>=16]);sha.update((a&15).tobytes());display.update(a.tobytes());counts+=np.bincount(a&15,minlength=11)
        ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for n,raw in [('rows',rb),('runs',vb)]:(output/f'{n}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    m.update(sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest());m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    m['red_sea_aden_partition_audit']={'bodies':audits,'land_changes':0,'method':'Full native spherical nearest-coast recomputation under the existing shared-sea rules. No new sea extent or mainland/island convention.'};(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'red-sea-aden-partition-audit.json').write_text(json.dumps(m['red_sea_aden_partition_audit'],indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','source','coasts']:p.add_argument(n,type=Path)
    a=p.parse_args();build(a.parent,a.output,a.source,a.coasts)

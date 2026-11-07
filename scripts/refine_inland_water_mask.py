"""Classify represented lake interiors as water without changing continent IDs.

Lake polygon holes preserve islands. Sampling remains at native cell centers.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import numpy as np
import shapefile
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import shape,mapping

def apply_lake_mask(cells,lakes):
    result=cells.copy()
    result[(lakes>0)&(cells>=16)] &= 15
    return result

def build(parent,output,source):
    output.mkdir(parents=True,exist_ok=True)
    meta=json.loads((parent/'proposal.json').read_text());w,h,s=meta['width'],meta['height'],meta['step']
    r=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4')
    v=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
    lakes=[shape(f.shape.__geo_interface__) for f in shapefile.Reader(str(source)).iterShapeRecords()]
    offsets=[0];chunks=[];total=changed=0;display=hashlib.sha256();continent=hashlib.sha256()
    for y in range(0,h,64):
        end=min(y+64,h);rows=[]
        for yy in range(y,end):
            z=v[r[yy]:r[yy+1]];rows.append(np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])))
        old=np.array(rows,dtype='uint8')
        selected=[(mapping(g),1) for g in lakes if g.bounds[3]>=90-end*s and g.bounds[1]<=90-y*s]
        mask=rasterize(selected,out_shape=old.shape,transform=from_origin(-180,90-y*s,s,s),dtype='uint8') if selected else np.zeros_like(old)
        a=apply_lake_mask(old,mask);changed+=int(np.count_nonzero(a!=old))
        assert np.array_equal(a&15,old&15)
        display.update(a.tobytes());continent.update((a&15).tobytes())
        for row in a:
            ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32')
            pairs=np.column_stack((ends,row[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    assert continent.hexdigest()==meta['sha256_uncompressed']
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,data in [('rows',rb),('runs',vb)]:
        (output/f'{name}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
    meta['display_sha256_uncompressed']=display.hexdigest()
    meta['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    audit={'land_to_inland_water_cells':changed,'continent_affiliation_changes':0,'sampling':'native cell centers; polygon holes preserve islands','source':'Natural Earth 1:10m lakes','source_shp_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'coast_cache_must_be_regenerated':True}
    meta['inland_water_mask_refinement']=audit
    (output/'proposal.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
    (output/'inland-water-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('source',type=Path);args=p.parse_args();build(args.parent,args.output,args.source)

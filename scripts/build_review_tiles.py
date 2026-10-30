"""Refine a continent draft with native center-sampled land and bounded-size assets.

Marine group boundaries are inherited from the explicitly named prior draft.
No continent approval is implied. This does not upsample its land mask.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import STRtree
from shapely.geometry import box
from build_continent_proposal import land_records, parts

W, H, TILE = 65536, 27307, 512
STEP = 360 / W

def build(source, parent, output):
    output.mkdir(parents=True, exist_ok=True)
    meta = json.loads((parent / 'proposal.json').read_text())
    prior = np.frombuffer(gzip.decompress((parent / 'continent-cells.u8.gz').read_bytes()), dtype='uint8').reshape(meta['height'],meta['width'])
    assert W == meta['width']*4
    records, _, _ = land_records(source)
    records = [(p, code) for geom, code in records for p in parts(geom)]
    geometries = [p for p, _ in records]
    tree = STRtree(geometries)
    entries = {}; counts = np.zeros(11,dtype='int64'); sha=hashlib.sha256(); display_sha=hashlib.sha256()
    overview = np.zeros((math.ceil(H/32),W//32),dtype='uint8')
    with (output/'display-tiles.pack').open('wb') as packed:
        for y0 in range(0,H,TILE):
            height=min(TILE,H-y0)
            # Existing marine group footprints retain their exact prior boundaries.
            row_indices=np.arange(y0,y0+height)//4
            band=np.repeat(prior[row_indices,:],4,axis=1).copy()
            for x0 in range(0,W,TILE):
                width=min(TILE,W-x0)
                window=box(-180+x0*STEP,90-(y0+height)*STEP,-180+(x0+width)*STEP,90-y0*STEP)
                candidates=tree.query(window,predicate='intersects')
                # Lower stable group ID wins overlapping source centers.
                selected=sorted((records[i] for i in candidates),key=lambda v:v[1],reverse=True)
                land=rasterize(selected,out_shape=(height,width),transform=from_origin(-180+x0*STEP,90-y0*STEP,STEP,STEP),dtype='uint8',all_touched=False) if selected else np.zeros((height,width),dtype='uint8')
                tile=band[:,x0:x0+width]
                tile[land>0]=land[land>0]
                tile[land>0]+=16
                raw=tile.tobytes();entry={'width':width,'height':height}
                if tile.min()==tile.max():entry['value']=int(tile[0,0])
                else:
                    encoded=gzip.compress(raw,compresslevel=6,mtime=0)
                    entry.update(offset=packed.tell(),length=len(encoded),sha256=hashlib.sha256(raw).hexdigest())
                    packed.write(encoded)
                entries[f'{x0//TILE},{y0//TILE}']=entry
            display_sha.update(band.tobytes())
            ids=band & 15
            assert ids.min()>=1 and ids.max()<=10
            counts+=np.bincount(ids.ravel(),minlength=11)
            sha.update(ids.tobytes())
            # Native center samples for a lightweight visual overview, never picking.
            for r in range(16,height,32):
                overview[(y0+r)//32,:]=band[r,16::32]
            print(f'Rows {y0+height}/{H}',flush=True)
    assert counts.sum()==W*H
    palette=np.array(meta['palette'],dtype='uint8').ravel().tolist()
    img=Image.fromarray(overview,'P');img.putpalette(palette);img.save(output/'overview.png')
    meta.update(proposal_id='continent-20261030-v3',width=W,height=H,step=STEP,southern_edge=90-H*STEP,
        sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display_sha.hexdigest(),
        sampling='cell_center',display_encoding='packed-gzip-tiles-u8',tile_size=TILE,tiles=entries,
        tile_pack='display-tiles.pack',marine_base_proposal=meta['proposal_id'],
        boundary_audit={'method':'native-resolution cell-center rasterization; lower group ID wins overlap'},
        caveats=[
          'Europe–Asia and Suez seams remain approximate and require lower-level compatibility checks.',
          'Marine group boundaries retain the previous draft footprints; this revision refines land sampling, not the sea-allocation research.',
          'Nearby-water groupings are editorial proposals, not sovereignty claims.',
          'Natural Earth coastline detail is incomplete; important inhabited-island representation still requires source and cell review.',
        ])
    for g in meta['groups']:g['cells']=int(counts[g['id']])
    meta['tile_pack_sha256']=hashlib.sha256((output/'display-tiles.pack').read_bytes()).hexdigest()
    (output/'proposal.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
    print(json.dumps({'grid_sha256':sha.hexdigest(),'cells':int(counts.sum()),'tiles':len(entries),'pack_bytes':(output/'display-tiles.pack').stat().st_size}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('parent',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();build(a.source,a.parent,a.output)

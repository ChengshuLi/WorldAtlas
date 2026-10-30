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
from shapely.affinity import scale as scale_geometry
from shapely.ops import unary_union
from build_continent_proposal import land_records, parts
from clean_ocean_pockets import clean_ocean_pockets

W, H, TILE = 65536, 27307, 512
STEP = 360 / W

def build(source, parent, output, proposal_id="continent-20261030-v6", maldives=None):
    output.mkdir(parents=True, exist_ok=True)
    meta = json.loads((parent / 'proposal.json').read_text())
    prior = np.frombuffer(gzip.decompress((parent / 'continent-cells.u8.gz').read_bytes()), dtype='uint8').reshape(meta['height'],meta['width']).copy()
    assert W == meta['width']*4
    pocket_audit = clean_ocean_pockets(prior)
    (output/"pocket-audit.json").write_text(json.dumps(pocket_audit,indent=2))
    records, _, _ = land_records(source, maldives)
    records = [(p, code) for geom, code in records for p in parts(geom)]
    geometries = [p for p, _ in records]
    tree = STRtree(geometries)
    socotra = unary_union([g for g, code in records if code == 1 and 51 < g.representative_point().x < 55 and 11 < g.representative_point().y < 13.5])
    # Local equirectangular distance approximation for this small, low-latitude envelope.
    factor = math.cos(math.radians(12.5))
    socotra_water = scale_geometry(scale_geometry(socotra, xfact=factor, yfact=1, origin=(0,0)).buffer(100/111.195), xfact=1/factor, yfact=1, origin=(0,0))
    entries = {}; counts = np.zeros(11,dtype='int64'); sha=hashlib.sha256(); display_sha=hashlib.sha256()
    overview = np.zeros((math.ceil(H/32),W//32),dtype='uint8')
    with (output/'display-tiles.pack').open('wb') as packed:
        for y0 in range(0,H,TILE):
            height=min(TILE,H-y0)
            # Existing marine group footprints retain their exact prior boundaries.
            row_indices=np.arange(y0,y0+height)//4
            band=np.repeat(prior[row_indices,:],4,axis=1).copy()
            # User-reviewed grouping: Heard–McDonald belongs with Kerguelen in Africa.
            # The box only selects the isolated existing Oceania footprint; it does
            # not turn intervening ocean into continental waters.
            r0=max(0, math.floor((90+50)/STEP)-y0)
            r1=min(height, math.ceil((90+56)/STEP)-y0)
            if r1>r0:
                region=band[r0:r1,math.floor((69+180)/STEP):math.ceil((77+180)/STEP)]
                region[region==6]=1
            if 90-y0*STEP >= socotra_water.bounds[1] and 90-(y0+height)*STEP <= socotra_water.bounds[3]:
                socotra_mask = rasterize([(socotra_water, 1)], out_shape=band.shape, transform=from_origin(-180,90-y0*STEP,STEP,STEP), dtype='uint8')
                band[(socotra_mask>0)&(band==2)] = 1
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
    meta.update(proposal_id=proposal_id,width=W,height=H,step=STEP,southern_edge=90-H*STEP,
        sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display_sha.hexdigest(),
        sampling='cell_center',display_encoding='packed-gzip-tiles-u8',tile_size=TILE,tiles=entries,
        tile_pack='display-tiles.pack',marine_base_proposal=meta['proposal_id'],
        boundary_audit={'method':'native-resolution cell-center rasterization; lower group ID wins overlap'},
        caveats=[
          'Europe–Asia and Suez seams remain approximate and require lower-level compatibility checks.',
          'Outer marine grouping boundaries retain prior draft footprints; enclosed ocean-code artifacts were removed and Heard–McDonald and Socotra were regrouped with Africa.',
          'Nearby-water groupings are editorial proposals, not sovereignty claims.',
          'Natural Earth coastline detail is incomplete; important inhabited-island representation still requires source and cell review.',
        ])
    meta['island_groups']['Heard Island and McDonald Islands']=1
    meta['reviewed_grouping_decisions']=[{'subject':'Kerguelen and Heard–McDonald','group':'Africa','basis':'User requested grouping together on 2026-10-30; shared Kerguelen Plateau, not political ownership','scope':'Heard–McDonald land and its existing associated nearby-water footprint'}, {'subject':'Socotra Archipelago','group':'Africa','basis':'User approved geographic grouping with the Horn of Africa on 2026-10-30','scope':'Archipelago and approximately 100 km surrounding waters, using a local distance approximation'}]
    meta['pocket_cleanup']={'components':len(pocket_audit),'parent_cells':sum(a['parent_cells'] for a in pocket_audit),'unresolved':sum(a['method']=='unresolved_review_required' for a in pocket_audit),'audit':'pocket-audit.json'}
    if maldives is not None:
        meta['maldives_source']={'publisher':'Geomatics Department, Ministry of Infrastructure, Housing and Urban Development, Maldives','url':'https://geomatics.gov.mv/nationalmapping.php','license':'https://readme.onemap.mv/pdf/Data%20Usage%20License.pdf','sha256':hashlib.sha256(maldives.read_bytes()).hexdigest(),'feature_count':len(json.loads(maldives.read_text())['features'])}
        source_audit=maldives.with_name('island-center-audit.json')
        if source_audit.exists():
            residential=[f for f in json.loads(source_audit.read_text()) if f['category']=='Residential Island']
            missing=sum(f['land_cells']==0 for f in residential)
            meta['maldives_source'].update(residential_features_without_cell_center=missing,residential_features_total=len(residential))
            meta['caveats'].append(f'Maldives source improved with official OneMap island polygons; {missing} of its {len(residential)} Residential Island features still contain no native cell center. No artificial enlargement has been applied.')
    for g in meta['groups']:g['cells']=int(counts[g['id']])
    meta['tile_pack_sha256']=hashlib.sha256((output/'display-tiles.pack').read_bytes()).hexdigest()
    (output/'proposal.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
    print(json.dumps({'grid_sha256':sha.hexdigest(),'cells':int(counts.sum()),'tiles':len(entries),'pack_bytes':(output/'display-tiles.pack').stat().st_size}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('parent',type=Path);p.add_argument('output',type=Path);p.add_argument('--proposal-id',default='continent-20261030-v6')
    p.add_argument('--maldives',type=Path)
    a=p.parse_args();build(a.source,a.parent,a.output,a.proposal_id,a.maldives)

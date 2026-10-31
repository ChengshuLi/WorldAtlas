"""Native center-sampled physical land at a finer grid, retaining reviewed group scope.

This stage is not publishable until its new coast/buffer and connectivity audits
finish. Reviewed continent-group footprints are retained as old cell-edge polygons;
physical land and lakes are independently rasterized, never enlarged old pixels.
"""
import argparse, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely import STRtree, make_valid, contains_xy
from shapely.geometry import shape, box
from build_continent_proposal import land_records, parts, features


def build(parent, sources, maldives, additions, exceptions, out, width, exclusions=None):
    out.mkdir(parents=True, exist_ok=False)
    m=json.loads((parent/'proposal.json').read_text())
    assert width==2*m['width'] and m['sampling']=='cell_center'
    w=width; h=2*m['height']; s=360/w
    rb=gzip.decompress((parent/'rows.u32.gz').read_bytes())
    vb=gzip.decompress((parent/'runs.u32.gz').read_bytes())
    assert hashlib.sha256(rb).hexdigest()==m['local_grid']['rows_sha256']
    assert hashlib.sha256(vb).hexdigest()==m['local_grid']['runs_sha256']
    R=np.frombuffer(rb,'<u4');V=np.frombuffer(vb,'<u4').reshape(-1,2)
    # Original source extraction supplies only physical polygons here. Existing
    # reviewed continental groups override its obsolete provisional seam labels.
    rec,_,_=land_records(sources,maldives)
    rec=[(p,c) for g,c in rec for p in parts(g)]
    # The independently rejected NE Aves component is geographically misplaced.
    # Replace only this exact component with verified actual Aves geometry below.
    ghost_box=box(-63.643626,15.694037,-63.633941,15.702949)
    removed=[];kept=[]
    for p,c in rec:
        if c==5 and ghost_box.covers(p):removed.append(p.bounds)
        else:kept.append((p,c))
    assert len(removed)==1,removed
    rec=kept
    replaced=[]
    if exclusions:
        replace_geoms=[shape(f['geometry']) for f in json.loads(exclusions.read_text())['features']]
        kept=[]; matches=[0]*len(replace_geoms)
        for p,c in rec:
            matched=[i for i,g in enumerate(replace_geoms) if p.bounds==g.bounds and p.equals(g)]
            if matched:
                assert len(matched)==1
                matches[matched[0]]+=1;replaced.append(p.bounds)
            else:kept.append((p,c))
        assert matches==[1]*len(replace_geoms),matches
        rec=kept
    geoms=[g for g,_ in rec];tree=STRtree(geoms)
    lakes=[g for _,g in features(sources,'ne_10m_lakes')];lt=STRtree(lakes)
    extras=[]; source_files=[]
    for fpath in (additions,exceptions):
        data=fpath.read_bytes();source_files.append({'path':str(fpath),'sha256':hashlib.sha256(data).hexdigest()})
        for f in json.loads(data)['features']:
            p=f['properties'];c=p.get('atlas_group',p.get('continent'))
            if c is None:c=p.get('continent_id',p.get('continent_group_id'))
            assert isinstance(c,int) and 1<=c<=6,(p,c)
            g=shape(f['geometry']);assert g.is_valid
            if 'expected_centers_131072' in p:
                assert w==131072
                we,so,ea,no=g.bounds
                xx,yy=np.meshgrid(np.arange(int((we+180)/s),int((ea+180)/s)+1),np.arange(int((90-no)/s),int((90-so)/s)+1))
                hits=int(contains_xy(g,-180+(xx+.5)*s,90-(yy+.5)*s).sum())
                assert hits==p['expected_centers_131072'],(p['name'],hits,p['expected_centers_131072'])
            extras.append((g,c,p['name']))
    et=STRtree([g for g,_,_ in extras])
    # Explicit current source groups apply only within their exact dry-land outlines.
    counts=np.zeros(11,dtype='int64'); land_count=water_to_land=land_to_water=0
    offsets=[0];nr=0;continent_hash=hashlib.sha256();display_hash=hashlib.sha256()
    run_hash=hashlib.sha256();raw_run_bytes=0
    candidate_foreign=0
    with (out/'runs.u32.gz').open('wb') as raw:
      with gzip.GzipFile(fileobj=raw,mode='wb',compresslevel=6,mtime=0) as packed:
        for y in range(0,h,64):
            end=min(y+64,h);bheight=end-y
            old=[]
            for oy in range(y//2,(end+1)//2):
                z=V[R[oy]:R[oy+1]]
                old.append(np.repeat(z[:,1].astype('uint8'),np.diff(np.r_[0,z[:,0]])))
            prior=np.repeat(np.repeat(np.array(old,dtype='uint8'),2,axis=0),2,axis=1)[:bheight]
            band=prior&15
            window=box(-180,90-end*s,180,90-y*s)
            ix=tree.query(window,predicate='intersects')
            selected=[rec[int(i)] for i in ix]
            tr=from_origin(-180,90-y*s,s,s)
            land=rasterize(selected,out_shape=band.shape,transform=tr,fill=0,dtype='uint8',all_touched=False) if selected else np.zeros_like(band)
            # Lakes retain continent labels; their holes preserve physical islands.
            li=lt.query(window,predicate='intersects')
            lake=rasterize([(lakes[int(i)],1) for i in li],out_shape=band.shape,transform=tr,fill=0,dtype='uint8',all_touched=False) if len(li) else None
            if lake is not None:land[lake>0]=0
            dry=land>0
            fallback=dry&(band>=7)
            candidate_foreign+=int(fallback.sum())
            band[fallback]=land[fallback]
            band[dry]+=16
            ei=et.query(window,predicate='intersects')
            if len(ei):
                ex=rasterize([(extras[int(i)][0],16+extras[int(i)][1]) for i in ei],out_shape=band.shape,transform=tr,fill=0,dtype='uint8',all_touched=False)
                band[ex>0]=ex[ex>0]
            assert np.isin(band,[1,2,3,4,5,6,7,8,9,10,17,18,19,20,21,22]).all()
            water_to_land+=int(((prior<16)&(band>=16)).sum())
            land_to_water+=int(((prior>=16)&(band<16)).sum());land_count+=int((band>=16).sum())
            display_hash.update(band.tobytes());ids=band&15;continent_hash.update(ids.tobytes())
            counts+=np.bincount(ids.ravel(),minlength=11)
            for row in band:
                ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,w].astype('uint32')
                pairs=np.column_stack((ends,row[ends-1])).astype('<u4').tobytes()
                packed.write(pairs);run_hash.update(pairs);raw_run_bytes+=len(pairs)
                nr+=len(ends);offsets.append(nr)
            print(f'Native rows {end}/{h}; source land cells {land_count}',flush=True)
    assert nr<2**32 and counts.sum()==w*h
    rows=np.array(offsets,dtype='<u4').tobytes()
    (out/'rows.u32.gz').write_bytes(gzip.compress(rows,compresslevel=6,mtime=0))
    audit={'stage':'native_land_candidate_requires_water_refresh','base_proposal':m['proposal_id'],
      'width':w,'height':h,'step':s,'center_sampling':True,'majority_rule':False,
      'reviewed_group_scope':'v32 cell-edge polygons retained; boundary precision unchanged',
      'source_land_recomputed':True,'land_cells':land_count,'new_land_vs_parent_footprint':water_to_land,
      'new_water_vs_parent_footprint':land_to_water,'source_group_fallback_cells':candidate_foreign,
      'removed_misplaced_NE_Aves_component':removed,'replaced_NE_component_bounds':replaced,'extra_source_files':source_files,
      'maldives_sha256':hashlib.sha256(maldives.read_bytes()).hexdigest()}
    m.update(proposal_id='continent-20261031-v33-native-candidate',width=w,height=h,step=s,
      southern_edge=90-h*s,status='draft',sampling='cell_center',
      sha256_uncompressed=continent_hash.hexdigest(),display_sha256_uncompressed=display_hash.hexdigest(),
      resolution_refinement=audit)
    m.setdefault('current_rules',{})['world_columns']=w
    m['local_grid'].update(run_count=nr,rows_sha256=hashlib.sha256(rows).hexdigest(),runs_sha256=run_hash.hexdigest(),decoded_bytes=len(rows)+raw_run_bytes,compressed_bytes=sum((out/f'{a}.u32.gz').stat().st_size for a in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    (out/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n')
    (out/'resolution-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','sources','maldives','additions','exceptions','output']:p.add_argument(n,type=Path)
    p.add_argument('--width',type=int,default=131072)
    p.add_argument('--exclusions',type=Path)
    a=p.parse_args();build(a.parent,a.sources,a.maldives,a.additions,a.exceptions,a.output,a.width,a.exclusions)

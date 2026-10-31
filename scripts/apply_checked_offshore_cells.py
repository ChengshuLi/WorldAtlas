"""Remove rule-checked offshore remnants, with independent native validation."""
import argparse,csv,gzip,hashlib,json,gc
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
import shapefile
from scipy.spatial import cKDTree
from shapely import contains_xy
from shapely.geometry import shape
from correct_suez import xyz
from sea_families import child_rules,OPEN_WATERS

def build(parent,output,candidates,coasts,marine_source,references):
    output.mkdir(parents=True,exist_ok=False)
    m=json.loads((parent/'proposal.json').read_text());w,h,s=m['width'],m['height'],m['step']
    R=np.frombuffer(gzip.decompress((parent/'rows.u32.gz').read_bytes()),'<u4')
    V=np.frombuffer(gzip.decompress((parent/'runs.u32.gz').read_bytes()),'<u4').reshape(-1,2)
    @lru_cache(maxsize=16)
    def row(y):
        z=V[R[y]:R[y+1]];return np.repeat(z[:,1],np.diff(np.r_[0,z[:,0]])).astype('uint8')
    raw=candidates.read_bytes();records=list(csv.DictReader(raw.decode().splitlines()))
    changes={};clusters=defaultdict(set)
    for r in records:
        x,y=int(r['cell_x']),int(r['cell_y']);old=int(r['current_raw']);new=int(r['expected_ocean_raw'])
        assert 1<=old<=6 and new in (7,8,9,10) and int(row(y)[x])==old
        assert abs(float(r['lon'])-(-180+(x+.5)*s))<1e-8 and abs(float(r['lat'])-(90-(y+.5)*s))<1e-8
        key=y*w+x;assert key not in changes;changes[key]=new
        clusters[(r['component'],r['candidate_cluster_id'],new)].add(key)
    keys=np.array(list(changes),dtype='int64');yy,xx=np.divmod(keys,w);lo=-180+(xx+.5)*s;la=90-(yy+.5)*s
    c=np.load(coasts);tree=cKDTree(xyz(*c['coordinates'].T));d,_=tree.query(xyz(lo,la),workers=2)
    assert np.all(2*np.arcsin(d/2)*6371.0088>22.224),'Would alter ordinary coastal band'
    del tree,c;gc.collect()
    protected=set(m['shared_seas'])|{n for names in m['continent_seas'].values() for n in names}|set(child_rules())
    protected|={'Bristol Channel','Inner Seas','Sea of Marmara','Bosporus','Dardanelles','Gulf of Bothnia','Gulf of Finland','Gulf of Riga','Skagerrak','Kattegat','Øresund','Waddenzee','Stettiner Haff','Mecklenburger Bucht'}
    protected-=OPEN_WATERS
    for f in shapefile.Reader(str(marine_source)).iterShapeRecords():
        name=f.record.as_dict()['name']
        if name in protected:assert not contains_xy(shape(f.shape.__geo_interface__),lo,la).any(),('Protected sea',name)
    source_files=set()
    for file in references.glob('*.json'):
        data=json.loads(file.read_text())
        if not isinstance(data,dict):continue
        for r in data.get('rules',[]):
            for name in r.get('files',[r.get('file')]):
                if name and (references/name).exists():source_files.add(references/name)
    hashes={}
    for file in sorted(source_files):
        raw_ref=file.read_bytes();data=json.loads(raw_ref)
        if data.get('type')!='Feature' or not data.get('geometry'):continue
        g=shape(data['geometry'])
        assert not contains_xy(g,lo,la).any(),('Published protected reference',file.name)
        hashes[file.name]=hashlib.sha256(raw_ref).hexdigest()
        del g,data,raw_ref;gc.collect()
    for (region,cluster,expected),points in clusters.items():
        oceans=set()
        for key in points:
            y,x=divmod(key,w)
            for ny,nx in [(y,(x-1)%w),(y,(x+1)%w),(max(0,y-1),x),(min(h-1,y+1),x)]:
                if ny*w+nx in points:continue
                value=int(row(ny)[nx])
                if 7<=value<=10:oceans.add(value)
        assert oceans=={expected},(region,cluster,oceans,expected)
    byrow=defaultdict(list)
    for key,value in changes.items():y,x=divmod(key,w);byrow[y].append((x,value))
    offsets=[0];chunks=[];total=0;sha=hashlib.sha256();display=hashlib.sha256();counts=np.zeros(11,dtype='int64')
    for y in range(h):
        old=row(y);a=old.copy()
        for x,value in byrow[y]:a[x]=value
        assert np.array_equal(a[old>=16],old[old>=16]) and np.array_equal(a>=16,old>=16)
        sha.update((a&15).tobytes());display.update(a.tobytes());counts+=np.bincount(a&15,minlength=11)
        ends=np.r_[np.flatnonzero(a[:-1]!=a[1:])+1,w].astype('uint32');pairs=np.column_stack((ends,a[ends-1])).astype('<u4');chunks.append(pairs.tobytes());total+=len(ends);offsets.append(total)
    rb=np.array(offsets,dtype='<u4').tobytes();vb=b''.join(chunks)
    for name,data in [('rows',rb),('runs',vb)]:(output/f'{name}.u32.gz').write_bytes(gzip.compress(data,compresslevel=6,mtime=0))
    m.update(sha256_uncompressed=sha.hexdigest(),display_sha256_uncompressed=display.hexdigest())
    m['local_grid'].update(run_count=total,rows_sha256=hashlib.sha256(rb).hexdigest(),runs_sha256=hashlib.sha256(vb).hexdigest(),decoded_bytes=len(rb)+len(vb),compressed_bytes=sum((output/f'{n}.u32.gz').stat().st_size for n in ['rows','runs']))
    for g in m['groups']:g['cells']=int(counts[g['id']])
    audit={'candidate_sha256':hashlib.sha256(raw).hexdigest(),'changed_water_cells':len(changes),'land_changes':0,'checked_reference_hashes':hashes,'method':'Outside every active/published bounded-sea mask and native22.224km coastal band; each connected proposed cluster touches only its assigned existing ocean.'}
    m['checked_offshore_cleanup']=audit;(output/'proposal.json').write_text(json.dumps(m,separators=(',',':'))+'\n');(output/'checked-offshore-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['parent','output','candidates','coasts','marine_source','references']:p.add_argument(n,type=Path)
    a=p.parse_args();build(a.parent,a.output,a.candidates,a.coasts,a.marine_source,a.references)

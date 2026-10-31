"""Encode all native cells as lossless row runs for up-front local rendering."""
import gzip, hashlib, json
from pathlib import Path
import numpy as np
import sys

def build(folder):
    meta=json.loads((folder/'proposal.json').read_text())
    packed=(folder/meta['tile_pack']).read_bytes()
    offsets=[0]; run_chunks=[]; count=0; sha=hashlib.sha256(); display_sha=hashlib.sha256()
    for ty in range((meta['height']+511)//512):
        band=np.empty((min(512,meta['height']-ty*512),meta['width']),dtype='uint8')
        for tx in range((meta['width']+511)//512):
            entry=meta['tiles'][f'{tx},{ty}']
            if 'value' in entry: tile=np.full((entry['height'],entry['width']),entry['value'],dtype='uint8')
            else:
                raw=gzip.decompress(packed[entry['offset']:entry['offset']+entry['length']]);assert hashlib.sha256(raw).hexdigest()==entry['sha256']
                tile=np.frombuffer(raw,dtype='uint8').reshape(entry['height'],entry['width'])
            band[:,tx*512:tx*512+entry['width']]=tile
        display_sha.update(band.tobytes());sha.update((band&15).tobytes())
        for row in band:
            ends=np.r_[np.flatnonzero(row[:-1]!=row[1:])+1,meta['width']].astype('uint32')
            pairs=np.empty((len(ends),2),dtype='<u4');pairs[:,0]=ends;pairs[:,1]=row[ends-1]
            run_chunks.append(pairs.tobytes());count+=len(ends);offsets.append(count)
    assert sha.hexdigest()==meta['sha256_uncompressed']
    assert display_sha.hexdigest()==meta['display_sha256_uncompressed']
    rows=np.array(offsets,dtype='<u4').tobytes();runs=b''.join(run_chunks)
    for name,raw in [('rows',rows),('runs',runs)]:
        (folder/f'{name}.u32.gz').write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    meta['local_grid']={'encoding':'row-runs-u32-pairs-v1','rows':'rows.u32.gz','runs':'runs.u32.gz','run_count':count,'rows_sha256':hashlib.sha256(rows).hexdigest(),'runs_sha256':hashlib.sha256(runs).hexdigest(),'decoded_bytes':len(rows)+len(runs),'compressed_bytes':sum((folder/f'{s}.u32.gz').stat().st_size for s in ['rows','runs'])}
    meta['display_encoding']='row-runs-u32-pairs-v1'
    for key in ['tile_pack','tile_pack_sha256','tile_size']:meta.pop(key,None)
    (folder/'proposal-full.json').write_text(json.dumps({k:v for k,v in meta.items() if k!='tiles'},separators=(',',':'))+'\n')
    print(json.dumps(meta['local_grid'],indent=2))
if __name__=='__main__':build(Path(sys.argv[1]))

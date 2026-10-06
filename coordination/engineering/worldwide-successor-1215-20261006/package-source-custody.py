"""Lossless transport of complete unchanged source blobs; no numerical regeneration."""
import argparse, gzip, hashlib, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence.immutable import deterministic_gzip
from physical_gap_successor import verify_decoded_relation
ORIGINAL = '548c5f89f00271050823076a84695bb41e1b8454'
SELECTED = '79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
PATHS = ['data/geography/part-30.json', 'data/geography/part-32.json']
def descriptor(path, raw):
    return {'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'hash_kind': 'file-bytes'}
def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    out = pathlib.Path(parser.parse_args().output)
    if out.exists(): raise ValueError('Refusing overwrite of a custody vintage')
    out.mkdir(parents=True)
    relations = []
    for path in PATHS:
        bodies = [subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT) for commit in [ORIGINAL, SELECTED]]
        if bodies[0] != bodies[1]: raise ValueError('Shared source bytes differ')
        raw = bodies[0]; packed = deterministic_gzip(raw)
        if gzip.decompress(packed) != raw: raise ValueError('Lossless transformation failed')
        name = path.replace('/', '_') + '.gz'; (out / name).write_bytes(packed)
        encoded = descriptor(name, packed); encoded.update(uncompressed_bytes=len(raw), uncompressed_sha256=hashlib.sha256(raw).hexdigest())
        source = descriptor(path, raw)
        relation = verify_decoded_relation(encoded, packed, source, raw, 1)
        relations.append({'source_commits': [ORIGINAL, SELECTED], 'source': source, 'encoded': encoded, 'decoded_relation': relation})
    receipt = {'version': 'whole-source-lossless-transport-v1', 'executed_packaging_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'scientific_producer_commit': 'd31c320fd3a71002a5c47cd72a20052e95c381a1', 'relations': relations, 'limits': 'Transport only: actual numerical source reads are recorded by the separately committed worldwide producer.'}
    (out / 'receipt.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'raw_bytes': sum(x['source']['bytes'] for x in relations), 'encoded_bytes': sum(x['encoded']['bytes'] for x in relations)}))
if __name__ == '__main__': main()

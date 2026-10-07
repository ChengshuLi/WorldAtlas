"""Directed actual reader and compact tuple/interval controls; no GIS run."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile

HERE = Path(__file__).resolve().parent

def module(name, p):
    spec = importlib.util.spec_from_file_location(name, p)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def run():
    reader = module('reference_native_reader_controls', HERE/'reader.py')
    products = module('reference_native_products_controls', HERE/'products.py')
    passed = []
    def rejects(label, fn):
        try: fn()
        except (ValueError, OSError): passed.append(label)
        else: raise AssertionError('Intended negative did not reject: '+label)
    rejects('Git option rejected before subprocess',lambda:reader.Inputs('--output=bad'))
    rejects('abbreviated commit rejected before subprocess',lambda:reader.Inputs('abcd1234'))
    with tempfile.TemporaryDirectory(prefix='reference-native-controls-',dir=HERE.parents[2]/'.cache') as td:
        root=Path(td); p=root/'body'; p.write_bytes(b'whole')
        assert reader.bounded(p,5)==b'whole'; passed.append('opened ordinary positive')
        rejects('declared overbound rejects before read',lambda:reader.bounded(p,reader.CAP+1))
        rejects('opened size differs declared',lambda:reader.bounded(p,4))
        rejects('relative traversal',lambda:reader.safe(root,'../body'))
        rejects('absolute path',lambda:reader.safe(root,str(p)))
        (root/'linked').symlink_to(root,target_is_directory=True)
        rejects('ancestor symlink',lambda:reader.safe(root,'linked/body'))
        rejects('supplied root symlink',lambda:reader.safe(root/'linked','body'))
        import gzip
        z=gzip.compress(b'whole',mtime=0)
        assert reader.gunzip(z,5)==b'whole';passed.append('whole compressed positive')
        rejects('decoded EOF bound',lambda:reader.gunzip(z,4))
        rejects('decoded declared overbound',lambda:reader.gunzip(z,reader.CAP+1))
    types=[{'attribute':a,'valid_from':b,'valid_to':e,'method':'reference','status':'reference'} for a,b,e in sorted(products.INTERVALS)]
    index={'types':types,'values':['retained']}
    rows={id:[[j,0,.75,1] for j in range(7)] for id in products.TARGETS}
    products.validate_fresh(index,rows,{});passed.append('all fourteen tuple identities positive')
    bad=copy.deepcopy(rows);bad.pop(next(iter(bad)))
    rejects('missing target ID',lambda:products.validate_fresh(index,bad,{}))
    bad=copy.deepcopy(rows);bad[next(iter(bad))].append(bad[next(iter(bad))][0])
    rejects('duplicate tuple interval',lambda:products.validate_fresh(index,bad,{}))
    bad=copy.deepcopy(rows);bad[next(iter(bad))][0][0]=99
    rejects('foreign type/category',lambda:products.validate_fresh(index,bad,{}))
    bad=copy.deepcopy(rows);bad[next(iter(bad))][0][2]=float('nan')
    rejects('nonfinite diagnostic',lambda:products.validate_fresh(index,bad,{}))
    bad=copy.deepcopy(rows);bad[next(iter(bad))].pop()
    rejects('missing tuple without scientific reason',lambda:products.validate_fresh(index,bad,{}))
    index_bad=copy.deepcopy(index);index_bad['types'][0]['valid_to']+=1
    rejects('changed source interval',lambda:products.validate_fresh(index_bad,rows,{}))
    import gzip, hashlib
    target_ids=sorted(products.TARGETS)
    ids=set(target_ids)|{'fixture:'+str(j) for j in range(49623)}
    groups=[[id,rs] for id,rs in rows.items()]
    def original_fixture(groups):
        body=gzip.compress(json.dumps(groups).encode(),mtime=0)
        old={'version':2,'locations':49625,'parts':['fixture.gz'],
             'parts_sha256':{'fixture.gz':hashlib.sha256(body).hexdigest()},
             'records':sum(len(rs) for _,rs in groups),'types':types,'values':['retained']}
        return old,{'fixture.gz':body}
    old,body=original_fixture(groups)
    products.records(old,body,ids);passed.append('complete original fourteen groups positive')
    old,body=original_fixture(groups[:1])
    rejects('entire original target omission with coherent counts/hashes',lambda:products.records(old,body,ids))
    old,body=original_fixture(groups+[[target_ids[0],[]]])
    rejects('duplicate within-part identity coherently rehashed',lambda:products.records(old,body,ids))
    duplicate=copy.deepcopy(groups);duplicate[0][1].append(duplicate[0][1][0])
    old,body=original_fixture(duplicate)
    rejects('duplicate original tuple coherently rehashed',lambda:products.records(old,body,ids))
    # Legitimate stock split attributes across different parts remain valid.
    first=[[id,rs[:6]] for id,rs in groups];second=[[id,rs[6:]] for id,rs in groups]
    old,body=original_fixture(first);other=gzip.compress(json.dumps(second).encode(),mtime=0)
    old['parts'].append('topography.gz');old['parts_sha256']['topography.gz']=hashlib.sha256(other).hexdigest()
    old['records']=14;body['topography.gz']=other
    products.records(old,body,ids);passed.append('literal cross-part attribute groups retained')
    oversized=gzip.compress(b' '*(33554432+1),mtime=0)
    rejects('real gzip decoded overbound during streamed allocation',lambda:products.decode_part(oversized))
    producer=module('reference_native_producer_controls',HERE/'producer.py')
    guard=producer.native_runtime.original_guard()
    guard_raw=(HERE.parent/'reference-source-custody-20261007/runtime.py').read_bytes()
    producer.authenticated_module(guard,guard_raw);passed.append('actual loaded original helper positive')
    saved=guard.code_value
    try:
        guard.code_value=lambda value: {}
        rejects('actual loaded original fingerprint callable mutated',lambda:producer.authenticated_module(guard,guard_raw))
    finally:guard.code_value=saved
    custody=module('reference_native_custody_controls',HERE.parent/'reference-source-custody-20261007/custody.py')
    custody_raw=Path(custody.__file__).read_bytes();saved=custody.restore_original
    try:
        custody.restore_original=lambda *args: None
        rejects('actual loaded source restoration callable mutated',lambda:producer.authenticated_module(custody,custody_raw))
    finally:custody.restore_original=saved
    print(json.dumps({'status':'PASS','actual_controls':len(passed),'controls':passed,'no_native_or_world_science_run':True}))

if __name__=='__main__':run()

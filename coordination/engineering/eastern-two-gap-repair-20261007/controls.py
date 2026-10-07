"""Directed counterexamples for exact additive, source-bounded correction."""
from pathlib import Path
import json,sys,tempfile
from shapely.geometry import box,mapping
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from kernel import TARGETS,exact_addition,exact_two_feature_replacements,complete_neighbor_relations
from reader import checked_file,Inputs
from producer import authenticate_code
from evidence.immutable import canonical_json

def controls():
    passes=[]
    def check(name,fn):fn();passes.append(name)
    def reject(fn):
        try:fn()
        except(ValueError,KeyError,FileNotFoundError):return
        raise AssertionError('Expected intended rejection')
    sid,cid=next(iter(TARGETS.items()));old=box(0,0,1,1);gap=box(1,0,2,1);native=box(1,-1,3,2);envelope=box(0,-1,3,2)
    def addition_positive():
        new,data=exact_addition(sid,cid,old,gap,native,envelope)
        assert new.covers(old)and new.covers(gap)and not mapping(new)==mapping(old)
        assert data['loss']['coordinates']==()
    check('exact no-loss full gain',addition_positive)
    check('wrong authorized component',lambda:reject(lambda:exact_addition(sid,'physical-component:wrong',old,gap,native,envelope)))
    check('source misses positive gap part',lambda:reject(lambda:exact_addition(sid,cid,old,gap,box(1,0,1.5,1),envelope)))
    check('retired envelope misses positive gap part',lambda:reject(lambda:exact_addition(sid,cid,old,gap,native,box(0,0,1.5,1))))
    check('existing positive ownership rejects',lambda:reject(lambda:exact_addition(sid,cid,old,box(.5,0,2,1),native,envelope)))
    def tiny():
        g=box(1,0,1+2**-40,1);new,data=exact_addition(sid,cid,old,g,native,envelope);assert new.difference(old).equals(g)and g.area>0
    check('positive tiny whole gain never area-filtered',tiny)
    check('invalid native polygon rejected',lambda:reject(lambda:exact_addition(sid,cid,old,gap,box(1,0,1,1),envelope)))
    check('invalid commit option before any Git',lambda:reject(lambda:authenticate_code('--output=/tmp/forbidden-1295')))
    with tempfile.TemporaryDirectory()as directory:
        p=Path(directory);(p/'x').write_bytes(b'raw not JSON')
        check('raw nonJSON ordinary bytes accepted',lambda:assert_equal(checked_file(p,'x'),b'raw not JSON'))
        check('parent traversal rejects',lambda:reject(lambda:checked_file(p,'../x')))
        check('absolute path rejects',lambda:reject(lambda:checked_file(p,str(p/'x'))))
        fixture={'aliases':[{'original':{'path':'original','bytes':14,'sha256':'0'*64},'codec':'raw','ordinary':{'path':'x','bytes':12,'sha256':'0'*64,'decoded_bytes':12,'decoded_sha256':'0'*64}}]}
        (p/'input-index.json').write_bytes(canonical_json(fixture))
        check('whole ordinary input corruption rejects',lambda:reject(lambda:Inputs(p).read('original')))
        (p/'link').symlink_to(p,target_is_directory=True)
        check('ancestor symlink rejects',lambda:reject(lambda:checked_file(p,'link/x')))
    def replacement():
        features=[{'id':i,'geometry':mapping(old),'properties':{'name':i,'unchanged':1}}for i in TARGETS]
        features.extend({'id':f'fixture:{i}','geometry':mapping(old),'properties':{'name':str(i)}}for i in range(49623))
        result=exact_two_feature_replacements(features,{i:mapping(box(0,0,2,1))for i in TARGETS})
        assert result[2:]==features[2:]and [f['properties']for f in result]==[f['properties']for f in features]
        reject(lambda:exact_two_feature_replacements(features[:-1],{i:mapping(old)for i in TARGETS}))
    check('whole unchanged identities and missing49k reject',replacement)
    check('duplicate world identity rejects',lambda:reject(lambda:complete_neighbor_relations(sid,old,old,[(sid,old),(sid,old)])))
    check('new positive neighbor overlap rejects',lambda:reject(lambda:complete_neighbor_relations(sid,old,box(0,0,2,1),[(sid,old),('neighbor',box(1,0,2,1))])))
    return {'passed':len(passes),'controls':passes,'limits':'Directed fixtures are not complete-world scientific evidence.'}
def assert_equal(a,b):assert a==b
if __name__=='__main__':print(json.dumps(controls(),sort_keys=True))

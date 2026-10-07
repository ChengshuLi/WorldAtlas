"""Directed real-reader controls for original native bytes and ordered archive custody."""
import argparse
import copy
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
import custody as c


def main(output):
    cases=[]; fixtures=[]
    def test(name, callback, rejects=False):
        failed=False
        try: callback()
        except (ValueError,FileExistsError): failed=True
        if failed != rejects: raise AssertionError(name)
        cases.append({'name':name,'expected':'reject' if rejects else 'accept','outcome':'passed'})
    header=c.HEADER.pack(7,4,1+(15<<8),0,1000000,0,1000000,100,100,-1,-1)
    points=b''.join(__import__('struct').pack('>2i',*p) for p in [(0,0),(1000000,0),(0,1000000),(0,0)])
    record=header+points
    def native(raw): return list(c.parse_native(io.BytesIO(raw)))
    test('complete-big-endian-native-record',lambda:native(record))
    row=native(record)[0]
    assert row['id']==7 and row['n']==4 and row['record_sha256']==c.digest(record) and row['coordinate_bytes_sha256']==c.digest(points) and row['closed']
    test('truncated-header',lambda:native(header[:-1]),True)
    test('truncated-coordinate',lambda:native(record[:-1]),True)
    test('trailing-native-byte',lambda:native(record+b'\x00'),True)
    test('duplicate-native-id',lambda:native(record+record),True)
    test('invalid-native-level',lambda:native(c.HEADER.pack(7,4,7,0,1,0,1,1,1,-1,-1)+points),True)
    test('negative-point-count',lambda:native(c.HEADER.pack(7,-1,1,0,1,0,1,1,1,-1,-1)),True)
    for name,commit in [('branch-name','main'),('short-sha','9ec87025'),('uppercase-sha','A'*40)]:
        test(name,lambda commit=commit:c.committed(Path.cwd(),commit,'x'),True)
    repo=Path.cwd().resolve();frozen='f778478cc6f4995b0e603dafb8560fce5436ab92'
    for name,path in [('absolute-path','/catalogue.json'),('parent-traversal','../catalogue.json'),('empty-segment','a//catalogue.json'),('dot-segment','a/./catalogue.json'),('backslash-path','a\\catalogue.json')]:
        test(name,lambda path=path:c.committed(repo,frozen,path),True)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='immutable-reader-controls-',dir=output.parent) as temp:
        temp=Path(temp);index=temp/'isolated-index';env=dict(os.environ,GIT_INDEX_FILE=str(index))
        def fixture(path,raw,mode):
            def command(*args,input=None):return subprocess.check_output(['git','-C',str(repo),*args],input=input,env=env,stderr=subprocess.PIPE)
            oid=command('hash-object','-w','--stdin',input=raw).decode().strip()
            command('read-tree',frozen)
            command('update-index','--add','--cacheinfo',mode+','+oid+','+path)
            tree=command('write-tree').decode().strip()
            commit=command('commit-tree',tree,'-p',frozen,'-m','Issue1261 directed immutable-reader fixture').decode().strip()
            fixtures.append({'commit':commit,'tree':tree,'changed_path':path,'changed_mode':mode,'changed_body_sha256':c.digest(raw),'baseline':frozen})
            return commit
        link=c.OWNED+'/control-symlink'
        link_commit=fixture(link,b'catalogue.json','120000')
        test('real-committed-symlink-rejected',lambda:c.committed(repo,link_commit,link),True)
        catalogue=json.loads(c.committed(repo,frozen,c.OWNED+'/catalogue.json'))
        catalogue['member']='gshhs_h.b'
        wrong_commit=fixture(c.OWNED+'/catalogue.json',(json.dumps(catalogue,sort_keys=True,separators=(',',':'))+'\n').encode(),'100644')
        def wrong_member():
            try:c.run(repo,wrong_commit,temp/'wrong-member-output')
            except ValueError as error:
                if str(error)!='Whole native member identity mismatch':raise AssertionError('Wrong rejection branch: '+str(error))
                raise
            raise AssertionError('Wrong existing member was accepted')
        test('actual-complete-wrong-existing-member-rejected',wrong_member,True)
    bodies={'one':b'abcdef','two':b'ghijk'}
    cat={'original_bytes':11,'original_sha256':c.digest(b'abcdefghijk'),'parts':[dict(path=k,bytes=len(v),sha256=c.digest(v),ordinal=i,offset=0 if i==0 else 6) for i,(k,v) in enumerate(bodies.items())]}
    def reconstructed(value,source=None):
        with tempfile.TemporaryDirectory() as tmp:
            return c.reconstruct(value,lambda p:(source or bodies)[p],Path(tmp)/'original')
    test('complete-ordered-byte-reconstruction',lambda:reconstructed(cat))
    altered=copy.deepcopy(cat);altered['parts'].reverse()
    test('reordered-fragments',lambda:reconstructed(altered),True)
    altered=copy.deepcopy(cat);altered['parts']=altered['parts'][:-1]
    test('omitted-fragment',lambda:reconstructed(altered),True)
    altered=copy.deepcopy(cat);altered['parts'].append(altered['parts'][0])
    test('extra-duplicate-fragment',lambda:reconstructed(altered),True)
    altered=copy.deepcopy(cat);altered['parts'][1]['offset']=5
    test('wrong-fragment-offset',lambda:reconstructed(altered),True)
    altered=copy.deepcopy(cat);altered['parts'][0]['bytes']=c.LIMIT+1
    test('oversized-fragment-descriptor',lambda:reconstructed(altered),True)
    test('changed-fragment-bytes',lambda:reconstructed(cat,{'one':b'abcdeg','two':b'ghijk'}),True)
    altered=copy.deepcopy(cat);altered['original_sha256']=c.digest(b'other product')
    test('wrong-whole-product-hash',lambda:reconstructed(altered),True)
    altered=copy.deepcopy(cat);altered['original_bytes']=12
    test('wrong-whole-product-size',lambda:reconstructed(altered),True)
    result={'method_id':'original-gshhg-custody','outcome':'passed','controls':cases,'controls_code_sha256':c.digest(Path(__file__).read_bytes()),'producer_code_sha256':c.digest(Path(c.__file__).read_bytes()),'actual_immutable_git_fixtures':fixtures,'fixture_limits':['Controlled Git trees reuse complete real immutable source bodies; no extra checkout, branch, numerical inventory or altered original producer. Wrong existing-member identity is rejected by the real full ZIP member reader.']}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.open('xb').write((json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode())
    print(len(cases),'controls passed')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args();main(Path(args.output))

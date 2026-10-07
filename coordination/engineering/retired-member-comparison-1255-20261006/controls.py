"""Directed actual-kernel/byte-reader/output-guard controls, not world generation."""
import argparse,gzip,json,pathlib,sys,tempfile,unittest.mock
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R));sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon
from kernel import member_union,compare
from reader import Inputs,output_target,SHA
from shapely.geometry import box,mapping
from shapely.errors import GEOSException


def feature(i,g):return {'id':i,'geometry':mapping(g)}
def rejected(fn,needle):
    try:fn()
    except ValueError as e:
        assert needle in str(e),(needle,str(e));return
    raise AssertionError('Intended rejection absent: '+needle)


def run(commit,out):
    results=[]
    def checked(name,fn):fn();results.append({'control':name,'outcome':'passed'})
    original=feature('m',box(0,0,2,2));diag,u=member_union([original]);assert diag['status']=='literal-original-member-union'
    for name,g,status in [('full',box(.2,.2,1,1),'original-member-union-covers-component'),('partial',box(1,1,3,3),'positive-area-partial-original-member-coverage'),('outside',box(3,3,4,4),'no-original-member-intersection-in-literal-domain'),('touch',box(2,0,3,1),'zero-area-original-member-contact')]:
        row=compare(feature(name,g),u);assert row['status']==status and row['administrative_assignment']is None and row['physical_status']=='unverified';results.append({'control':name,'outcome':'passed'})
    invalid={'id':'bad','geometry':{'type':'Polygon','coordinates':[[[0,0],[1,1],[1,0],[0,1],[0,0]]]}}
    d,v=member_union([invalid]);assert v is None and d['status']=='unknown-invalid-original-member';results.append({'control':'invalid original member is unknown','outcome':'passed'})
    rows=[]
    class Broken:
        is_empty=False;is_valid=True;geom_type='Polygon'
        def intersection(self,_):raise GEOSException('fixture injected middle operation')
    import kernel
    actual=kernel.shape
    def injected(g):return Broken()if g.get('injected')else actual(g)
    cohort=[feature('first',box(.2,.2,1,1)),{'id':'middle','geometry':{'injected':True}},feature('last',box(.3,.3,1,1))]
    with unittest.mock.patch.object(kernel,'shape',injected):rows=[compare(f,u)for f in cohort]
    assert [r['component']for r in rows]==['first','middle','last']and rows[1]['status']=='unknown-failed-component-operation'and rows[1]['administrative_assignment']is None and rows[2]['status']=='original-member-union-covers-component';results.append({'control':'failed middle row preserves complete cohort','outcome':'passed'})
    for bad in [PREFIX+'/../escape',PREFIX+'/x//bad',PREFIX+'/x/./bad','/absolute/path','elsewhere/x',PREFIX+'\\bad']:
        checked('invalid output '+bad,lambda bad=bad:rejected(lambda:output_target(R,PREFIX,bad),'Unsafe repository path'if '..'in bad or '//'in bad or '/./'in bad or bad.startswith('/')or'\\'in bad else'outside'))
    temp=pathlib.Path(tempfile.mkdtemp(prefix='control-',dir=P/'.cache'));sentinel=temp/'sentinel';sentinel.write_bytes(b'preserve')
    symlink=temp/'linked';symlink.symlink_to(temp,target_is_directory=True)
    checked('symlink output rejected',lambda:rejected(lambda:output_target(R,PREFIX,str((symlink/'fresh').relative_to(R))),'Symlink'))
    checked('existing destination rejected',lambda:rejected(lambda:output_target(R,PREFIX,str(temp.relative_to(R))),'Existing'))
    assert sentinel.read_bytes()==b'preserve'and not(temp/'fresh').exists()
    index=json.loads((P/'input-index.json').read_bytes());reader=Inputs(R,commit,PREFIX)
    raw=reader.read('input-index.json');checked('changed ordinary full pin rejects',lambda:rejected(lambda:reader.read('input-index.json',{'bytes':len(raw),'sha256':'0'*64}),'Changed input'))
    actual_archive=reader.archive(index);assert len(actual_archive['locations'])==19050;results.append({'control':'complete original encoded+decoded fragment relationship','outcome':'passed'})
    for kind in ['encoded','decoded']:
        changed=json.loads(canon(index));changed['archive'][kind]['parts'][0]['offset']=1
        checked(kind+' wrong offset rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Missing/reordered'))
        changed=json.loads(canon(index));changed['archive'][kind]['parts'].pop()
        checked(kind+' missing fragment rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Archive whole bytes'))
        changed=json.loads(canon(index));changed['archive'][kind]['whole_sha256']='0'*64
        checked(kind+' wrong whole hash rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Archive whole bytes'))
    reader.close();out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(canon({'controls':results,'count':len(results),'world_generation':False,'limitations':['Directed controls do not approve factual source roles or replace two complete final runs.']}));print(json.dumps({'controls':len(results),'out':str(out)}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--code-commit',required=True);a.add_argument('--output',required=True);x=a.parse_args();(P/'.cache').mkdir(exist_ok=True);run(x.code_commit,pathlib.Path(x.output))

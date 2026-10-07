"""Directed actual-kernel/byte-reader/output-guard controls, not world generation."""
import argparse,gzip,json,pathlib,sys,tempfile,unittest.mock,subprocess
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];PREFIX=str(P.relative_to(R));sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon
from kernel import member_union,compare
from reader import Inputs,output_target,SHA,validate_family_scope,validate_pointsets,authenticate_executed_modules
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
    for malformed in [None,{'type':'Polygon','coordinates':[]}]:
        d,v=member_union([{'id':'malformed','geometry':malformed}]);assert v is None and d['status']=='unknown-invalid-original-member'
        r=compare({'id':'malformed','geometry':malformed},u);assert r['status'].startswith('unknown-')and r['administrative_assignment']is None
        results.append({'control':'malformed/empty geometry retained unknown','outcome':'passed'})
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
    before=sorted(str(p.relative_to(R))for p in P.rglob('*'))
    for bad in [PREFIX+'/../escape-cli',PREFIX+'/x//bad-cli','/absolute/invalid-cli','elsewhere/invalid-cli',str((symlink/'fresh').relative_to(R))]:
        r=subprocess.run([sys.executable,str(P/'producer.py'),'--code-commit',commit,'--output',bad],capture_output=True)
        assert r.returncode!=0 and b'processed'not in r.stdout and sorted(str(p.relative_to(R))for p in P.rglob('*'))==before
        results.append({'control':'actual CLI rejects before writes '+bad,'outcome':'passed'})
    assert sentinel.read_bytes()==b'preserve'
    for malformed in ['short','G'*40,'--output='+str(temp/'unsafe-git-output')]:
        with unittest.mock.patch('reader.subprocess.check_output',side_effect=AssertionError('Git must not be called')):
            checked('commit validated before Git '+malformed,lambda malformed=malformed:rejected(lambda:authenticate_executed_modules(R,malformed,[PREFIX+'/reader.py']),'Immutable execution commit'))
        before=sorted(str(p.relative_to(R))for p in P.rglob('*'))
        r=subprocess.run([sys.executable,str(P/'producer.py'),'--code-commit='+malformed,'--output',PREFIX+'/.cache/invalid-commit-cli'],capture_output=True)
        assert r.returncode!=0 and b'Immutable execution commit required before Git'in r.stderr and sorted(str(p.relative_to(R))for p in P.rglob('*'))==before and sentinel.read_bytes()==b'preserve'
        results.append({'control':'actual CLI rejects commit/option before Git or output writes '+malformed,'outcome':'passed'})
    fixture={'id':'c','geometry':mapping(box(0,0,1,1))};member={**fixture,'id':'m','metadata':{'number':1}}
    sc={'family_ids':['f'],'component_ids':['c'],'member_ids':['m'],'contact_ids':['t'],'roster_canonical_sha256':{'families':SHA(canon(['f'])),'components':SHA(canon(['c'])),'members':SHA(canon(['m']))},'existing_current_component_and_member_pins':[{'id':'c','canonical_feature_sha256':SHA(canon(fixture)),'geometry_sha256':SHA(canon(fixture['geometry']))}],'retired_member_complete_record_pins':[{'id':'m','canonical_record_sha256':SHA(canon(member)),'canonical_geometry_sha256':SHA(canon(member['geometry'])),'metadata':member['metadata']}]}
    fam={'f':{'component_ids':['c'],'component_count':1,'component_ids_sha256':SHA(canon(['c'])),'contact_ids':['t'],'source_families':[{'kind':'physical-adaptation-processing-reproduction','original_source_member_ids':['m']}]}}
    validate_family_scope(sc,fam,(1,1,1,1));validate_pointsets(sc,{'c':fixture},{'m':member});results.append({'control':'complete fixture source/member/pointset scope','outcome':'passed'})
    for field in ['component_ids','contact_ids','member_ids']:
        altered=json.loads(canon(sc));altered[field]=[]
        checked('omitted '+field,lambda altered=altered:rejected(lambda:validate_family_scope(altered,fam,(1,1,1,1)),'Complete fixed scope'))
    altered=json.loads(canon(fam));altered['f']['source_families'][0]['kind']='administrative-authority'
    checked('source role promotion rejects',lambda:rejected(lambda:validate_family_scope(sc,altered,(1,1,1,1)),'Wrong source role'))
    altered=json.loads(canon(member));altered['metadata']['number']=1.0
    checked('numerically equal metadata representation mutation rejects',lambda:rejected(lambda:validate_pointsets(sc,{'c':fixture},{'m':altered}),'metadata representation'))
    checked('missing component pointset rejects',lambda:rejected(lambda:validate_pointsets(sc,{}, {'m':member}),'current component'))
    checked('missing member pointset rejects',lambda:rejected(lambda:validate_pointsets(sc,{'c':fixture},{}),'member bindings'))
    with unittest.mock.patch.object(pathlib.Path,'read_bytes',return_value=b'changed local code'):
        checked('executed local code mutation rejects',lambda:rejected(lambda:authenticate_executed_modules(R,commit,[PREFIX+'/reader.py']),'Executed'))

    index=json.loads((P/'input-index.json').read_bytes());reader=Inputs(R,commit,PREFIX)
    raw=reader.read('input-index.json');checked('changed ordinary full pin rejects',lambda:rejected(lambda:reader.read('input-index.json',{'bytes':len(raw),'sha256':'0'*64}),'Changed input'))
    for a in index['aliases']:
        raw=reader.original(a['original']['commit'],a['original']['path'],index,parse=False)
        assert len(raw)==a['original']['decoded_bytes']and SHA(raw)==a['original']['decoded_sha256']
    results.append({'control':'every whole original alias authenticates bytes without forcing recipe text into JSON','outcome':'passed'})
    actual_archive=reader.archive(index);assert len(actual_archive['locations'])==19050;results.append({'control':'complete original encoded+decoded fragment relationship','outcome':'passed'})
    for kind in ['encoded','decoded']:
        changed=json.loads(canon(index));changed['archive'][kind]['parts'][0]['offset']=1
        checked(kind+' wrong offset rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Missing/reordered'))
        changed=json.loads(canon(index));changed['archive'][kind]['parts'].pop()
        checked(kind+' missing fragment rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Archive whole bytes'))
        changed=json.loads(canon(index));changed['archive'][kind]['whole_sha256']='0'*64
        checked(kind+' wrong whole hash rejects',lambda changed=changed:rejected(lambda:reader.archive(changed),'Archive whole bytes'))
    alias=index['aliases'][0];bad_index=json.loads(canon(index));bad_alias=bad_index['aliases'][0];bad=b'not-json-original-fixture'
    bad_alias['original'].update(bytes=len(bad),sha256=SHA(bad),decoded_bytes=len(bad),decoded_sha256=SHA(bad))
    with unittest.mock.patch.object(reader,'read',return_value=bad):
        assert reader.original(bad_alias['original']['commit'],bad_alias['original']['path'],bad_index,parse=False)==bad
        checked('malformed actual JSON decoder path rejects after byte authentication',lambda:rejected(lambda:reader.original(bad_alias['original']['commit'],bad_alias['original']['path'],bad_index),'Expecting value'))
    from verify import normalized_diagnostic,validate_diagnostic
    expected=compare(feature('diagnostic',box(.2,.2,1,1)),u);stored=normalized_diagnostic(expected)
    objects={SHA(canon(expected[k]['geometry'])):expected[k]['geometry']for k in ['intersection','difference']}
    validate_diagnostic(stored,expected,objects);results.append({'control':'complete scientific diagnostic positive','outcome':'passed'})
    for change in ['status','intersection','difference','partition_equals_original','member_union_covers_component','area_arithmetic_delta']:
        changed=json.loads(canon(stored))
        if change=='status':changed[change]='unknown-original-member-union'
        elif change in ['intersection','difference','partition_equals_original']:changed.pop(change)
        else:changed[change]=not changed[change]if isinstance(changed[change],bool)else 999
        # Rebound counts and whole-shard digest cannot hide scientific mutation.
        rebound={'counts':{changed['status']:1},'shard_sha256':SHA(canon([changed]))}
        assert rebound['shard_sha256']==SHA(canon([changed]))
        checked('rebound diagnostic '+change+' rejects',lambda changed=changed:rejected(lambda:validate_diagnostic(changed,expected,objects),'Complete scientific diagnostic'))
    unknown,_=member_union([invalid]);unknown_stored=normalized_diagnostic(unknown);validate_diagnostic(unknown_stored,unknown,{})
    for change in ['status','invalid_members','failure_class']:
        altered=json.loads(canon(unknown_stored))
        if change=='status':altered['status']='literal-original-member-union'
        elif change=='invalid_members':altered['invalid_members']=[]
        else:altered['invalid_members'][0]['failure_class']='invented'
        checked('unknown original member '+change+' rejects',lambda altered=altered:rejected(lambda:validate_diagnostic(altered,unknown,{}),'Complete scientific diagnostic'))
    for change in ['commit','path','sha256']:
        altered=json.loads(canon(index));a=altered['aliases'][0]
        if change in ['commit','path']:a['original'][change]='0'*40 if change=='commit'else 'wrong-source-report.json'
        else:a['original']['sha256']='0'*64
        expected_error='Original whole containing input omitted'if change in ['commit','path']else'Original alias relationship'
        checked('wrong frozen source selector '+change+' rejects',lambda altered=altered:rejected(lambda:reader.original(alias['original']['commit'],alias['original']['path'],altered,parse=False),expected_error))
    reader.close();out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(canon({'controls':results,'count':len(results),'world_generation':False,'limitations':['Directed controls do not approve factual source roles or replace two complete final runs.']}));print(json.dumps({'controls':len(results),'out':str(out)}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--code-commit',required=True);a.add_argument('--output',required=True);x=a.parse_args();(P/'.cache').mkdir(exist_ok=True);run(x.code_commit,pathlib.Path(x.output))

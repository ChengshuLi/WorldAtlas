"""Authenticate two complete leaf output vintages in one bounded metadata phase."""
import argparse,gzip,json,pathlib,subprocess,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import refresh
bio=refresh.bio
Q=refresh.Q

def compare(repo,head,ordinal,destination):
    planpath=Q+'inputs/pair-pins.json';raw=refresh.metadata(repo,head,planpath);plan=json.loads(raw);bio.need(type(ordinal) is int and 1<=ordinal<=7,'Exact paired leaf ordinal');row=plan[ordinal-1];bio.need(row['ordinal']==ordinal,'Whole pair ordinal')
    runtimepath=Q+'inputs/runtime.json';runtime_raw=refresh.metadata(repo,head,runtimepath);runtime=json.loads(runtime_raw)
    code=[]
    for path in (*refresh.CODE,Q+'compare.py'):
        body=refresh.metadata(repo,head,path);bio.need((repo/path).read_bytes()==body,'Actual comparison code binding');code.append({'commit':head,'path':path,'bytes':len(body),'sha256':bio.sha(body)})
    own=[{'commit':head,'path':path,'bytes':len(body),'sha256':bio.sha(body)} for path,body in ((planpath,raw),(runtimepath,runtime_raw))]
    pins=own+code+row['inventories']+[p for pair in row['pairs'] for p in pair]
    phase=bio.Phase(repo,repo/Q/'vintages'/destination,pins,1048576,runtime['files'])
    for p in own+code:phase.read(p)
    invs=[json.loads(phase.read(p)) for p in row['inventories']]
    bio.need(all(v['facts']['execution_commit']=='7743d731c33215cc926ba84d967b31631abac34f' and v['facts']['ordinal']==ordinal for v in invs),'Actual original execution vintage/ordinal')
    result=[]
    for pair in row['pairs']:
        bio.need(len(pair)==2 and pathlib.PurePosixPath(pair[0]['path']).name==pathlib.PurePosixPath(pair[1]['path']).name,'Exact complete paired output names')
        for n,p in enumerate(pair):bio.need(any(all(p.get(k)==v.get(k) for k in ('path','bytes','sha256','uncompressed_bytes','uncompressed_sha256')) for v in invs[n]['outputs']),'Complete original inventory custody')
        bio.need(all(pair[0].get(k)==pair[1].get(k) for k in ('bytes','sha256','uncompressed_bytes','uncompressed_sha256')),'Whole encoded and decoded pair disagreement')
        bodies=[phase.read(p) for p in pair];bio.need(bodies[0]==bodies[1],'Whole complete decoded pair disagreement')
        modes=[refresh.git(repo,'ls-tree',p['commit'],'--',p['path']).decode().split()[0] for p in pair];bio.need(modes==['100644','100644'],'Exact ordinary paired modes')
        result.append({'name':pathlib.PurePosixPath(pair[0]['path']).name,'pairs':pair,'mode':'100644','whole_encoded_decoded_equal':True})
    bio.need(len(row['pairs'])==len(invs[0]['outputs'])==len(invs[1]['outputs']),'No omitted complete catalog or membership body')
    phase.output('pair.json',bio.canonical({'ordinal':ordinal,'component_count':invs[0]['facts']['component_count'],'original_execution_commit':invs[0]['facts']['execution_commit'],'outputs':result,'whole_equal':True,'limits':['Metadata byte/mode equivalence only; no scientific recomputation.']}))
    return refresh.finish(phase,code,{'stage':'complete-refreshed-leaf-pair','ordinal':ordinal,'component_count':invs[0]['facts']['component_count'],'whole_equal':True})

def main():
    p=argparse.ArgumentParser();p.add_argument('--head',required=True);p.add_argument('--ordinal',type=int,required=True);p.add_argument('--destination',required=True);a=p.parse_args();repo=pathlib.Path(refresh.git(pathlib.Path.cwd(),'rev-parse','--show-toplevel').decode().strip());bio.need(refresh.git(repo,'rev-parse','HEAD').decode().strip()==a.head,'Actual comparison head');bio.need(__import__('re').fullmatch('[a-zA-Z0-9-]+',a.destination),'Fresh plain comparison destination');print(json.dumps(compare(repo,a.head,a.ordinal,a.destination),sort_keys=True))
if __name__=='__main__':main()

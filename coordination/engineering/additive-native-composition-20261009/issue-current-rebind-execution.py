"""Fresh whole local Mac pre-use issuer; original Python lineage preserved."""
import pathlib,sys,json,os,importlib.util
HERE=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rebind_execution_contract',HERE/'execution-contract.py');contract=importlib.util.module_from_spec(spec);exec(compile((HERE/'execution-contract.py').read_bytes(),str(HERE/'execution-contract.py'),'exec'),contract.__dict__)

def issue(root,head,plan_path,destination,output):
 assert root.is_absolute() and len(head)==40 and all(c in '0123456789abcdef' for c in head)
 assert destination.is_relative_to(root/'.cache') and output.is_relative_to(root/'.cache')
 for p in [plan_path,destination,output]:
  assert p.is_absolute() and '..' not in p.parts
  for a in p.parents:assert not a.is_symlink() and a.is_dir()
 assert not os.path.lexists(destination) and not os.path.lexists(output),'Fresh output custody/destination required'
 stat=plan_path.stat();assert stat.st_size<=131072 and stat.st_mode&0o777==0o644
 raw=plan_path.read_bytes();plan=json.loads(raw);assert plan['execution_commit']==head and 0<plan['limits']['complete_phase_bytes']<=contract.PHASE
 for name in ['mac-execution-runtime-original.json','run-current-rebind.mjs','supervise-current-rebind.py']:
  assert (HERE/name).stat().st_size<=131072 and not (HERE/name).is_symlink()
 assert [p['path'] for p in plan['executed_code']]==json.loads((HERE/'execution-code-paths.json').read_bytes())
 runtime=json.loads((HERE/'mac-execution-runtime-original.json').read_text())['runtime']
 assert pathlib.Path(sys.executable).resolve()==pathlib.Path(next(p['path'] for p in runtime if p['role']=='supervisor-python')).resolve(),'Actual Python executable differs from bound runtime'
 for name in ['package.json','sha2.js','_md.js','_u64.js','utils.js']:
  source=next(p for p in plan['executed_code'] if p['path'].endswith('/module-bodies/'+name));p=root/'node_modules'/'@noble'/'hashes'/name
  runtime.append({'role':'installed-dependency','path':str(p),'bytes':source['bytes'],'sha256':source['sha256'],'mode':0o644})
 # Declare actual source/stat descriptors before any runtime/code body opens.
 def ordinary(p):s=p.stat();assert s.st_size<=contract.FILE and s.st_mode&0o777==0o644;return {'path':str(p),'bytes':s.st_size,'sha256':contract.digest(p.read_bytes()),'mode':0o644}
 # Small entry/supervisor metadata bodies have their own fixed1MiB metadata
 # admission. Full installed runtime is only opened by capture after union stats.
 pre={'runtime':runtime,'code':plan['executed_code'],'entry':ordinary(HERE/'run-current-rebind.mjs'),'supervisor':ordinary(HERE/'supervise-current-rebind.py'),'plan':{'path':str(plan_path),'bytes':len(raw),'sha256':contract.digest(raw),'mode':0o644}}
 python_extra=sum(p['bytes'] for p in runtime if p['role'] not in ('node','git','installed-dependency'))
 operating=plan['limits']['complete_phase_bytes']+python_extra+contract.OUTPUT+contract.META
 assert operating<=contract.PHASE,'Whole child carried union plus actual external runtime/output reserve exceeds operating phase'
 contract.capture(root,head,pre)
 command=[next(p['path'] for p in runtime if p['role']=='time'),'-l',next(p['path'] for p in runtime if p['role']=='node'),'--expose-gc',pre['entry']['path'],str(plan_path),str(destination)]
 result={'version':1,'kind':'issued-current-rebind-execution-pre-use-v1','execution_commit':head,'root':str(root),'command':command,'pre_use':pre,'operating_phase_bytes':operating,'output_log_reserve_bytes':contract.OUTPUT}
 body=contract.canonical(result);assert len(body)<=131072
 fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 try:os.write(fd,body)
 finally:os.close(fd)
 return result
if __name__=='__main__':
 assert sys.flags.isolated and sys.dont_write_bytecode,'Use exact isolated Python -I -B entry'
 assert len(sys.argv)==7
 result=issue(pathlib.Path(sys.argv[1]),sys.argv[2],pathlib.Path(sys.argv[3]),pathlib.Path(sys.argv[4]),pathlib.Path(sys.argv[5]));assert sys.argv[6]=='issue-only';print(json.dumps({'bytes':len(contract.canonical(result)),'sha256':contract.digest(contract.canonical(result)),'operating_phase_bytes':result['operating_phase_bytes']}))

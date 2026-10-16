import pathlib,subprocess,os,json,hashlib,gzip,time,datetime
w=pathlib.Path.cwd();d=w/'.takeover/original-package-completion-audit/frozen-original-repair39315';d.mkdir(exist_ok=True);inp=d/'inputs';inp.mkdir(exist_ok=True);b=w/'.takeover/private-recovery.git';c='f7c358326d776398bc1cffe84df81eac7033091c';prefix='coordination/engineering/global-current-cell-work-queue-20261014/';env={**os.environ,'GIT_NO_LAZY_FETCH':'1'};inventory=[]
def g(*a):return subprocess.check_output(['git','-c','protocol.allow=never','--git-dir='+str(b),*a],env=env)
def read(name):
 path=prefix+name;line=g('ls-tree','-z',c,'--',path).decode();assert line.startswith('100644 blob ')and line.endswith('\t'+path+'\0');oid=line.split()[2].split('\t')[0];raw=g('cat-file','blob',oid);assert hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest()==oid;target=inp/name
 if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 else:assert target.read_bytes()==raw
 inventory.append({'commit':c,'path':path,'mode':'100644','git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});return raw
manifest=json.loads(read('source-package-queue.json'));pkg=manifest['packages'][16];assert pkg['package_id']=='gb-MMR-ADM3--repair-evaluation'and pkg['native_cells']==39315
read('source-batch-intervals.mjs')
for name in manifest['input_sha256']:
 if g('ls-tree','-z',c,'--',prefix+name):read(name)
 else:read(name+'.gz')
source=json.loads((inp/'source-census-summary.json').read_bytes());physical=json.loads((inp/'physical-unassigned-summary.json').read_bytes())
for block in pkg['native_blocks']:
 pin=source['blocks'][block]
 for part in pin.get('parts',[{'path':f'source-candidates-block-{block:03d}.json.gz'}]):read(part['path'])
 for kind in ['physical-support','inland-water-support']:read(f'{kind}-block-{block:03d}.json.gz')
start=time.monotonic();cmd=['node',str(inp/'source-batch-intervals.mjs'),'gb-MMR-ADM3--repair-evaluation',str(d/'output')];env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None);r=subprocess.run(cmd,env=env,capture_output=True);(d/'actual-extraction.stdout.json').write_bytes(r.stdout);(d/'actual-extraction.stderr.log').write_bytes(r.stderr);assert r.returncode==0,r.stderr
rows=[]
for block in pkg['native_blocks']:rows.extend(json.load(gzip.open(d/'output'/f'block-{block:03d}.json.gz')))
keys=[[o,row[0],x]for row in rows for o in row[3]for x in range(row[1],row[2])];assert len(keys)==39315 and len(set(map(tuple,keys)))==39315
result={'kind':'actual-frozen-stock-original-Myanmar-repair39315-interval-extraction','source_vintage':c,'original_package':'gb-MMR-ADM3--repair-evaluation','command':cmd,'exact_original_cells':len(keys),'exact_original_intervals':len(rows),'native_blocks':pkg['native_blocks'],'elapsed_seconds':time.monotonic()-start,'source_or_native_scientific_replays':0,'stock_extraction_only':True,'whole_materialized_input_bytes':sum(p['bytes']for p in inventory),'inputs':inventory,'rows':rows};(d/'exact-original-repair39315-intervals.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in['inputs','rows','command']},indent=2))

import datetime,json,os,pathlib,subprocess,time
TASK=pathlib.Path('/Users/chengshuli/Documents/Codex/2026-10-14/task-2/.cache/worker5-mmr2041-delivery-001')
OUT=TASK/'actual-selected-joint-001';OUT.mkdir(exist_ok=False)
ROOT=pathlib.Path('/Users/chengshuli/world-atlas-workspace/.worldatlas-workspaces/8c86b01772c1c827/deffe01c536ee2f18f79ce6584ab3dc5127d53015f04a5988e18700e807b9c01/work')
HEAD='193c36b73ea1a47c370161189d83c260181eb256';BASE='b6382262f8d03d9e7d33b26d8adb40a55197262b';CANDIDATE='64906aa677fde4f35dbc13d3585b4b85d19f0977';DEST=ROOT/'.cache/worker5-mmr2041-selected-native-001'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args]).decode().strip()
assert git('rev-parse','HEAD')==HEAD and not git('status','--porcelain','--untracked-files=normal')
assert git('rev-parse',HEAD+'^{tree}')=='63b04070d599239073c8308ce4c993cdec65a2f5'
assert not DEST.exists()
env=dict(os.environ)
token=env.get('GH_TOKEN') or subprocess.check_output(['gh','auth','token'],stderr=subprocess.PIPE).decode().strip()
assert token
env['GH_TOKEN']=token;env['GITHUB_REPOSITORY']='ChengshuLi/WorldAtlas'
cmd=['/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs',str(ROOT),HEAD,BASE,CANDIDATE,str(DEST)]
record={'command':cmd,'cwd':str(ROOT),'actual_executing_head':HEAD,'actual_reviewed_multipart_root_tree':'63b04070d599239073c8308ce4c993cdec65a2f5','accepted_baseline':BASE,'candidate':CANDIDATE,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'authentication':'Existing GitHub authentication provided transiently; no value recorded','execution_status':'reviewed unmerged capability execution; not accepted adoption/proof','source_or_qualification_producer_replay':False,'numeric_budget_heapflags_or_artificial_deadline':False,'cold_producer_fallback':False}
(OUT/'execution-start.json').write_text(json.dumps(record,indent=2)+'\n');start=time.monotonic()
with (OUT/'stdout.json').open('wb') as stdout,(OUT/'stderr.txt').open('wb') as stderr:
    result=subprocess.run(cmd,cwd=str(ROOT),env=env,stdout=stdout,stderr=stderr)
record.update(exit_code=result.returncode,elapsed_seconds=time.monotonic()-start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),destination=str(DEST),destination_exists=DEST.exists(),root_head_after=git('rev-parse','HEAD'),accepted_or_adopted_selected_delivery=False)
(OUT/'execution.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));print((OUT/'stderr.txt').read_text()[-5000:])
if result.returncode==0:
    d=json.loads((OUT/'stdout.json').read_text());print(json.dumps({'mode':d.get('mode'),'reuse_unavailable':d.get('reuse_unavailable'),'native_status':d.get('native',{}).get('status'),'affected_rows':d.get('native',{}).get('affected_rows')}))

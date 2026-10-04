"""Whole-byte inventory of actual retained scheduling evidence, never fabricated metrics."""
import gzip, hashlib, json, subprocess
from pathlib import Path
ROOT=Path('data/engineering/startup-scheduling-20261004-a9c2')
MANIFEST=Path('coordination/engineering/startup-scheduling-20261004-a9c2/evidence-quality.json')
BASE='1179243875790e1600f0d4a4e1dd508ac9ab5bfe'
PRIOR='data/engineering/startup-20261004-a9c2/'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args])
def descriptor(path,baseline=False,role=None):
 raw=git('show',BASE+':'+path) if baseline else Path(path).read_bytes()
 row=dict(path=path,bytes=len(raw),sha256=sha(raw),hash_kind='file-bytes')
 if role:row['role']=role
 if raw[:2]==b'\x1f\x8b':
  expanded=gzip.decompress(raw);row.update(uncompressed_bytes=len(expanded),uncompressed_sha256=sha(expanded));assert len(expanded)<=32*1024*1024,path
 assert len(raw)<=32*1024*1024,path
 return row
changes=[]
for line in git('diff','--name-status','--no-renames',BASE).decode().splitlines():
 status,path=line.split('\t');changes.append((dict(A='added',M='modified',D='removed')[status],path))
for path in git('ls-files','--others','--exclude-standard').decode().splitlines():
 if path not in [p for _,p in changes]:changes.append(('added',path))
if str(MANIFEST) not in [p for _,p in changes]:changes.append(('added',str(MANIFEST)))
changes.sort(key=lambda x:x[1])
paths={path for status,path in changes if status!='added'}
paths.update(git('ls-tree','-r','--name-only',BASE,PRIOR+'candidate-package-06').decode().splitlines())
paths.update([PRIOR+'served5-reference-inputs/atlas-geography.json',PRIOR+'ownership-transport-parity-02.json',PRIOR+'reference-bundle-parity-01.json',PRIOR+'served5-reference-parity-01.json','data/canonical-grid/manifest.json','data/geographic-releases/current-manifest.json','data/geographic-releases/index.json','data/hierarchy.json','data/prepared-evidence/index.json'])
baseline=[descriptor(p,True,'original-source' if p.startswith('data/') else 'implementation-baseline') for p in sorted(paths)]
outputs=[descriptor(p) for status,p in changes if status!='removed' and p!=str(MANIFEST)]
by_path={x['path']:x for x in outputs}
receipts=[]
for status,path in changes:
 row=dict(path=path,status=status)
 if status!='added':row['original_sha256']=sha(git('show',BASE+':'+path))
 if status=='removed':raise Exception('No deletion authorized in this scheduling work')
 receipts.append(row)
metrics=[];bindings=[]
def metric(identifier,path,pointer,value,unit,evaluation):
 metrics.append(dict(id=identifier,value=value,unit=unit,vintage='archived',evaluation_commit=evaluation,input_sha256=by_path[path]['sha256']))
 bindings.append(dict(metric_id=identifier,path=path,json_pointer=pointer))
for short in sorted(ROOT.glob('*.json')):
 if not (short.name.startswith('merged745-before-') or short.name.startswith('scheduling-after-')):continue
 r=json.loads(short.read_text())
 if not r.get('completed_at_utc') and not all(k in r for k in ['initial','repeat','navigation']):raise Exception('Incomplete experiment '+str(short))
 evaluation=BASE if short.name.startswith('merged745') or short.stem=='scheduling-after-01' else git('rev-parse','4d3e66c' if int(short.stem.rsplit('-',1)[1])>=6 else '879b5d0').decode().strip()
 for visit in ['initial','repeat']:
  metric(short.stem+'-'+visit,str(short),'/'+visit+'/elapsed_ms',r[visit]['elapsed_ms'],'milliseconds',evaluation)
  for key in ['TaskDuration','ScriptDuration','JSHeapUsedSize']:
   if key in r[visit].get('metrics',{}):metric(short.stem+'-'+visit+'-'+key,str(short),'/'+visit+'/metrics/'+key,r[visit]['metrics'][key],'bytes' if key=='JSHeapUsedSize' else 'seconds',evaluation)
 for i,n in enumerate(r['navigation']):metric(short.stem+'-navigation-'+str(i),str(short),'/navigation/'+str(i)+'/elapsed_ms',n['elapsed_ms'],'milliseconds',evaluation)
for short,keys in [('scoped-tests-receipt-07.json',['tests','passed','failed','skipped']),('scoped-tests-receipt-08.json',['tests','passed','failed','skipped']),('scoped-tests-receipt-09.json',['tests','passed','failed','skipped'])]:
 r=json.loads((ROOT/short).read_text())
 for key in keys:metric(short+'-'+key,str(ROOT/short),'/'+key,r[key],'tests',git('rev-parse','4d3e66c').decode().strip())
for short,keys in [('candidate-modes-07.json',['continents','profiles','modes','year','navigation_ownership_compilations','navigation_ownership_uploads'])]:
 r=json.loads((ROOT/short).read_text())
 for key in keys:
  if isinstance(r[key],(int,float)):metric(short+'-'+key,str(ROOT/short),'/'+key,r[key],'count' if key!='year' else 'selected year',git('rev-parse','4d3e66c').decode().strip())
short='candidate-controls-07.json';r=json.loads((ROOT/short).read_text())
metric('final-canvas2d-painted-pixels',str(ROOT/short),'/fallback_pixels/painted_pixels',r['fallback_pixels']['painted_pixels'],'pixels',git('rev-parse','4d3e66c').decode().strip())
source=dict(id='retained-startup-inputs',url='https://github.com/ChengshuLi/WorldAtlas',role='Prior accepted complete transport plus unchanged source/static inputs; no new factual assertion',vintage='Main1179243875790e1600f0d4a4e1dd508ac9ab5bfe; served Site24 release5 separate from offline6',retrieved_at='2026-10-04',license=dict(status='unknown',terms='Existing upstream reuse terms not independently reapproved'),retention='restoration-only',verification='unverified',temporal_status='reference',restoration='Checkout baseline and candidate-package-06 from prior merged startup evidence; all raw files and original root are whole-byte pinned. Actual compiled vintages/source maps retained with restoration receipt, not inherited caches. Preserve all source/research/predecessor objects.',limit='Hashes and previous review do not establish original primary-source authenticity, geographic approval, historical-import permission, production object retention or served acceptance. Preview payloads local; backend actual served5; offline source6 remains distinct. Physical phone/provider wake/query phases unverified. Measurements have uncommitted source inventories and complete compiled sourcemap vintages; ancestry is not a clean-tree claim.')
manifest=dict(version=1,issue=712,lane='engineering',worker_id='engineering-startup-a9c25e14-20261004',subject_ids=[],subject_ids_sha256=sha(b'[]'),baseline=dict(commit=BASE,files=baseline,pins={},pin_files={},subject_files={}),sources=[source],outputs=outputs,change_receipts=receipts,metric_bindings=bindings,rendered_tables=[],methods=[dict(id='pinned-startup-pipeline',kind='code',description='Start ownership rows before catalog, and one-shot exact initial evidence/history/hash-pinned index while complete geography loads. Preserve all stream completion, temporal/revision/withdrawal gates, cancellation and generation isolation; no renderer, geometry, facts or source changes.',software='Node24.19.0',units='Complete inputs and exact selection'),dict(id='complete-startup-measurement',kind='measurement',description='Navigation to loader hidden plus complete selected-year canvas; all fresh/repeat samples, traces, outliers and failures retained. Actual original production root is verified before pinned local complete transports. No equivalent hosted or physical-device target claim.',software='Playwright Chromium153.0.8010.12 Linux1440x1080, no CPU/network throttle; Node24.19.0 GET-only private proxy',units='milliseconds')],metrics=metrics,summaries=[dict(metric_id=m['id'],value=m['value'],unit=m['unit']) for m in metrics],validation=[dict(method_id='complete-startup-measurement',kind=k,outcome='passed',evidence_path=str(ROOT/(k+'-07.json'))) for k in ['positive-control','negative-control']],conclusions=[dict(text='Scheduling experiments remain bounded partial implementation. Every measured sample/outlier is retained; fresh ten-second and actual served acceptance remain unmet/unverified. Complete-map timing includes Preparing and Loading, never an early canvas or hidden loader substitute.',status='unresolved',source_ids=['retained-startup-inputs']),dict(text='No publication, geographic approval, factual import, schema/provider change or issue closure. Publisher owns coherent source/static/server/release/claim/archive/rollback checks.',status='unresolved',source_ids=['retained-startup-inputs'])],stages=dict(research='partial',implementation='proposed',geographic_approval='not-requested'),commands=['node --test test/compact-map-client.test.mjs test/ownership-assets.test.mjs test/reference-bundle.test.mjs test/hosted-temporal-client.test.mjs test/hosted-temporal-geography.test.mjs','Compile declared VITE_STATIC_ATLAS/VITE_HOSTED_DATABASE frontend and use exact retained candidate06 whole-root proof with owned benchmark/modes/controls; credential only hidden stdin','python3 '+str(ROOT/'prepare-evidence.py'),'node scripts/evidence-quality.mjs '+str(MANIFEST)])
assert len(baseline)+len(outputs)<=512
assert sum(x['bytes'] for x in baseline+outputs)<=256*1024*1024
MANIFEST.parent.mkdir(parents=True,exist_ok=True);MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(descriptors=len(baseline)+len(outputs),raw_bytes=sum(x['bytes'] for x in baseline+outputs),changed_files=len(changes),metrics=len(metrics))))

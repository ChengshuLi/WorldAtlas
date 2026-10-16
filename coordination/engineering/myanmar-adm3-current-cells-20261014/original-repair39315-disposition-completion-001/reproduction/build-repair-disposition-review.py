from pathlib import Path
import json,subprocess,hashlib,os,collections,gzip
w=Path.cwd();d=w/'.takeover/original-package-completion-audit';b=w/'.takeover/private-recovery.git';out=d/'repair-exception-review';out.mkdir(exist_ok=True)
base='7ef13f96c0005b6e181a640005bd867bbc2f63d0';pending='09139b584597dbf1861d59d8c60bb8dcb4ba1dff';qualified='3be4f0b127100ce1c5374b2395ab45af263c1660';prefix='coordination/engineering/myanmar-adm3-current-cells-20261014/original-repair39315-disposition-completion-001/'
env=os.environ|{'GIT_DIR':str(b),'GIT_INDEX_FILE':str(b/'repair907-review.index'),'GIT_NO_LAZY_FETCH':'1'}
for k,c in [('GIT_AUTHOR_NAME','user.name'),('GIT_AUTHOR_EMAIL','user.email')]:env[k]=subprocess.check_output(['git','config',c]).decode().strip()
env['GIT_COMMITTER_NAME']=env['GIT_AUTHOR_NAME'];env['GIT_COMMITTER_EMAIL']=env['GIT_AUTHOR_EMAIL']
def git(*a,raw=None):return subprocess.check_output(['git','-c','protocol.allow=never',*a],env=env,input=raw)
def read(c,p):return json.loads(git('show',c+':'+p))
def save(name,x):raw=(json.dumps(x,indent=2)+'\n').encode();(out/name).write_bytes(raw);return raw
def patch(c):
 sel=read(c,'data/ownership-selection.json');side=read(c,sel['additive_release']['path']);pin=side['logical_asset_map']['patch'];v=read(pin['commit'],pin['path']);return {(row['y'],x):owner for row in v['rows']for start,end,owner in row['runs']for x in range(start,end)},pin
accepted,ap=patch(base);prepared,pp=patch(pending);original=json.load(open(d/'frozen-original-repair39315/exact-original-repair39315-intervals.json'));prior=json.load(open(d/'repair39315-accepted-and-conditional-disposition-audit.json'));remaining={tuple(r['original_key'][k]for k in ['owner','y','x']):r for r in prior['remaining_records']}
portable=json.load(open(w/'.takeover/full-foreign-variants834/portable-qualified-full-foreign13.json'));foreign={(r['original_owner'],r['y'],r['x']):r for r in portable['original_to_adopted_owner_joins']};kaw=json.load(open(w/'.takeover/remaining1295/portable-qualified-kawthoung3.json'));kawkeys=set(map(tuple,kaw['keys']))
counts=collections.Counter();rows=[];allkeys=set();exceptions=[];known=[]
for ordinal,original_row in enumerate(original['rows']):
 y,start,end,owners=original_row[:4];segments=[]
 for owner in owners:
  for x in range(start,end):
   key=(owner,y,x);assert key not in allkeys;allkeys.add(key);a=accepted.get((y,x));p=prepared.get((y,x))
   if a is not None:assert a==owner;status='actually-accepted-original-owner';newowner=owner
   elif p is not None:assert p==owner;status='prepared967-original-owner-awaiting-acceptance';newowner=owner
   elif key in foreign:status='genuinely-qualified-adopted-alternate-owner-awaiting-delivery';newowner=foreign[key]['adopted_owner']
   elif key in kawkeys:status='genuinely-qualified-original-owner-awaiting-delivery';newowner=owner
   else:
    r=remaining[key];assert r['status'].startswith('evidenced-');status=r['status'];newowner=None;exceptions.append(r)
   counts[status]+=1
   if segments and segments[-1]['owner']==owner and segments[-1]['status']==status and segments[-1]['end']==x and segments[-1]['result_owner']==newowner:segments[-1]['end']=x+1
   else:segments.append({'owner':owner,'start':x,'end':x+1,'status':status,'result_owner':newowner})
 rows.append({'original_interval_ordinal':ordinal,'original_interval_unchanged':original_row,'disposition_segments':segments})
assert len(allkeys)==39315 and len(rows)==15134 and len(exceptions)==907 and sum(counts.values())==39315
assert set(foreign)|kawkeys<=allkeys and len(foreign)==13 and len(kawkeys)==3
# Check every coverage/territorial exception against the genuine current stock diagnostic output.
diagnostics={}
for n in range(5):
 p=w/f'.cache/delivery-handoff/neither78-group{n}-native-diagnostic-001/native-diagnostic.json';v=json.load(open(p));diagnostics[n]=v
 actual={(owner,row['y'],x):reason for row in v['decision_rows']for start,end,owner,reason in row['runs']for x in range(start,end)}
 for r in exceptions:
  if r.get('diagnostic_group')==n:assert actual[tuple(r['original_key'][k]for k in ['owner','y','x'])]==r['stock_diagnostic_reason']
parent=json.load(open(w/'.takeover/remaining1295/diagnostic383/exact-Rakhine11-original-parent-holds.json'));parentkeys={tuple(r['key'])for r in parent['records']};assert len(parentkeys)==11
assert {tuple(r['original_key'][k]for k in ['owner','y','x'])for r in exceptions if 'parent-exception'in r['status']}==parentkeys
full=json.load(open(w/'.takeover/full-foreign-variants834/complete-five-full-families-observation834.json'));no={ (r['owner'],r['y'],r['x'])for r in full['records']if r['disposition']=='no-unique-existing-reference-consistent-full-foreign-target'}
assert len(no)==821 and {tuple(r['original_key'][k]for k in ['owner','y','x'])for r in exceptions if 'source-scale'in r['status']}==no
contract=read('f7c358326d776398bc1cffe84df81eac7033091c','coordination/engineering/global-current-cell-work-queue-20261014/source-package-queue.json')['packages'][16];assert contract['package_id']=='gb-MMR-ADM3--repair-evaluation'
metadata={'kind':'original-Myanmar-repair39315-complete-current-and-pending-disposition-coverage','original_package':contract,'original_cells':39315,'original_intervals':15134,'accepted_data':base,'accepted_patch':ap,'pending967':pending,'prepared_patch':pp,'genuine_followons13':qualified,'genuine_followons3':kaw['head'],'counts':dict(counts),'documented_unresolved_exceptions':907,'known_positive_followons':16,'completion_claim':False,'remaining_acceptance':'Known supported deliveries require actual accepted selected consumer/conservation, then final original-interval coverage binding and distinct review/root adoption. Exact13 alternate-owner joins remain explicit rather than original-owner matches.','intervals':rows}
save('repair39315-full-interval-outcome-map.json',metadata);save('repair907-evidence-backed-exceptions.json',{'kind':'proposed-exact-original-repair907-evidence-backed-unresolved-dispositions','records':exceptions,'counts':dict(collections.Counter(r['status']for r in exceptions)),'original_interval_and_owner_joins':'All907 exact records belong to the frozen39315 scope; all negative evidence and questions remain held.','accepted_native_credit':0});save('original-frozen-repair-contract.json',{'commit':'f7c358326d776398bc1cffe84df81eac7033091c','path':'coordination/engineering/global-current-cell-work-queue-20261014/source-package-queue.json','pointer':'/packages/16','literal_package':contract})
readme='''# Original Myanmar repair scope: proposed final disposition coverage\n\nThe original frozen work contract permits each exact interval to end in a qualified additive repair or a documented exception. This packet derives all 39,315 original keys in 15,134 literal intervals. Actual accepted 7ef data owns 37,873 original-owner keys. Pending967 adds 519 original-owner keys, and 16 genuine follow-ons await delivery: three original-owner Kawthoung keys and thirteen explicitly adopted alternate-existing-owner choices. Those thirteen preserve the original request-to-result crosswalk and cannot be counted as literal original-owner matches.\n\nThe remaining907 are precise, evidence-backed unresolved exceptions:821 original Myanmar fine/foreign-country-reference source-scale disagreements without an existing neighboring fine target in all retained simplified and same-build full families;23 whole-physical coverage holds;52 territorial-operand holds;11 original-parent holds. Neither a coarse country reference nor its absence is an automatic rejection. Every contrary source, physical issue and actual stock diagnostic remains retained. Future supported interpretation is possible; no arbitrary owner is invented to complete this contract.\n\nThis is a review/preparation packet. No completion or native acceptance is claimed before actual selected delivery of known supported additions, final original-scope intersections, distinct review and parent adoption. Original reviews and proof vintages remain literal. The accepted physical-review package independently retains294 unresolved questions.\n''';(out/'README.md').write_text(readme)
git('read-tree',qualified);inventory=[]
def stage(path,raw):
 oid=git('hash-object','-w','--stdin',raw=raw).decode().strip();git('update-index','--add','--cacheinfo','100644',oid,path);p={'path':path,'mode':'100644','git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()};inventory.append(p);return p
for file in sorted(out.iterdir()):
 if file.is_file()and file.name!='immutable-repair-disposition-review-packet.json':stage(prefix+file.name,file.read_bytes())
for name in ['exact-original-repair39315-intervals.json']:
 stage(prefix+'frozen-extraction/'+name,(d/'frozen-original-repair39315'/name).read_bytes())
for file in ['extract-original-repair39315.py','build-repair-disposition-review.py']:
 stage(prefix+'reproduction/'+file,(d/file).read_bytes())
sourcefiles=['complete-country-reference-observation1295.json','complete-current-world-contact-observation834.json','complete-current-world-contact-observation78.json','complete-original-foreign-fine-observation834.json','complete-original-foreign-fine-observation78.json','neither78-native-inputs.json']
for file in sourcefiles:stage(prefix+'retained-study/'+file,(w/'.takeover/remaining1295'/file).read_bytes())
for file in ['complete-five-full-families-observation834.json','acquisition.json']+[f'full-{c}-observation834.json'for c in ['BGD','CHN','IND','LAO','THA']]:
 stage(prefix+'retained-study/'+file,(w/'.takeover/full-foreign-variants834'/file).read_bytes())
fullsources=[]
for c in ['BGD','CHN','IND','LAO','THA']:
 file='geoBoundaries-'+c+'-ADM2.geojson.gz';pin=stage('coordination/engineering/myanmar-adm3-current-cells-20261014/full-foreign13-variant-study-001/full-sources/'+file,(w/'.takeover/full-foreign-variants834'/file).read_bytes());fullsources.append(pin)
for n in range(5):
 cache=w/f'.cache/delivery-handoff/neither78-group{n}-native-diagnostic-001'
 for f in cache.iterdir():
  if f.is_file():stage(prefix+f'actual-stock-diagnostic/group{n}/'+f.name,f.read_bytes())
 for suffix in ['config.json','execution.json','stdout.json','stderr.log']:
  f=w/f'.takeover/remaining1295/neither78-group{n}-native-diagnostic-{suffix}'
  if f.is_file():stage(prefix+f'actual-stock-diagnostic/group{n}/'+suffix,f.read_bytes())
stage(prefix+'retained-study/exact-Rakhine11-original-parent-holds.json',(w/'.takeover/remaining1295/diagnostic383/exact-Rakhine11-original-parent-holds.json').read_bytes())
tree=git('write-tree').decode().strip();head=git('commit-tree',tree,'-p',qualified,raw=b'Prepare exact original Myanmar repair disposition coverage and literal907 evidence-backed exceptions\n').decode().strip();git('update-ref','refs/heads/engineering/myanmar-repair39315-disposition-review-20261016',head)
result={'head':head,'tree':tree,'parent':qualified,'status':'prepared for distinct907 disposition review; no completion/accepted-native credit','prefix':prefix,'files':inventory,'whole_retained_source_pins':[{'commit':head,**p}for p in fullsources],'counts':dict(counts),'known_supported_followons':16,'unresolved_exceptions':907}
(out/'immutable-repair-disposition-review-packet.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in['files','whole_retained_source_pins']},indent=2))

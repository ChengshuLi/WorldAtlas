#!/usr/bin/env python3
"""Join every original Canada key to genuine stock authority or an explicit hold.

Read immutable ordinary Git bodies. This does not re-run source/physical work,
construct new authority, or assert current selected ownership or delivery credit.
"""
import argparse, gzip, hashlib, json, subprocess
from collections import Counter
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('--repo',required=True);p.add_argument('--input-commit',required=True)
p.add_argument('--accounting',required=True);p.add_argument('--handoff',required=True)
a=p.parse_args();assert len(a.input_commit)==40 and all(c in '0123456789abcdef' for c in a.input_commit)
P='coordination/engineering/canada-repair-delivery-20261017/';inputs=[]
def git(*args):return subprocess.check_output(['git','-c','protocol.allow=never','-C',a.repo,*args])
def pin(path,commit=None):
 commit=commit or a.input_commit;line=git('ls-tree','-z',commit,'--',path).decode();mode,kind,tail=line.split(' ',2);oid,actual=tail.rstrip('\0').split('\t')
 assert mode=='100644' and kind=='blob' and actual==path
 raw=git('cat-file','blob',oid)
 return {'path':path,'commit':commit,'mode':mode,'git_blob_oid':oid,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},raw

def read(name):
 descriptor,raw=pin(P+name);inputs.append(descriptor)
 return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)

def expand(rows):
 result=set();n=0
 for row in rows:
  for lo,hi,o in row['runs']:
   assert isinstance(o,int) and 0<=lo<hi
   for x in range(lo,hi):result.add((row['y'],x,o));n+=1
 assert len(result)==n,'Duplicate native keys'
 return result

package=read('frozen-original-001/package.json');original={};intervals=0
for name in git('ls-tree','-r','--name-only',a.input_commit,'--',P+'frozen-original-001/').decode().splitlines():
 if not name.endswith('.json.gz'):continue
 for y,lo,hi,owners,competitors,physical in read(name[len(P):]):
  assert len(owners)==1 and isinstance(competitors,list);intervals+=1
  for x in range(lo,hi):
   k=(y,x,owners[0]);assert k not in original;original[k]=physical
assert len(original)==package['native_cells']==438062
assert intervals==package['interval_segments']==139042
assert len({k[2] for k in original})==len(package['owners'])==209
assert Counter(original.values())=={'land':375635,'inland-water':62427}
screen=read('source-review/source-target-screening.json')
subjects=sorted(o['id'] for o in screen['owners']);assert len(subjects)==len(set(subjects))==209
app=read('aafc-native-operands-001/applicability-decision.json')
holds={(r['y'],r['x'],r['owner']):r['reason'] for r in app['held']}
assert len(holds)==len(app['held'])==103 and holds.keys()<=original.keys()
physical_owners={o for b in app['batches'] for o in b['owners']}
assert len(physical_owners)==72
physical_original={k for k in original if k[2] in physical_owners};admin_original=set(original)-physical_original
assert len(physical_original)==144097 and len(admin_original)==293965
assert len(physical_original & holds.keys())==50 and len(admin_original & holds.keys())==53
qualified=set();components=set();target_ids=set();quartets=[];batches=[]
for label,authority_name,patch_name,diag_name in [
 *[(f'aafc-{i:03d}',f'aafc-native-authority-{i:03d}',f'aafc-native-operands-001/batch-{i:03d}/requested-native-patch.json',f'aafc-native-diagnostic-{i:03d}/native-diagnostic.json') for i in range(1,6)],
 ('administrative','admin-native-authority-004','admin-supported-native-patch-003.json','admin-native-diagnostic-003/native-diagnostic.json')]:
 authority=read(authority_name+'/constructor-result.json');binding=read(authority_name+'/authority-binding.json');preimage=read(authority_name+'/original-rule-preimage.json')
 diag=read(diag_name);patch=read(patch_name);request=expand(patch['rows']);good=expand(diag['supported_rows']);bad=expand(diag['held_rows']);requested=expand(diag['requested_rows'])
 assert not good&bad and good|bad==requested and len(good)==diag['supported_cells'] and len(bad)==diag['held_cells']
 if label=='administrative':
  assert requested==admin_original and bad==admin_original & holds.keys() and len(bad)==53
 else:assert requested==request and not bad
 assert request==good
 assert authority['kind']=='existing-source-target-native-constructor-result'
 rule_pin,rule_raw=pin(P+authority_name+'/original-rule-preimage.json')
 assert authority['rule_sha256']==hashlib.sha256(rule_raw).hexdigest()
 assert {**binding,'kind':'source-target-native-rule-v1'}==preimage
 if label!='administrative':assert authority['rule_sha256']==diag['rule_sha256']
 assert authority['component_ids']==[r['component_id'] for r in authority['ledger_rows']]
 keys=set()
 for row in authority['ledger_rows']:
  assert row['disposition']=='assigned' and row['component_id'] not in components
  components.add(row['component_id']);target_ids.add(row['target_id']);members=expand(row['native_rows'])
  assert len(members)==row['native_cells'] and {k[2] for k in members}=={row['pixelIndex']}
  assert not keys&members;keys.update(members)
 assert keys==request and not qualified&keys and not keys&holds.keys();qualified.update(keys)
 # Preserve the exact original binding locator, including its original commit.
 actual,raw=pin(binding['native_patch']['path'],binding['native_patch']['commit']);assert actual==binding['native_patch']
 assert expand(json.loads(raw)['rows'])==request
 for role in ['source_evidence']:
  actual,_=pin(binding[role]['path'],binding[role]['commit']);assert actual==binding[role]
 quartet={'rule_preimage':rule_pin,'source_authority':pin(P+authority_name+'/authority-binding.json')[0],
          'ledger':pin(P+authority_name+'/constructor-result.json')[0],'native_patch':binding['native_patch']}
 quartets.append(quartet);batches.append({'label':label,'qualified_cells':len(keys),'targets':len(authority['ledger_rows']),'original_requested_cells':len(requested),'diagnostic_held_cells':len(bad)})
assert len(components)==len(target_ids)==209 and target_ids==set(subjects)
assert len(qualified)==437959 and qualified|holds.keys()==original.keys()
assert len(qualified & physical_original)==144047 and len(qualified & admin_original)==293912
classes=lambda keys:dict(sorted(Counter(original[k] for k in keys).items()))
assert classes(qualified)=={'inland-water':62395,'land':375564}
assert classes(holds)=={'inland-water':32,'land':71}
limits=['Constructor qualification is not actual current-owner-zero or selected-output acceptance; accepted repair credit remains zero until genuine later delivery.',
 'The complete original 438062-cell, 139042-interval, 209-subject denominator and all 103 held keys remain obligations.',
 'Complete original source/physical evidence and historic #887, #607/#609 territorial, clipping and crosswalk/remainder obligations are retained; no regional/legal approval or historical import.']
result={'kind':'complete-original-Canada-native-authority-accounting','version':1,'input_commit':a.input_commit,
 'original_cells':len(original),'original_intervals':intervals,'original_targets':209,'qualified_cells':len(qualified),'held_cells':len(holds),
 'qualified_administrative_cells':293912,'qualified_physical_region_cells':144047,'qualified_components':len(components),
 'original_physical_classes':classes(original),'qualified_physical_classes':classes(qualified),'held_physical_classes':classes(holds),
 'source_hold_reasons':dict(sorted(Counter(holds.values()).items())),'held_keys':[{'y':y,'x':x,'owner':o,'physical_class':original[(y,x,o)],'reason':reason} for (y,x,o),reason in sorted(holds.items())],
 'all_original_keys_exactly_partitioned':True,'all_original_subjects_retained':True,'batches':batches,'subject_ids':subjects,'inputs':inputs,'limits':limits}
handoff={'kind':'qualified-Canada-original-native-authority-handoff','version':1,'input_commit':a.input_commit,
 'original_cells':438062,'qualified_cells':437959,'explicit_held_cells':103,'original_intervals':139042,'subject_ids':subjects,
 'authorities':quartets,'batches':batches,'limits':limits}
for path,obj in [(a.accounting,result),(a.handoff,handoff)]:
 with Path(path).open('x')as f:json.dump(obj,f,indent=2,ensure_ascii=False);f.write('\n')
print(json.dumps({k:result[k] for k in ['original_cells','original_intervals','original_targets','qualified_cells','held_cells','qualified_physical_classes','held_physical_classes','all_original_keys_exactly_partitioned']}))

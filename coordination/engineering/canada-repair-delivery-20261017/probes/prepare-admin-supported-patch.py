#!/usr/bin/env python3
"""Use exact stock diagnostic partitions, preserving every original source hold."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--input-commit',required=True);p.add_argument('--patch',required=True);p.add_argument('--accounting',required=True);a=p.parse_args();P='coordination/engineering/canada-repair-delivery-20261017/';pins=[]
assert len(a.input_commit)==40 and all(c in '0123456789abcdef' for c in a.input_commit)
def read(name):
 path=P+name;raw=subprocess.check_output(['git','-c','protocol.allow=never','-C',a.repo,'show',a.input_commit+':'+path]);pins.append({'commit':a.input_commit,'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()});return json.loads(raw)
def keys(rows):
 out=set();n=0
 for r in rows:
  for lo,hi,o in r['runs']:
   assert lo<hi
   for x in range(lo,hi):out.add((r['y'],x,o));n+=1
 assert n==len(out);return out
app=read('aafc-native-operands-001/applicability-decision.json');physical_owners={o for b in app['batches'] for o in b['owners']};expected={(r['y'],r['x'],r['owner']) for r in app['held'] if r['owner'] not in physical_owners}
d=read('admin-native-diagnostic-003/native-diagnostic.json');original=keys(read('source-stage/admin-requested-native-patch.json')['rows']);requested=keys(d['requested_rows']);supported=keys(d['supported_rows']);held=keys(d['held_rows'])
assert requested==original and len(requested)==293965
assert not supported&held and supported|held==requested
assert held==expected and len(held)==d['held_cells']==53
assert len(supported)==d['supported_cells']==293912
reasons={}
for row in d['decision_rows']:
 for lo,hi,owner,reason in row['runs']:reasons[reason]=reasons.get(reason,0)+hi-lo
body=(json.dumps({'rows':d['supported_rows']},separators=(',',':'))+'\n').encode();out=Path(a.patch)
with out.open('xb') as f:f.write(body)
result={'kind':'exact-original-administrative-native-diagnostic-accounting','requested_cells':len(original),'supported_cells':len(supported),'held_cells':len(held),'all_held_keys_exactly_equal_known_foreign_original_contacts':True,'decision_reasons':reasons,'supported_targets':len({k[2] for k in supported}),'supported_patch':{'path':P+'admin-supported-native-patch-003.json','bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()},'held_keys':[{'y':y,'x':x,'owner':o} for y,x,o in sorted(held)],'inputs':pins,'limits':['Diagnostic eligibility only; the supported patch still requires the unchanged stock native authority constructor and actual current selected-output acceptance.']}
with Path(a.accounting).open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['requested_cells','supported_cells','held_cells','decision_reasons','supported_targets']}))

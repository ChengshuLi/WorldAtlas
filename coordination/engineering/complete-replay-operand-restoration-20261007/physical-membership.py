"""CACHE-ONLY continuation proposal. Must be frozen at a new head before execution.
Original ce98 acquisition algorithms/products remain immutable. This helper owns
only full current/physical membership validation and its transparent continuation.
The cold caller must authenticate the request/spec/project/runtime before Phase,
freeze this helper separately, and run its mandatory live_guard at every boundary.
"""
import json,re
OLD='ce98a747ecab13ba05bd35b7dd3e20662bc70193'
SCOPE={'components':95173,'mismatches':1294,'ordered_queries':10419}
MEMBERSHIP='complete-current-physical-membership-v1'
JOIN='complete-original-physical-query-join-via-membership-v1'
RESERVE=48*1024*1024+2*1024*1024

def need(ok,msg):
 if not ok:raise ValueError(msg)

def unique(pins,a):
 result={}
 for p in pins:
  a.bounds(p);k=a.Phase.key(p)
  need(k not in result or result[k]==p,'Conflicting complete continuation pin')
  result[k]=p
 return list(result.values())

def exact(actual,expected,a):
 need(len(actual)==len(unique(actual,a)) and len(expected)==len(unique(expected,a)) and
      {a.Phase.key(p):p for p in actual}=={a.Phase.key(p):p for p in expected},'Whole original continuation roster drift')

def validate_spec(spec,context):
 need(spec['version']==1 and spec['scientific_execution_commit']==OLD and spec['scope']==SCOPE,'Original full scientific vintage/scope differs')
 head=context.get('execution_commit')
 need(type(head) is str and re.fullmatch('[a-f0-9]{40}',head) and head!=OLD and spec['continuation_execution_commit']==head,'Fresh actual continuation vintage required')
 need(context.get('scientific_execution_commit')==OLD and context.get('request_pin') and context.get('freeze_pin') and context.get('spec_pin'),'Explicit current request/freeze/spec custody required')
 need(context.get('current_project_pins') and all(p.get('commit')==head for p in context['current_project_pins']),'Actual separately frozen current project closure required')
 need(spec['prior_project_pins'] and all(p.get('commit')==OLD for p in spec['prior_project_pins']),'Original ce98 executed closure required')
 need(len(spec['physical'])==71 and len(product(spec['components'],'components-'))==7 and len(spec['routing'])==25,'Complete original71/7/25 stage roster required')
 for family in ('physical','routing'):
  need([s['ordinal'] for s in spec[family]]==list(range(len(spec[family]))),'Original source shard ordering differs')


def stage_pins(s):return [s['publication'],s['inventory'],*s['outputs']]

def selected_stage(s,prefix):return [s['publication'],s['inventory'],*product(s,prefix)]

def membership_inputs(spec,a):return unique([*selected_stage(spec['components'],'components-'),*[p for s in spec['physical'] for p in selected_stage(s,'physical-index-')]],a)

def join_inputs(spec,member,a):return unique([*stage_pins(member),*[p for s in spec['physical'] for p in selected_stage(s,'physical-index-')],*[p for s in spec['routing'] for p in selected_stage(s,'routing-')],*selected_stage(spec['mismatches'],'mismatch-index-')],a)

def check_original(phase,s,spec,a):
 inv=a.completed_inventory(phase,s['publication'],s['inventory'])
 exact(inv['outputs'],s['outputs'],a)
 need(inv['facts']['operation']==s['operation'],'Original predecessor operation differs')
 if 'ordinal' in s and s['operation']=='routing-containing-part':
  need(inv['facts']['part']==s['ordinal'],'Original routing part differs')
 actual={a.Phase.key(p):p for p in inv['input_descriptors']}
 need(all(actual.get(a.Phase.key(p))==p for p in spec['prior_project_pins']),'Original predecessor ce98 project closure differs')
 return inv

def product(s,prefix):return [p for p in s['outputs'] if p['path'].rsplit('/',1)[-1].startswith(prefix)]

def indexed_rows(phase,pins,a):
 for shard,pin in enumerate(pins):
  for ordinal,line in enumerate(phase.read(pin).splitlines()):
   need(bool(line),'Empty complete current component row')
   row=json.loads(line);yield row,shard,ordinal,a.sha(a.canonical(row))

def membership_rows(components,physical,count,a):
 """Pure bounded control entry; public production count is fixed95173."""
 ids=set(physical);seen=set()
 for row,shard,ordinal,digest in components:
  identity=row['id'];need(type(identity) is str and re.fullmatch('physical-component:[a-f0-9]{64}',identity) and identity not in seen and identity in ids,'Duplicate/foreign current membership')
  need(type(shard) is int and shard>=0 and type(ordinal) is int and ordinal>=0 and re.fullmatch('[a-f0-9]{64}',digest),'Invalid complete inverse row metadata')
  seen.add(identity)
  item={'id':identity,'shard':shard,'ordinal':ordinal,'row_sha256':digest}
  need(len(a.canonical(item))<=256,'Whole inverse membership row exceeds prospective bound')
  yield item
 need(len(ids)==count and seen==ids,'Missing complete current/physical membership')

def membership(phase,*,spec,context,acquisition,live_guard):
 a=acquisition;validate_spec(spec,context);live_guard()
 need(phase.reserve>=RESERVE,'Whole ledger plus inventory reserve required')
 check_original(phase,spec['components'],spec,a)
 for s in spec['physical']:check_original(phase,s,spec,a)
 physical=a.exact_ids(a.raw_rows(phase,[p for s in spec['physical'] for p in product(s,'physical-index-')]),'id')
 pins=product(spec['components'],'components-');need(len(pins)==7,'Complete geometry-bearing current product roster differs')
 phase.rows('current-physical-membership',membership_rows(indexed_rows(phase,pins,a),physical,95173,a))
 live_guard()
 return phase.finish({'operation':MEMBERSHIP,'scope':SCOPE,'scientific_execution_commit':OLD,
  'continuation_execution_commit':context['execution_commit'],'spec_pin':context['spec_pin'],
  'component_products':pins,'maximum_row_bytes':256,'complete':95173})

def read_membership(phase,member,spec,context,a):
 inv=a.completed_inventory(phase,member['publication'],member['inventory']);exact(inv['outputs'],member['outputs'],a)
 facts=inv['facts'];need(facts.get('operation')==MEMBERSHIP and facts.get('scope')==SCOPE and facts.get('scientific_execution_commit')==OLD and facts.get('continuation_execution_commit')==context['execution_commit'] and facts.get('spec_pin')==context['spec_pin'] and facts.get('maximum_row_bytes')==256 and facts.get('complete')==95173,'Membership actual vintage/scope/binding differs')
 originals=membership_inputs(spec,a);inputs={a.Phase.key(p):p for p in inv['input_descriptors']}
 need(all(inputs.get(a.Phase.key(p))==p for p in [*originals,*context['current_project_pins']]),'Missing whole original/current membership inverse custody')
 exact(facts['component_products'],product(spec['components'],'components-'),a)
 return a.exact_ids(a.raw_rows(phase,product(member,'current-physical-membership-')),'id')

def reconcile_rows(physical,members,routing,mismatches,count,mismatch_count,query_count):
 need(len(physical)==len(members)==len(routing)==count and set(physical)==set(members)==set(routing) and len(mismatches)==mismatch_count and set(mismatches)<=set(physical),'Missing/foreign full continuation roster')
 # Complete inverse ordinal coverage prevents coherent duplicate/foreign positions.
 seen=set();previous={};queries=0
 for identity,item in members.items():
  need(set(item)=={'id','shard','ordinal','row_sha256'} and item['id']==identity and type(item['shard']) is int and 0<=item['shard']<7 and type(item['ordinal']) is int and item['ordinal']>=0 and re.fullmatch('[a-f0-9]{64}',item['row_sha256']),'Membership inverse metadata differs')
  pos=(item['shard'],item['ordinal']);need(pos not in seen,'Duplicate inverse component shard/ordinal');seen.add(pos)
  previous.setdefault(item['shard'],[]).append(item['ordinal'])
 need(set(previous)==set(range(7)),'Missing complete inverse component shard')
 for ordinals in previous.values():need(sorted(ordinals)==list(range(len(ordinals))),'Missing/reordered inverse component row ordinal')
 for identity,item in routing.items():
  if not item['selected']:continue
  row=item['row'];support=physical[identity];path=support['original_path']
  need(path==row['whole_physical_containing_file'] and support['packed_whole_row_sha256']==row['whole_physical_row_sha256'],'Wrong whole physical containing-file/row binding')
  if identity in mismatches:
   need(mismatches[identity]['physical_containing_file']==path,'Original mismatch physical containing-file differs');queries+=support['query_count']
 need(queries==query_count,'Complete original ordered query cohort differs')
 return {'complete':count,'mismatches':mismatch_count,'ordered_queries':queries}

def reconcile(phase,*,spec,member,context,acquisition,live_guard):
 a=acquisition;validate_spec(spec,context);live_guard()
 for s in [*spec['physical'],*spec['routing'],spec['mismatches']]:check_original(phase,s,spec,a)
 physical=a.exact_ids(a.raw_rows(phase,[p for s in spec['physical'] for p in product(s,'physical-index-')]),'id')
 members=read_membership(phase,member,spec,context,a)
 routing=a.exact_ids(a.raw_rows(phase,[p for s in spec['routing'] for p in product(s,'routing-')]),'id')
 mismatches=a.exact_ids(a.raw_rows(phase,product(spec['mismatches'],'mismatch-index-')),'id')
 facts=reconcile_rows(physical,members,routing,mismatches,95173,1294,10419);live_guard()
 return phase.finish(dict(facts,operation=JOIN,scientific_execution_commit=OLD,continuation_execution_commit=context['execution_commit'],spec_pin=context['spec_pin'],membership_publication=member['publication'],membership_inventory=member['inventory']))

def authorize_query(phase,*,join,spec,context,acquisition,live_guard):
 """New cold driver must call before the unchanged original query_part callable.
 This authenticates the new helper operation, never claims old physical_join ran.
 """
 validate_spec(spec,context);live_guard();a=acquisition
 inv=a.completed_inventory(phase,join['publication'],join['inventory']);exact(inv['outputs'],join['outputs'],a);f=inv['facts']
 need(f.get('operation')==JOIN and f.get('scientific_execution_commit')==OLD and f.get('continuation_execution_commit')==context['execution_commit'] and f.get('spec_pin')==context['spec_pin'] and all(f.get(k)==v for k,v in SCOPE.items() if k!='components') and f.get('complete')==95173,'Unqualified/stale continuation query admission')
 inputs={a.Phase.key(p):p for p in inv['input_descriptors']}
 need(context.get('membership_stage') and all(inputs.get(a.Phase.key(p))==p for p in [*join_inputs(spec,context['membership_stage'],a),*context['current_project_pins']]),'Missing complete original/current parent custody')
 return inv

def inverse_rows(rows,original,shard,a):
 wanted={r['ordinal']:r for r in rows if r['shard']==shard}
 need(len(wanted)==sum(r['shard']==shard for r in rows),'Duplicate complete inverse ordinal')
 seen=set()
 for ordinal,row in enumerate(original):
  need(ordinal in wanted and wanted[ordinal]['id']==row['id'] and wanted[ordinal]['row_sha256']==a.sha(a.canonical(row)),'Drifted whole original component inverse row/shard')
  seen.add(ordinal)
 need(seen==set(wanted),'Missing/foreign whole original component inverse row')
 return len(seen)

def verify_inverse_shard(phase,*,spec,member,shard,context,acquisition,live_guard):
 a=acquisition;validate_spec(spec,context);live_guard()
 need(type(shard) is int and 0<=shard<7,'Whole original inverse shard selection required')
 members=read_membership(phase,member,spec,context,a)
 pin=product(spec['components'],'components-')[shard]
 count=inverse_rows(list(members.values()),a.raw_rows(phase,[pin]),shard,a);live_guard()
 return phase.finish({'operation':'whole-original-component-membership-inverse-v1','scientific_execution_commit':OLD,'continuation_execution_commit':context['execution_commit'],'spec_pin':context['spec_pin'],'shard':shard,'whole_original_component_product':pin,'rows':count})

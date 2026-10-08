"""Cache-only dispatch body for the separately frozen guarded cold custody entry.
Not a standalone executable or permission to edit/replay old ce98 jobs.
The cold entry must validate request+spec hashes and HEAD, derive every input
before constructing original Phase, consume its exact code/runtime/request pins,
and guard original and new helper code objects at each finish callback.
"""
def dependencies(operation,spec,arguments,a,helper):
 if operation=='physical-membership':return helper.membership_inputs(spec,a)
 if operation=='physical-membership-join':return helper.join_inputs(spec,arguments['member'],a)
 if operation=='physical-membership-inverse':
  shard=arguments['shard'];a.require(type(shard) is int and 0<=shard<7,'Exact inverse shard required')
  return helper.unique([*helper.stage_pins(arguments['member']),helper.product(spec['components'],'components-')[shard]],a)
 if operation=='query-part-continuation':
  p=arguments['physical'];j=arguments['join']
  return helper.unique([p['publication'],p['inventory'],*helper.product(p,'whole-original-physical.'),*helper.selected_stage(spec['mismatches'],'mismatch-index-'),*helper.stage_pins(j)],a)
 if operation=='query-join-continuation':
  return helper.unique([*[pin for s in arguments['queries'] for pin in helper.selected_stage(s,'native-query-index-')],*[pin for s in spec['physical'] for pin in helper.selected_stage(s,'physical-index-')],*helper.selected_stage(spec['mismatches'],'mismatch-index-'),*helper.stage_pins(arguments['join'])],a)
 raise ValueError('Unsupported exact continuation operation')

def execute(operation,phase,*,spec,arguments,context,acquisition,helper,original_immutable,live_guard):
 a=acquisition;helper.validate_spec(spec,context);live_guard()
 if operation=='physical-membership':return helper.membership(phase,spec=spec,context=context,acquisition=a,live_guard=live_guard)
 if operation=='physical-membership-join':return helper.reconcile(phase,spec=spec,member=arguments['member'],context=context,acquisition=a,live_guard=live_guard)
 if operation=='physical-membership-inverse':return helper.verify_inverse_shard(phase,spec=spec,member=arguments['member'],shard=arguments['shard'],context=context,acquisition=a,live_guard=live_guard)
 if operation=='query-part-continuation':
  physical=arguments['physical'];helper.need(physical in spec['physical'],'Foreign original physical query shard')
  helper.check_original(phase,physical,spec,a);helper.check_original(phase,spec['mismatches'],spec,a)
  helper.authorize_query(phase,join=arguments['join'],spec=spec,context=context,acquisition=a,live_guard=live_guard)
  pins=helper.product(physical,'whole-original-physical.');helper.need(len(pins)==1,'Whole original physical query product missing')
  # This is the SAME unchanged original ce98 callable, authenticated by live_guard.
  # Guarded phase.finish appends CURRENT execution provenance to its true original
  # operation facts; it must never relabel this execution as ce98.
  return a.query_part(phase,pins[0],helper.product(spec['mismatches'],'mismatch-index-'),original_immutable.canonical_json)
 if operation=='query-join-continuation':
  helper.authorize_query(phase,join=arguments['join'],spec=spec,context=context,acquisition=a,live_guard=live_guard)
  qs=arguments['queries'];helper.need(len(qs)==71 and [s['ordinal'] for s in qs]==list(range(71)),'Complete original71 query stages required')
  for s in [*spec['physical'],spec['mismatches']]:helper.check_original(phase,s,spec,a)
  for s in qs:
   inv=a.completed_inventory(phase,s['publication'],s['inventory']);helper.exact(inv['outputs'],s['outputs'],a)
   # Exact child requests/freezes come from the parent's root-issued request,
   # captured before child launch, never from child producer facts.
   expected=helper.unique([*context['bootstrap_project_pins'],s['request_pin'],s['freeze_pin'],
      *helper.selected_stage(spec['physical'][s['ordinal']],'whole-original-physical.'),
      *helper.selected_stage(spec['mismatches'],'mismatch-index-'),
      *helper.stage_pins(arguments['join'])],a)
   helper.exact(inv['input_descriptors'],expected,a)
   helper.need(inv['runtime_bytes']==context['runtime_bytes'],'Actual query installed-runtime charge differs')
   f=inv['facts'];helper.need(f['operation']=='actual-original-native-query-containing-file' and f['scientific_execution_commit']==helper.OLD and f['execution_commit']==context['execution_commit'] and f['spec_pin']==context['spec_pin'],'Foreign query execution/helper vintage')
   helper.need(f['request_pin']==s['request_pin'] and f['freeze_pin']==s['freeze_pin'],'Query request/freeze differs from root-issued launch')
   helper.need(f['whole_restored_physical_input']==helper.product(spec['physical'][s['ordinal']],'whole-original-physical.')[0],'Original query shard binding differs')
  return a.query_join(phase,[pin for s in qs for pin in helper.product(s,'native-query-index-')],helper.product(spec['mismatches'],'mismatch-index-'),[pin for s in spec['physical'] for pin in helper.product(s,'physical-index-')])
 raise ValueError('Unsupported exact continuation execution')

"""Validate selected Neon List 1 policy, category bindings and entry links.

Callers must authenticate each passed snapshot/report/file hash independently.
This module does not resolve geographic features or ingest reference labels.
"""
import re
HEX=re.compile(r'^[0-9a-f]{64}$')
def need(v,m):
 if not v:raise ValueError(m)
def unique(items,key,label):
 need(isinstance(items,list) and len(items)<=100000,'invalid '+label+' list');out={}
 for x in items:
  need(isinstance(x,dict) and isinstance(x.get(key),str) and x[key] and x[key] not in out,'duplicate or invalid '+label);out[x[key]]=x
 return out
def names(snapshot):
 entities=snapshot.get('entities');bindings=snapshot.get('category_bindings');need(isinstance(entities,list) and isinstance(bindings,list),'missing categories');byid={}
 for e in entities:
  need(isinstance(e,dict) and type(e.get('id')) is int and e['id'] not in byid,'invalid category entity');byid[e['id']]=e
 result={}
 for b in bindings:
  if b.get('physical_class')!='land':continue
  code=b.get('code');e=byid.get(b.get('entity_id'));need(type(code) is int and 17<=code<=22 and str(code) not in result and isinstance(e,dict) and e.get('level')=='continent' and isinstance(e.get('name'),str) and e['name'],'invalid land category binding');result[str(code)]=e['name']
 need(set(result)==set(map(str,range(17,23))) and len(set(result.values()))==6,'incomplete land categories');return result

def compile_policy(snapshot,baseline_snapshot,baseline_report,pins,supported_methods):
 need(isinstance(snapshot,dict) and snapshot.get('schema')=='worldatlas-geography-decision-draft-evidence-v1' and snapshot.get('source')=='neon-export' and isinstance(baseline_snapshot,dict) and baseline_snapshot.get('source')=='neon-export','authenticated Neon snapshots required')
 rev=snapshot.get('decision_revision',{});entity=snapshot.get('entity_revision',{});base_rev=baseline_snapshot.get('decision_revision',{});base_ent=baseline_snapshot.get('entity_revision',{})
 need(rev.get('status')=='draft' and entity.get('status')=='draft' and rev.get('entity_revision')==entity.get('id') and base_rev.get('status')=='draft' and base_ent.get('status')=='draft' and base_rev.get('entity_revision')==base_ent.get('id'),'invalid decision/entity revisions')
 need(isinstance(pins,dict) and set(pins)=={'baseline_report_sha256','baseline_rows_sha256','baseline_runs_sha256','baseline_decision_snapshot_sha256','physical_rows_sha256','physical_runs_sha256','component_rows_sha256','component_runs_sha256'} and all(isinstance(x,str) and HEX.fullmatch(x) for x in pins.values()),'invalid baseline pins')
 need(isinstance(baseline_report,dict) and baseline_report.get('schema')=='stage2-source-geodesic-report-v1' and baseline_report.get('status')=='stage2-research-awaiting-monitor' and baseline_report.get('decision_revision')==base_rev.get('id') and baseline_report.get('entity_revision')==base_ent.get('id') and baseline_report.get('decision_snapshot_sha256')==pins['baseline_decision_snapshot_sha256'] and baseline_report.get('output_rows_sha256')==pins['baseline_rows_sha256'] and baseline_report.get('output_runs_sha256')==pins['baseline_runs_sha256'],'baseline report identity mismatch')
 need(all(baseline_report.get('inputs_sha256',{}).get(k)==pins[k+'_sha256'] for k in ('physical_rows','physical_runs','component_rows','component_runs')),'baseline physical/component pins mismatch')
 n=names(snapshot);need(n==names(baseline_snapshot)==baseline_report.get('categories'),'baseline/override category mismatch')
 policy=snapshot.get('list1_policy');need(isinstance(policy,dict) and policy.get('decision_revision')==rev.get('id') and policy.get('baseline_revision')==base_rev.get('id') and policy.get('execution_status')=='selected_for_research' and policy.get('conflict_policy')=='error_on_different_target' and policy.get('unclaimed_policy')=='preserve_baseline' and policy.get('physical_water_policy')=='preserve_unassigned' and all(policy.get(k)==v for k,v in pins.items()),'invalid selected List 1 policy')
 entries=unique(snapshot.get('list1_entries'),'entry_id','entry');affiliations=unique(snapshot.get('affiliations'),'affiliation_id','affiliation')
 eids=policy.get('entry_ids');aids=policy.get('affiliation_ids');need(isinstance(eids,list) and isinstance(aids,list) and eids and aids and len(eids)==len(set(eids)) and len(aids)==len(set(aids)) and set(eids)==set(entries),'invalid selected entry/affiliation sets')
 need(isinstance(supported_methods,(set,frozenset)) and supported_methods and all(isinstance(x,str) and x for x in supported_methods),'missing supported resolver registry')
 selected={aid for aid,a in affiliations.items() if a.get('scope')=='land' and isinstance(a.get('evidence'),dict) and a['evidence'].get('execution_status')=='selected_for_research'}
 need(set(aids)==selected,'selected affiliations differ from policy');links={aid:set() for aid in aids};entry_trace={}
 for eid in sorted(eids):
  e=entries[eid];l=e.get('affiliation_ids');old=e.get('old_list1_refs')
  need(e.get('decision_revision')==rev['id'] and e.get('execution_status')=='selected_for_research' and isinstance(e.get('title'),str) and e['title'].strip() and isinstance(e.get('reason'),str) and e['reason'].strip() and isinstance(old,list) and isinstance(l,list) and l and len(l)==len(set(l)) and set(l)<=set(aids),'invalid or orphan List 1 entry')
  for aid in l:links[aid].add(eid)
  entry_trace[eid]={'title':e['title'],'reason':e['reason'],'old_list1_refs':old,'affiliation_ids':sorted(l)}
 need(all(links.values()),'unlinked selected affiliation')
 land_codes={b['entity_id']:b['code'] for b in snapshot['category_bindings'] if b.get('physical_class')=='land'}
 for aid in aids:
  a=affiliations[aid];need(a.get('decision_revision')==rev['id'] and a.get('relationship')=='affiliation' and a.get('method') in supported_methods and type(a.get('entity_id')) is int and a['entity_id'] in land_codes,'unsupported, stale or non-continent selected affiliation')
 return {'revision':rev['id'],'entity_revision':entity['id'],'baseline_revision':base_rev['id'],'categories':n,'entry_ids':sorted(eids),'affiliation_ids':sorted(aids),'entries':entry_trace,'affiliation_entry_links':{k:sorted(v) for k,v in sorted(links.items())},'policy':policy}

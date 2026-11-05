#!/usr/bin/env python3
"""Evaluate selected source-decisions against immutable diagnostics, never select from them."""
import hashlib,importlib.util,json,os,shutil,sqlite3,sys
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np

def need(v,msg):
 if not v:raise ValueError(msg)
def guard():
 if shutil.disk_usage('.').free<2*1024**3:raise OSError('disk floor reached')

def sha(path,guard=guard):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while True:
   guard();b=f.read(1048576)
   if not b:break
   h.update(b)
 return h.hexdigest()
def row_grid(rows,runs,y,w,allowed):
 a,b=map(int,rows[y:y+2]);need(0<=a<b<=len(runs),'invalid row offsets');x=runs[a:b];ends=x[:,0];values=x[:,1]
 need(int(ends[0])>0 and int(ends[-1])==w and np.all(ends[1:]>ends[:-1]) and np.all(np.isin(values,list(allowed))),'invalid row coverage or category')
 return ends,values

def evaluate_row(y,w,base,post,reference,clusters,changes,land,water,claims,links,coverage,counts):
 be,bv=base;pe,pv=post;re,rv=reference
 pieces=[be,pe,re,np.array([x for c in clusters for x in (c[0],c[1])],dtype=np.uint32),np.array([x for t in changes for x in (t['start'],t['end'])],dtype=np.uint32)]
 ends=np.unique(np.concatenate(pieces));ends=ends[ends>0];starts=np.r_[np.uint32(0),ends[:-1]]
 b=bv[np.searchsorted(be,starts,side='right')];p=pv[np.searchsorted(pe,starts,side='right')];r=rv[np.searchsorted(re,starts,side='right')];length=(ends-starts).astype(np.int64)
 need(np.all((b==0)==(p==0)),'post-build changed physical land/water')
 shared=np.isin(b,list(land))&np.isin(r,list(land));initial=shared&(b!=r);after=shared&(p!=r);changed=b!=p
 counts['initial_mismatch_cells']+=int(length[initial].sum());counts['post_mismatch_cells']+=int(length[after].sum());counts['extra_changed_shared_land_cells']+=int(length[shared&~initial&changed].sum());counts['changed_outside_shared_land_cells']+=int(length[~shared&changed].sum());counts['changed_cells']+=int(length[changed].sum())
 counts['candidate_land_reference_water']+=int(length[np.isin(b,list(land))&np.isin(r,list(water))].sum());counts['candidate_water_reference_land']+=int(length[(b==0)&np.isin(r,list(land))].sum())
 def section(a,z):
  need(type(a) is int and type(z) is int and 0<=a<z<=w,'invalid span');i=int(np.searchsorted(starts,a));j=int(np.searchsorted(starts,z));need(i<j and int(starts[i])==a and int(ends[j-1])==z,'span boundaries missing');return slice(i,j)
 trace_covered=np.zeros(len(starts),dtype=bool);trace_by_interval=[]
 for t in changes:
  need(set(t)=={'row','start','end','from_code','to_code','affiliation_ids','entry_ids'} and t['row']==y,'invalid trace shape');sec=section(t['start'],t['end']);aids=t['affiliation_ids'];eids=t['entry_ids']
  need(isinstance(aids,list) and aids and aids==sorted(set(aids)) and isinstance(eids,list) and eids and eids==sorted(set(eids)),'invalid trace IDs')
  need(all(x in claims and claims[x]==t['to_code'] for x in aids) and eids==sorted({v for x in aids for v in links[x]}),'trace IDs do not match selected decision/entry bindings')
  need(not np.any(trace_covered[sec]) and np.all(b[sec]==t['from_code']) and np.all(p[sec]==t['to_code']) and np.all(changed[sec]),'overlap or trace/output discrepancy');trace_covered[sec]=True;trace_by_interval.append((t['start'],t['end'],aids,eids))
 need(np.array_equal(trace_covered,changed),'post-build changes not exactly covered by trace')
 cluster_covered=np.zeros(len(starts),dtype=bool)
 trace_cursor=0
 for a,z,ref,orig,root in clusters:
  sec=section(a,z);need(not np.any(cluster_covered[sec]) and np.all(initial[sec]) and np.all(r[sec]==ref) and np.all(b[sec]==orig),'initial cluster/span mismatch');cluster_covered[sec]=True
  target=p[sec]==r[sec];total=int(length[sec].sum());fixed=int(length[sec][target].sum());cov=coverage[root];cov['initial']+=total;cov['explained']+=fixed;cov['unresolved']+=total-fixed
  while trace_cursor<len(trace_by_interval) and trace_by_interval[trace_cursor][1]<=a:trace_cursor+=1
  k=trace_cursor
  while k<len(trace_by_interval) and trace_by_interval[k][0]<z:
   lo,hi,aids,eids=trace_by_interval[k];s=section(max(lo,a),min(hi,z));n=int(length[s][p[s]==r[s]].sum())
   if n:cov['affiliation_ids'].update(aids);cov['entry_ids'].update(eids)
   k+=1
 need(np.array_equal(cluster_covered,initial),'initial mismatch is not exactly covered by clusters')

def attach_selected_evidence(module,snapshot,compiled,files):
 evidence=module.resolve(snapshot,compiled,files,guard)
 need(isinstance(evidence,dict) and set(evidence)==set(compiled['entries']) and all(isinstance(v,list) for v in evidence.values()),'evidence entries do not match compiled policy')
 for eid,items in evidence.items():compiled['entries'][eid]['geographic_membership_evidence']=items
 return evidence

def collect_claims(report, snapshot):
 links=report['policy']['affiliation_entry_links'];rows=report['point_resolution']['claims']+report['polygon_resolution']['claims']+report['bering_resolution']['claims'];aff={x['affiliation_id']:x for x in snapshot['affiliations']};bindings={x['entity_id']:x['code'] for x in snapshot['category_bindings'] if x.get('physical_class')=='land'};claims={}
 for x in rows:
  aid=x.get('affiliation_id');need(aid in aff and aid not in claims and x.get('method')==aff[aid].get('method') and x.get('entity_id')==aff[aid].get('entity_id') and type(x.get('entity_code')) is int and x['entity_code']==bindings.get(x['entity_id']),'claim target/identity mismatch');claims[aid]=x['entity_code']
 need(set(links)==set(claims) and all(isinstance(v,list) and v and v==sorted(set(v)) for v in links.values()),'selected decision linkage mismatch');return claims
def require_policy_match(compiled, expected):
 need(compiled==expected,'selected Neon policy/evidence does not match report')

def validate_polygon_custody(snapshot,report,cfg,module):
 ids={x['affiliation_id'] for x in snapshot['affiliations'] if x.get('affiliation_id') in report['policy']['affiliation_entry_links'] and x.get('method') in ('component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1')}
 policy=module.adapt(snapshot,ids);need(policy['source_pins']==report.get('polygon_source_custody'),'polygon custody trace mismatch')
 files=cfg['polygon_source_files'];sources={(x['source_id'],x['version']):x for x in files};need(len(sources)==len(files) and set(sources)=={(x['source_id'],x['version']) for x in policy['source_pins']},'polygon source set mismatch')
 for x in policy['source_pins']:
  f=sources[(x['source_id'],x['version'])];need(f['sha256']==x['sha256'] and f['size_bytes']==x['size_bytes'] and Path(f['path']).stat().st_size==f['size_bytes'] and sha(f['path'])==f['sha256'],'polygon source bytes mismatch')
 return policy['source_pins']

def run():
 base=Path('actual-stage2-v7-input-20261104/config.json');compare=Path('actual-stage2-v7-clusters-20261104');post=Path('combined-draft24-reduced-floor-output-20261105');monitor=Path('combined-draft24-reduced-floor-monitor-20261105/watchdog.json');output=Path('combined-draft24-reduced-floor-reconciliation-output-20261105')
 guard();expected_path=Path('combined-draft24-reduced-floor-reconcile-20261105/expected.json');expected_sha=sha(expected_path);expected=json.loads(expected_path.read_bytes());need(set(expected)=={'schema','stage3_report_sha256','stage3_monitor_sha256','stage3_watchdog_sha256'} and expected['schema']=='stage3-reconciliation-observed-output-pins-v1','invalid expected pins');code_sha=sha(Path(__file__));need(not output.exists(),'output exists; inspect before retry');need(sha(base)=='623dfd7655e1cbe354854a909019afcae702a57b2f4bee116f8b17e316266450','comparison config mismatch');need(sha(post/'report.json')==expected['stage3_report_sha256'] and sha(monitor)==expected['stage3_monitor_sha256'],'stage3 report or monitor identity mismatch');cfg=json.loads(base.read_bytes());cr=json.loads((compare/'report.json').read_bytes());report=json.loads((post/'report.json').read_bytes());mon=json.loads(monitor.read_bytes())
 need(sha(compare/'report.json')=='93726691f683daf73f8618635aa792fd629da4dc93257ab7e4e8456485d4adc3' and sha(compare/'clusters.sqlite')==cr['database_sha256'] and sha(base)==cr['config_sha256'],'comparison identity mismatch')
 need(report.get('schema')=='stage3-selected-mixed-land-report-v1' and report.get('status')=='research-awaiting-monitor' and report.get('publishable') is False,'incomplete stage3 report');need(mon.get('schema')=='sampled-process-group-watchdog-v1' and mon.get('status')=='complete' and mon.get('watchdog_sha256')==expected['stage3_watchdog_sha256'] and mon.get('guardian_sha256')=='b0a1c6cd72d351ac1e1b3e513e738c0bb718e4ba1c64bd627727c41d4870ce72' and mon.get('memory_floor_kib')==1048576 and mon.get('minimum_available_kib',0)>=1048576 and 0<mon.get('peak_group_rss_kib',0)<=mon.get('group_rss_limit_kib',0)==716800 and mon.get('samples',0)>0 and 0<mon.get('sample_interval_seconds',1)<=.1,'stage3 monitor incomplete');need(report.get('request_sha256')=='d0b01fc0ccc9708dc8dcd65c86693ca27cd58e7f2e366524900f36daba5504ac' and report.get('decision_snapshot_sha256')=='04139b6f39d092b825f11092b23f963483079b75a8be2aab980f00b35506b794','stage3 request/snapshot mismatch');need(sha('combined-draft24-reduced-floor-input-20261105/config.json')==report['request_sha256'],'stage3 config mismatch');need(sha(compare/'comparison-monitor.json')=='6ed9528a635175e27bda9d1e454edd24d94337c02256dbe5fa594290c0c65c40','comparison monitor mismatch')
 stage3cfg=json.loads(Path('combined-draft24-reduced-floor-input-20261105/config.json').read_bytes());request_pin=stage3cfg['point_request'];need(sha(request_pin['path'])==request_pin['sha256'],'point request mismatch');request=json.loads(Path(request_pin['path']).read_bytes());need(sha(request['snapshot']['path'])==request['snapshot']['sha256']==report['decision_snapshot_sha256'],'selected Neon snapshot mismatch');snapshot=json.loads(Path(request['snapshot']['path']).read_bytes());baseline_snapshot=stage3cfg['stage2']['snapshot'];baseline_report=stage3cfg['stage2']['report'];need(sha(baseline_snapshot['path'])==baseline_snapshot['sha256'] and sha(baseline_report['path'])==baseline_report['sha256'],'baseline provenance mismatch');contract=Path('stage3-mixed-leeward-full-20261105/decision_contract.py');need(sha(contract)==stage3cfg['code']['contract']=='c01744cc863aa5210835448ba0667391d75346019662dee52117fad3cb1b30f8','selected decision validator mismatch');spec=importlib.util.spec_from_file_location('selected_decision_contract',contract);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);compiled=module.compile_policy(snapshot,json.loads(Path(baseline_snapshot['path']).read_bytes()),json.loads(Path(baseline_report['path']).read_bytes()),stage3cfg['policy_pins'],{'source_point_component_v1','source_point_named_region_component_v1','raw_json_city_named_region_component_v1','osm_api_node_named_region_component_v1','osm_api_island_node_group_component_v1','component_intersection_v1','osm_relation_component_intersection_v1','component_containment_v1','osm_archipelago_component_intersection_v1','osm_archipelago_component_containment_v1','osm_archipelago_anchored_rings_intersection_v1','label_contained_ecoregion_contact_v1'});evidence_path=Path('stage3-mixed-leeward-full-20261105/entry_evidence.py');need(sha(evidence_path)==stage3cfg['code']['entry_evidence']=='5732954de3b23586f67a0469dc2c43e7966a1c4e8d1bec6a018ecc0134d50f6c','evidence validator mismatch');espec=importlib.util.spec_from_file_location('entry_evidence_validation',evidence_path);emodule=importlib.util.module_from_spec(espec);espec.loader.exec_module(emodule);evidence=attach_selected_evidence(emodule,snapshot,compiled,stage3cfg['evidence_source_files'])
 require_policy_match(compiled,report['policy'])
 custody_code=Path('stage3-mixed-leeward-full-20261105/polygon_policy.py');need(sha(custody_code)==stage3cfg['code']['polygon_policy']=='73351482c17640e8f1f368905d3ef5db9a42aba8cf0aff4295bbaea814a89fc3','polygon policy code mismatch');cspec=importlib.util.spec_from_file_location('selected_polygon_custody',custody_code);cmodule=importlib.util.module_from_spec(cspec);cspec.loader.exec_module(cmodule);custody=validate_polygon_custody(snapshot,report,stage3cfg,cmodule)
 writer=report['writer'];postfiles={n:post/n for n in ('rows.u32le','runs.u32le','changes.jsonl')}
 for n,k in (('rows.u32le','output_rows_sha256'),('runs.u32le','output_runs_sha256'),('changes.jsonl','changes_sha256')):need(sha(postfiles[n])==writer[k],'stage3 output mismatch: '+n)
 links=report['policy']['affiliation_entry_links'];claims=collect_claims(report,snapshot)
 need(sha(cfg['provenance']['reference_manifest']['path'])==cfg['provenance']['reference_manifest']['sha256']=='fa14b5612db119285cf03820fc9dff932d0d63603cdc81e70da4128f85f73105','V7 manifest mismatch');manifest=json.loads(Path(cfg['provenance']['reference_manifest']['path']).read_bytes());land={x['id'] for x in manifest['categories'] if x['physical_class']=='land'};water={x['id'] for x in manifest['categories'] if x['physical_class']=='water'};w,h=cfg['grid']['width'],cfg['grid']['height']
 paths={'baseline_rows':Path(cfg['candidate_rows']['path']),'baseline_runs':Path(cfg['candidate_runs']['path']),'reference_rows':Path(cfg['reference_rows']['path']),'reference_runs':Path(cfg['reference_runs']['path'])};
 for n,p in paths.items():need(sha(p)==cfg[{'baseline_rows':'candidate_rows','baseline_runs':'candidate_runs','reference_rows':'reference_rows','reference_runs':'reference_runs'}[n]]['sha256'],'input hash mismatch: '+n)
 def mm(name,shape):
  a=np.memmap(name,dtype='<u4',mode='r');need(a.size%shape==0,'unaligned RLE');return a.reshape(-1,shape) if shape>1 else a
 br,bu,rr,ru=mm(paths['baseline_rows'],1),mm(paths['baseline_runs'],2),mm(paths['reference_rows'],1),mm(paths['reference_runs'],2);pr,pu=mm(postfiles['rows.u32le'],1),mm(postfiles['runs.u32le'],2)
 for off,runs in ((br,bu),(rr,ru),(pr,pu)):need(len(off)==h+1 and int(off[0])==0 and int(off[-1])==len(runs) and np.all(off[1:]>=off[:-1]),'invalid RLE offsets')
 source=sqlite3.connect((compare/'clusters.sqlite').resolve().as_uri()+'?mode=ro',uri=True);meta={r:(cid,cells) for r,cid,cells in source.execute('select root,cluster_id,cells from clusters')};coverage=defaultdict(lambda:{'initial':0,'explained':0,'unresolved':0,'affiliation_ids':set(),'entry_ids':set()});counts=Counter();last_trace=(-1,-1);trace_file=postfiles['changes.jsonl'].open();pending=trace_file.readline();prev_component_run=0
 for y in range(h):
  if y%1000==0:guard()
  changes=[]
  while pending:
   t=json.loads(pending);need(type(t.get('row')) is int and t['row']>=y,'trace order error')
   if t['row']!=y:break
   key=(y,t['start']);need(key>last_trace,'trace ordering error');last_trace=key;changes.append(t);pending=trace_file.readline()
  cs=[tuple(map(int,x)) for x in source.execute('select start,end,reference,candidate,root from resolved where row=? order by start,end',(y,))]
  evaluate_row(y,w,row_grid(br,bu,y,w,land|{0}),row_grid(pr,pu,y,w,land|{0}),row_grid(rr,ru,y,w,land|water),cs,changes,land,water,claims,links,coverage,counts)
 trace_file.close();need(not pending and set(coverage)==set(meta),'unconsumed trace or missing clusters');need(counts['initial_mismatch_cells']==cr['counts']['mismatch'] and counts['candidate_land_reference_water']==305 and counts['candidate_water_reference_land']==369,'initial totals changed')
 need(counts['changed_cells']==writer['changed_cells'],'writer changed-cell count mismatch')
 for n,p in paths.items():need(sha(p)==cfg[{'baseline_rows':'candidate_rows','baseline_runs':'candidate_runs','reference_rows':'reference_rows','reference_runs':'reference_runs'}[n]]['sha256'],'input changed')
 for n,k in (('rows.u32le','output_rows_sha256'),('runs.u32le','output_runs_sha256'),('changes.jsonl','changes_sha256')):need(sha(postfiles[n])==writer[k],'post changed')
 need(sha(custody_code)==stage3cfg['code']['polygon_policy'] and validate_polygon_custody(snapshot,report,stage3cfg,cmodule)==custody,'polygon custody changed')
 need(sha(compare/'report.json')=='93726691f683daf73f8618635aa792fd629da4dc93257ab7e4e8456485d4adc3' and sha(compare/'clusters.sqlite')==cr['database_sha256'] and sha(base)==cr['config_sha256'] and sha(compare/'comparison-monitor.json')=='6ed9528a635175e27bda9d1e454edd24d94337c02256dbe5fa594290c0c65c40','comparison inputs changed during reconciliation');need(sha(post/'report.json')==expected['stage3_report_sha256'] and sha(monitor)==expected['stage3_monitor_sha256'] and sha('combined-draft24-reduced-floor-input-20261105/config.json')==report['request_sha256'] and sha(request['snapshot']['path'])==report['decision_snapshot_sha256'] and sha(request_pin['path'])==request_pin['sha256'] and sha(contract)==stage3cfg['code']['contract'] and sha(evidence_path)==stage3cfg['code']['entry_evidence'] and emodule.resolve(snapshot,compiled,stage3cfg['evidence_source_files'],guard)==evidence and sha(expected_path)==expected_sha and sha(Path(__file__))==code_sha,'stage3 inputs or code changed during reconciliation')
 output.mkdir();fd=os.open(output.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd);f=output/'clusters.jsonl'
 with f.open('x') as out:
  for root,(cid,cells) in sorted(meta.items(),key=lambda x:x[1][0]):
   c=coverage[root];need(c['initial']==cells and c['explained']+c['unresolved']==cells,'cluster count failure');out.write(json.dumps({'cluster_id':cid,'cells':cells,'explained_cells':c['explained'],'unresolved_cells':c['unresolved'],'affiliation_ids':sorted(c['affiliation_ids']),'entry_ids':sorted(c['entry_ids'])},sort_keys=True)+'\n')
  out.flush();os.fsync(out.fileno())
 counts['explained_cells']=sum(c['explained'] for c in coverage.values());counts['unresolved_cells']=sum(c['unresolved'] for c in coverage.values());need(counts['post_mismatch_cells']==counts['unresolved_cells']+counts['extra_changed_shared_land_cells'],'post mismatch accounting failure')
 result={'schema':'stage3-trace-reconciliation-v1','status':'diagnostic-evaluation-only','comparison_report_sha256':sha(compare/'report.json'),'stage3_report_sha256':sha(post/'report.json'),'stage3_monitor_sha256':sha(monitor),'changes_sha256':writer['changes_sha256'],'counts':dict(counts),'clusters':len(meta),'cluster_status_sha256':sha(f),'code_sha256':code_sha,'expected_pins_sha256':expected_sha,'limitations':['The trace and source decisions must be independently authenticated; numerical agreement does not establish geographic correctness. Geographic evidence sections and interpretations are selected assertions, not machine-verified.','Different selected targets are rejected by the writer; hypothetical conflicts were not measured.','The generic stage-3 monitor does not cryptographically bind the command it observed; its report and exact output pins were separately verified. Each unobservable process may delay full-group observation by up to 0.25 seconds; delays can accumulate.','Physical-mask differences are excluded from shared-land mismatch totals.']}
 pending,final=output/'report.pending',output/'report.json'
 with pending.open('x') as out:json.dump(result,out,sort_keys=True,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
 linked=False
 try:
  os.link(pending,final);linked=True;os.unlink(pending);fd=os.open(output,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 except OSError as exc:
  if linked:raise OSError('completion marker may exist but durability is uncertain; inspect before retry') from exc
  raise
 print(json.dumps(result,sort_keys=True))
if __name__=='__main__':
 try:run()
 except Exception as exc:print('error: '+str(exc),file=sys.stderr);raise SystemExit(1)

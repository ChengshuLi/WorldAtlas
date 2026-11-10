"""Experimental in-memory bridge from a fresh regional run to mixed writer claims.

This helper does not authenticate Neon, source files, or same-run freshness.
The caller must rerun the rule against the current component generation and
must not pass saved comparison or preview data as a selector.
"""
import copy,hashlib,json,math,re

BASES={'whole_component_line_side','source_anchored_nearest_main_island','inferred_source_extent_group_convention'}
RULE='lydekker-whole-island-regional-v1'
LINE='lydekker-anu-figure81-regional-boo-east-v2'
LINE_SHA='87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655'

def need(ok,msg):
    if not ok: raise ValueError(msg)

def merge_live_claims(policy,compiled,selected,regional,*,snapshot_sha256,component_sha256,policy_canonical_sha256,pending_roots,protected_roots):
    """Return writer-shaped claims and separate provenance; never write a grid.

    The caller must authenticate policy, snapshot, source resolver reports,
    physical lineage, runtime, same-run freshness and current pending set.
    Known pending roots are withheld from new claims. The mixed writer retains
    the baseline code where no claim applies; withholding does not mark a root
    unassigned. Every region-claim channel must also use the returned filter.
    This is research wiring, not automatic production activation.
    """
    need(isinstance(policy,dict) and isinstance(compiled,dict) and isinstance(regional,dict),'invalid policy or regional input')
    need(isinstance(policy_canonical_sha256,str) and re.fullmatch(r'[0-9a-f]{64}',policy_canonical_sha256) is not None and
         hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()==policy_canonical_sha256,'policy definition pin mismatch')
    need(isinstance(policy,dict) and policy.get('rule_set_id')==RULE and policy.get('status')=='selected_for_research','regional rule not selected for research')
    need(policy.get('decision_revision')==compiled.get('revision'),'decision revision mismatch')
    need(policy.get('line')=={'line_id':LINE,'geometry_sha256':LINE_SHA} and regional.get('line_id')==LINE and regional.get('geometry_sha256')==LINE_SHA,'line pin mismatch')
    need(isinstance(component_sha256,dict) and set(component_sha256)=={'rows','runs'} and regional.get('component_input_sha256')==component_sha256 and
         policy['evidence'].get('component_rows_sha256')==component_sha256['rows'] and policy['evidence'].get('component_runs_sha256')==component_sha256['runs'],'component generation mismatch')
    need(isinstance(selected,dict) and isinstance(regional,dict) and isinstance(regional.get('proposals'),dict) and isinstance(regional.get('review'),dict),'invalid claim sets')
    need(isinstance(pending_roots,(set,frozenset)) and isinstance(protected_roots,(set,frozenset)) and all(type(r) is int and 0<=r<0xffffffff for r in pending_roots|protected_roots),'invalid explicit protections')
    review=regional['review']
    need(all(type(r) is int and 0<=r<0xffffffff and isinstance(reason,str) and reason for r,reason in review.items()),'invalid regional reviews')
    pending=set(pending_roots)|{r for r,reason in review.items() if reason=='source_group_pending_review'}
    blocked_region_roots=set(review)|pending|set(protected_roots)
    claims={};withheld=[];selected_codes={}
    for root,items in selected.items():
        need(type(root) is int and 0<=root<0xffffffff and isinstance(items,list) and items,'invalid selected claim')
        for c in items:
            need(isinstance(c,dict) and set(c)=={'affiliation_id','entry_ids','code'} and isinstance(c['affiliation_id'],str) and c['affiliation_id'] and isinstance(c['entry_ids'],list) and c['entry_ids'] and c['entry_ids']==sorted(set(c['entry_ids'])) and type(c['code']) is int and 17<=c['code']<=22,'invalid selected claim')
        need(all(c['affiliation_id'] in compiled.get('affiliation_ids',[]) and c['entry_ids']==compiled.get('affiliation_entry_links',{}).get(c['affiliation_id']) for c in items),'selected claim is not linked to compiled policy')
        codes={c['code'] for c in items};need(len(codes)==1 and root not in protected_roots,'selected target conflict or protected root')
        selected_codes[root]=next(iter(codes))
        if root in pending:withheld.append(root)
        else:claims[root]=copy.deepcopy(items)
    trace={}
    for root,p in regional['proposals'].items():
        need(type(root) is int and 0<=root<0xffffffff and isinstance(p,dict) and p.get('basis') in BASES|{'selected_affiliation'} and type(p.get('code')) is int and p['code'] in (18,22),'invalid regional proposal')
        need(root not in protected_roots,'regional proposal hits protected root')
        if root in pending:continue
        need(root not in review,'reviewed root cannot be assigned')
        if root in selected_codes:
            need(selected_codes[root]==p['code'] and p['basis']=='selected_affiliation','regional proposal contradicts or masks selected claim')
            continue
        need(p['basis'] in BASES,'selected proposal lacks source claim')
        basis=p['basis']
        if basis=='whole_component_line_side':
            evidence={'line_id':LINE,'geometry_sha256':LINE_SHA}
        elif basis=='source_anchored_nearest_main_island':
            evidence=regional.get('satellites',{}).get(root)
            need(isinstance(evidence,dict) and isinstance(evidence.get('source_id'),str) and evidence['source_id'] and
                 isinstance(evidence.get('source_feature_id'),str) and evidence['source_feature_id'] and
                 isinstance(evidence.get('source_version'),str) and evidence['source_version'] and
                 isinstance(evidence.get('source_sha256'),str) and re.fullmatch(r'[0-9a-f]{64}',evidence['source_sha256']) is not None and
                 type(evidence.get('parent_root_current_generation_only')) is int and 0<=evidence['parent_root_current_generation_only']<0xffffffff and
                 type(evidence.get('distance_m')) in (int,float) and math.isfinite(evidence['distance_m']) and evidence['distance_m']>=0,
                 'missing satellite source evidence')
            evidence=copy.deepcopy(evidence)
        else:
            evidence=regional.get('regional_group_proposals',{}).get(root)
            need(isinstance(evidence,list) and evidence and all(isinstance(x,dict) and x.get('target_code')==p['code'] and
                 isinstance(x.get('group_id'),str) and x['group_id'] and isinstance(x.get('source'),dict) and x['source'] for x in evidence),
                 'missing regional-group source evidence')
            evidence=copy.deepcopy(evidence)
        claims[root]=[{'affiliation_id':RULE,'entry_ids':[RULE],'code':p['code']}]
        trace[root]={'basis':basis,'code':p['code'],'evidence':evidence,'policy_canonical_sha256':policy_canonical_sha256}
    return {'component_claims':claims,'regional_proposal_trace':trace,'withheld_selected_pending_roots':sorted(withheld),'synthetic_affiliation_id':RULE,'blocked_region_roots':sorted(blocked_region_roots),
            'provenance':{'policy_canonical_sha256':policy_canonical_sha256,'decision_snapshot_sha256':snapshot_sha256,'component_input_sha256':dict(component_sha256),'line_id':LINE,'geometry_sha256':LINE_SHA},
            'limitations':['Caller must authenticate current source inputs, same-run freshness and pending groups.',
                           'The writer retains baseline values where new claims are withheld; this does not mark the output unassigned.',
                           'Every region-claim channel must filter blocked roots before writing.']}


def filter_region_claims(region_claims, blocked_roots):
    """Remove protected, pending and reviewed roots from each region channel.

    Call for every row before passing claims to the mixed overlay. Geometry spans
    remain unchanged; empty root sets are dropped. Does not mutate the input.
    """
    need(isinstance(region_claims,list) and isinstance(blocked_roots,(set,frozenset,list,tuple)) and
         all(type(r) is int and 0<=r<0xffffffff for r in blocked_roots),'invalid region protections')
    blocked=set(blocked_roots);out=[]
    for item in region_claims:
        need(isinstance(item,dict) and set(item)=={'claim','roots','spans'} and
             isinstance(item['roots'],(set,frozenset)) and all(type(r) is int and 0<=r<0xffffffff for r in item['roots']) and
             isinstance(item['spans'],list),'invalid region claim')
        roots=set(item['roots'])-blocked
        if roots:out.append({'claim':copy.deepcopy(item['claim']),'roots':roots,'spans':list(item['spans'])})
    return out


def protected_region_rows(region_rows, blocked_roots):
    """Wrap the driver callback so every row's independent region channel is filtered."""
    need(callable(region_rows),'region row callback required')
    frozen=frozenset(blocked_roots)
    # Validate root types even if the callback is never invoked.
    filter_region_claims([],frozen)
    return lambda row: filter_region_claims(region_rows(row),frozen)

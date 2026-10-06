"""Complete scoped native observations, investigation queues and source batches.

This consumes the accepted frozen inventory. A sampled cell is never a verdict
about all of a component, water, or administrative assignment.
"""
import argparse
from collections import Counter, defaultdict
import copy
import gzip
import importlib.util
import json
import math
import pathlib
import platform
import subprocess
import sys
import numpy as np
import shapely
from evidence.immutable import canonical_json, descriptor, deterministic_gzip, sha256
from geographic_grid import CanonicalGrid
from physical_gap_priority import (ORDER_NAMES, attach_rank_positions,
    investigation_ranks, issue_subject_index, related_issue_scopes,
    validate_rank_positions)
from worldwide_native_observations import component_probe, observe_probes, full_owner_counts
from worldwide_gap_source_context import issue_rosters, administrative_product_context
from worldwide_gap_operational_batches import operational_batches, dispatch_candidates

ROOT = pathlib.Path(__file__).resolve().parents[1]
C = 'cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
M = '79ffb2ed04702e16f009e4675a8d74ef9bd09d4f'
H = '549cc2a863d4a487a662c2613e4d02888e39b5ba'
N = '548c5f89f00271050823076a84695bb41e1b8454'
IP = 'coordination/engineering/worldwide-inventory-1164-20261006/run-one/'
CP = 'coordination/engineering/worldwide-contexts-1184-20261006/run-one/'
PP = 'coordination/engineering/physical-gap-priorities-1005-20261006-local20/priorities-v2/'
OWNED = 'coordination/engineering/worldwide-native-batches-1184-20261006/'
MAX = 32 * 1024 * 1024

def verify_runtime(versions):
    expected={'python':'3.12.14','numpy':'2.3.5','shapely':'2.1.2','geos':'3.13.1'}
    if versions!=expected:raise ValueError('Pinned scientific runtime differs')

def verify_native_binding(manifest, context_report, label, latitude_count):
    expected=context_report['frozen_native_candidate'] if label=='frozen-reviewed-native' else context_report['selected_release']
    expected_release=expected['geographic_release'] if label=='frozen-reviewed-native' else expected['id']
    if (manifest['geographic_release']!=expected_release
            or manifest['footprints_sha256']!=expected['footprints_sha256']
            or manifest['hierarchy_sha256']!=expected['hierarchy_sha256']):
        raise ValueError('Exact cohort release/footprint/hierarchy binding differs')
    size=context_report['frozen_native_candidate']['size']
    if manifest['size']!=size or latitude_count!=size or manifest['coordinateBits']!=math.ceil(math.log2(size)):
        raise ValueError('Exact common probe/latitude/native coordinate domain differs')

def executed_code_equal(path, committed_bytes):
    import stat
    if not stat.S_ISREG(path.lstat().st_mode) or path.is_symlink() or path.read_bytes()!=committed_bytes:
        raise ValueError('Executed project code differs from committed custody: '+str(path))

def authenticate_executed_code(inputs,commit):
    paths={pathlib.Path(__file__).resolve()}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            path=pathlib.Path(file).resolve()
            if path.is_relative_to(ROOT/'scripts') and path.suffix=='.py':paths.add(path)
    for path in sorted(paths):
        executed_code_equal(path,inputs.read(commit,str(path.relative_to(ROOT))))
    return sorted(str(p.relative_to(ROOT)) for p in paths)

class Inputs:
    """Whole ordinary Git blobs, a bounded transport cache and full decoded pins."""
    def __init__(self):
        self.process = subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        self.modes, self.pins = {}, {}
    def read(self, commit, path, pin=None):
        if commit not in self.modes:
            tree=subprocess.check_output(['git','ls-tree','-r','-z',commit],cwd=ROOT)
            self.modes[commit]={r.split(b'\t',1)[1].decode():r.split(b' ',1)[0].decode()
                               for r in tree.split(b'\0') if r}
        if self.modes[commit].get(path) not in ('100644','100755'):
            raise ValueError('Input is not an ordinary file: '+path)
        self.process.stdin.write((commit+':'+path+'\n').encode());self.process.stdin.flush()
        header=self.process.stdout.readline().decode().split()
        if len(header)!=3 or header[1]!='blob' or int(header[2])>MAX:
            raise ValueError('Missing or oversized ordinary blob')
        raw=self.process.stdout.read(int(header[2]))
        if len(raw)!=int(header[2]) or self.process.stdout.read(1)!=b'\n':
            raise ValueError('Truncated ordinary blob')
        observed={**descriptor(path,raw),'commit':commit,'mode':self.modes[commit][path]}
        if pin and any(pin[k]!=observed[k] for k in ('sha256','bytes') if k in pin):
            raise ValueError('Whole input pin differs: '+path)
        self.pins[(commit,path)]=observed
        return raw
    def json(self,commit,path,pin=None):
        raw=self.read(commit,path,pin)
        if raw[:2]==b'\x1f\x8b':
            raw=gzip.decompress(raw)
            if len(raw)>MAX:raise ValueError('Oversized decoded ordinary input')
            if pin and any(pin[k]!=v for k,v in (
                    ('uncompressed_bytes',len(raw)),('uncompressed_sha256',sha256(raw))) if k in pin):
                raise ValueError('Decoded whole input pin differs')
            self.pins[(commit,path)].update(uncompressed_bytes=len(raw),uncompressed_sha256=sha256(raw))
        return json.loads(raw)

class GridSource:
    def __init__(self,inputs,commit,root,manifest):
        self.inputs,self.commit=inputs,commit
        self.pins={root+'/'+p['path']:p for p in manifest['parts']}
    def read(self,path):return self.inputs.read(self.commit,path,self.pins[path])

def write_parts(out,name,rows):
    pins=[];batch=[];size=0
    def flush():
        raw=canonical_json(batch)
        if len(raw)>MAX:raise ValueError('Oversized complete output shard')
        encoded=deterministic_gzip(raw);target=out/f'{name}-{len(pins):03d}.json.gz'
        target.write_bytes(encoded)
        pins.append({**descriptor(str(target.relative_to(ROOT)),encoded),
            'uncompressed_bytes':len(raw),'uncompressed_sha256':sha256(raw),'records':len(batch)})
    for row in rows:
        n=len(canonical_json(row))
        if batch and size+n>8*1024*1024:flush();batch=[];size=0
        batch.append(row);size+=n
    if batch:flush()
    return pins

def semantic_ranks(records):
    """Permutation alone is insufficient: verify complete tuple/ID order."""
    validate_rank_positions(records)
    result={}
    for name in ORDER_NAMES:
        ranked=sorted(records,key=lambda r:r['rank_positions'][name])
        expected=sorted(records,key=lambda r:r['investigation_orders'][name])
        a=[[r['component'],r['investigation_orders'][name]] for r in ranked]
        b=[[r['component'],r['investigation_orders'][name]] for r in expected]
        if a!=b:raise ValueError('Complete semantic rank order differs: '+name)
        if any(r['investigation_orders'][name][-1]!=r['component'] for r in records):
            raise ValueError('Missing explicit deterministic component-ID tie break')
        result[name]={'records':len(a),'ordered_id_tuple_sha256':sha256(canonical_json(a)),
            'view':'sort complete investigations by rank_positions.'+name}
    return result

def validate_batch_membership(batches,ids):
    observed=[c for b in batches for c in b['component_ids']]
    if len(observed)!=len(set(observed)) or set(observed)!=set(ids):
        raise ValueError('Missing or multiply assigned actionable batch component')
    for b in batches:
        if b['component_ids']!=sorted(b['component_ids']) or b['component_count']!=len(b['component_ids']):
            raise ValueError('Changed complete batch roster')
        if b['component_ids_sha256']!=sha256(canonical_json(b['component_ids'])):
            raise ValueError('Changed complete batch roster hash')

def observation_overlay(original,current):
    before={r['component']:r for r in original};after={r['component']:r for r in current}
    if len(before)!=len(original) or set(before)!=set(after) or len(after)!=len(current):
        raise ValueError('Comparison overlay requires the complete identical component roster')
    changed=[after[i] for i in sorted(after) if canonical_json(before[i])!=canonical_json(after[i])]
    overlay={'complete_component_ids_sha256':sha256(canonical_json(sorted(before))),
        'component_count':len(before),'original_rows_sha256':sha256(canonical_json([before[i] for i in sorted(before)])),
        'current_rows_sha256':sha256(canonical_json([after[i] for i in sorted(after)])),
        'changed_rows':changed,'unchanged_count':len(before)-len(changed)}
    replay=dict(before)
    for row in changed:replay[row['component']]=row
    if canonical_json([replay[i] for i in sorted(replay)])!=canonical_json([after[i] for i in sorted(after)]):
        raise ValueError('Full observation overlay reconstruction differs')
    return overlay

def verify_annotation_original(annotation,original,pin,ordinal):
    reference=annotation['original_investigation']
    if (annotation['component']!=original['component']
            or reference['path']!=pin['path'] or reference['file_sha256']!=pin['sha256']
            or type(reference['row_index'])is not int or reference['row_index']!=ordinal
            or reference['commit']!=C or annotation['native_observation_reference']['component']!=original['component']
            or annotation['native_observation_reference']['family']!='frozen-reviewed-native'):
        raise ValueError('Complete annotation original-file/index/identity binding differs')

def source_family(context):
    metadata=context['original_metadata']
    if context['id'].startswith('atlas:physical:'):
        return {'kind':'physical-adaptation-processing-reproduction',
            'original_source_member_ids':metadata.get('source_member_ids'),
            'source_id':metadata.get('source_id'),
            'source_token':{k:metadata[k] for k in ('ECO_ID','SUB_CODE','lake_id','lakeID') if k in metadata},
            'recorded_coastline_adjustments':metadata.get('coastline_adjustments'),
            'recipe':'scripts/refine-remote.py','vintage':C}
    return {'kind':'source-authority-and-product-comparison',
        'source_id':metadata.get('source_id'),'recorded_source_url':metadata.get('source_url'),
        'reference_year':metadata.get('reference_year'),'recipe':'scripts/administrative.py','vintage':C}

def classify(record,observation,contexts):
    ids=record['distinct_contact_ids'];edges=record['positive_length_neighbor_ids']
    closure=[contexts[i] for i in ids if i in contexts]
    regions=sorted({n['id'] for c in closure for n in c['ancestry'] if n['level']=='subcontinent'})
    families=[source_family(c) for c in closure]
    physical=any(f['kind']=='physical-adaptation-processing-reproduction' for f in families)
    bucket=observation['native_status']
    if record['unmeasured_fragment_ids']:bucket+=':unmeasured-impact'
    elif record['original_domain_flags']['touches_reference_shore']:bucket+=':reference-shore-context'
    elif len(edges)>=2:bucket+=':multiple-edge-neighbors'
    else:bucket+=':other-contact-context'
    # Shared complete source sets and geographic hierarchy define coordinated
    # questions. No nearest-owner or water inference is part of this grouping.
    key={'observed_scope_bucket':bucket,'subcontinents':regions,
         'work_kind':'processing-reproduction-and-source-comparison' if physical else 'source-authority-and-water-reference-research',
         'source_families':sorted({sha256(canonical_json(f)) for f in families}),
         'recorded_parent_ids':sorted({c['original_parent_id'] for c in closure if c['original_parent_id']})}
    return key,families

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);parser.add_argument('--issues',required=True)
    args=parser.parse_args();out=ROOT/args.output
    software={'python':platform.python_version(),'numpy':np.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string}
    verify_runtime(software)
    if not args.output.startswith(OWNED) or out.exists():raise ValueError('Fresh owned complete-output directory required')
    out.mkdir(parents=True);inputs=Inputs()
    inventory=inputs.json(M,IP+'report.json');context_report=inputs.json(H,CP+'report.json')
    contexts={}
    for d in context_report['outputs']:
        for row in inputs.json(H,d['path'],d):
            if row['id'] in contexts:raise ValueError('Duplicate context')
            contexts[row['id']]=row
    if len(contexts)!=49625 or context_report['context_count']!=49625:raise ValueError('Incomplete context closure')
    # Exact source/hierarchy/owner context already authenticated in accepted PR1.
    # All archived fields remain present in these expanded rows; no old transport
    # is consumed or given new native authority.
    bounds=inputs.json(C,'data/canonical-grid/bounds.json.gz')
    ordered=sorted(bounds,key=lambda x:x['index']) if isinstance(bounds,list) else sorted(bounds['locations'],key=lambda x:x['index'])
    if [r['index'] for r in ordered]!=list(range(1,49626)) or {r['id'] for r in ordered}!=set(contexts):
        raise ValueError('Complete native owner registry differs')
    if any(contexts[r['id']]['frozen_owner_registry']!=r for r in ordered):raise ValueError('Complete accepted owner-order binding differs')
    owner_ids=[None]+[r['id'] for r in ordered]
    hierarchy=inputs.read(C,'data/hierarchy.json');hierarchy_hash=sha256(hierarchy)
    code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
    executed_modules=authenticate_executed_code(inputs,code_commit)
    for p in ('scripts/build-worldwide-native-batches.py','scripts/worldwide_native_observations.py',
              'scripts/worldwide_gap_source_context.py','scripts/physical_gap_priority.py',
              'scripts/geographic_grid.py','scripts/evidence/immutable.py',
              'scripts/administrative.py','scripts/refine-remote.py'):
        inputs.read(code_commit,p)
    pages=json.loads(pathlib.Path(args.issues).read_bytes());strong,weaker,rejected=issue_rosters(pages)
    issue_raw=canonical_json(pages);issue_path=out/'all-state-issues.json.gz';issue_encoded=deterministic_gzip(issue_raw)
    if len(issue_raw)>MAX:raise ValueError('Oversized complete issue snapshot')
    issue_path.write_bytes(issue_encoded)
    subject_sets=defaultdict(set);roster_by_issue=defaultdict(list)
    for row in strong:subject_sets[row['issue']].update(row['subject_ids']);roster_by_issue[row['issue']].append(row)
    compiled=issue_subject_index(subject_sets)
    registry=inputs.json(M,'data/administrative-sources.json');policy=inputs.json(M,'data/location-policy.json')
    source_rows=[]
    for identity in sorted(contexts):
        c=contexts[identity]
        source_rows.append({'id':identity,'original_metadata_sha256':sha256(canonical_json(c['original_metadata'])),
            'source_family':source_family(c),'administrative_product_context':administrative_product_context(c['original_metadata'],registry,policy),
            'selected_successor_applicability':c['selected_successor_applicability'],'cause_status':'unknown'})
    root='coordination/engineering/native-grid-candidate-1010-20261005-local16/candidate-v1'
    native=inputs.json(N,root+'/manifest.json');latpin=native['native_latitudes']
    latraw=inputs.read(latpin['commit'],latpin['path'],latpin);latdecoded=gzip.decompress(latraw)
    if len(latdecoded)!=latpin['decoded_bytes'] or sha256(latdecoded)!=latpin['decoded_sha256']:
        raise ValueError('Stored normative latitude stream differs')
    latitudes=np.frombuffer(latdecoded,dtype='<f8')
    if len(latitudes)!=native['size'] or not np.all(np.isfinite(latitudes)) or not np.all(latitudes[1:]<latitudes[:-1]):
        raise ValueError('Invalid normative latitude domain or order')
    geometry_probes=[];component_ids=[]
    for d in inventory['complete_products']['components']:
        path=next(p['path'] for p in inventory['source_descriptors'] if p['sha256']==d['sha256'])
        collection=inputs.json(M,path,d)
        if not isinstance(collection,dict) or collection.get('type')!='FeatureCollection' or not isinstance(collection.get('features'),list):
            raise ValueError('Complete component product must preserve its FeatureCollection wrapper')
        for feature in collection['features']:
            component_ids.append(feature['id']);geometry_probes.append(component_probe(feature,native['size'],latitudes))
    if len(component_ids)!=95174 or len(set(component_ids))!=95174:raise ValueError('Incomplete accepted component cohort')
    print('complete geometry probes',len(geometry_probes),flush=True)
    outputs={};grid_reports={};frozen_observations=None
    for label,commit,gridroot in [('frozen-reviewed-native',N,root),('selected-repository-native',M,'data/native-ownership/repaired-v7')]:
        manifest=inputs.json(commit,gridroot+'/manifest.json')
        verify_native_binding(manifest,context_report,label,len(latitudes))
        if manifest['method']!='native-linear-evenodd-first-owner-v1' or manifest['hierarchy_sha256']!=hierarchy_hash or manifest['native_latitudes']!=latpin:
            raise ValueError('Native rule/source binding differs')
        # Source custody hashes and release applicability come from accepted PR1.
        if label=='selected-repository-native' and manifest['geographic_release']!=context_report['selected_release']['id']:
            raise ValueError('Selected repository native release differs')
        adapted=copy.deepcopy(manifest)
        for p in adapted['parts']:p['compressed_bytes']=p['bytes']
        grid=CanonicalGrid(GridSource(inputs,commit,gridroot,manifest),adapted,gridroot,max_owner_id=len(owner_ids)-1)
        observations,counts=observe_probes(geometry_probes,grid,owner_ids)
        owners,accounting=full_owner_counts(grid,owner_ids)
        if label=='frozen-reviewed-native':outputs[label]=write_parts(out,label,observations)
        else:
            overlay=observation_overlay(list(frozen_observations.values()),observations)
            outputs[label+'-complete-overlay']=write_parts(out,label+'-complete-overlay',[overlay])
        outputs[label+'-owner-counts']=write_parts(out,label+'-owner-counts',owners)
        grid_reports[label]={'manifest_commit':commit,'manifest_path':gridroot+'/manifest.json',
            'release':manifest['geographic_release'],'footprints_sha256':manifest['footprints_sha256'],
            'hierarchy_sha256':manifest['hierarchy_sha256'],'component_count':len(observations),
            'status_counts':counts,'full_grid_accounting':accounting,
            'applicability':'frozen component geometry; selected native grid is a comparison only, not selected-successor component measurements'}
        if label=='frozen-reviewed-native':frozen_observations={r['component']:r for r in observations}
        del grid,owners,observations
        print('complete native cohort',label,counts,flush=True)
    prior=inputs.json(C,PP+'report.json');investigations=[];annotations={};groups={};triage_counts=Counter()
    for d in prior['outputs']['investigations']:
        for ordinal,archived in enumerate(inputs.json(C,d['path'],d)):
            identity=archived['component']
            if identity not in frozen_observations:raise ValueError('Original investigation absent from complete cohort')
            record=copy.deepcopy(archived)
            record['archived_investigation_row_sha256']=sha256(canonical_json(archived))
            links=related_issue_scopes(record['distinct_contact_ids'],record['positive_length_neighbor_ids'],subject_sets,compiled)
            for link in links:
                link['declaration_roster_indices']=[n for n,r in enumerate(strong) if r['issue']==link['issue']]
            record['current_issue_subject_joins']=links
            record['native_observation']=frozen_observations[identity]
            record['investigation_orders']=investigation_ranks(record,contexts)
            key,families=classify(record,frozen_observations[identity],contexts)
            bid='gap-source-batch:'+sha256(canonical_json(key))[:24]
            record['actionable_batch_id']=bid
            record['cause_triage']={'observed_bucket':key['observed_scope_bucket'],'cause_status':'unknown',
                'processing_clues_are_hypotheses':True,'source_family_references':[sha256(canonical_json(f)) for f in families]}
            annotations[identity]={'component':identity,'original_investigation':{'commit':C,'path':d['path'],
                'file_sha256':d['sha256'],'row_index':ordinal},
                'native_observation_reference':{'family':'frozen-reviewed-native','component':identity},
                'current_issue_subject_joins':links,'actionable_batch_id':bid,'cause_triage':record['cause_triage']}
            verify_annotation_original(annotations[identity],archived,d,ordinal)
            triage_counts[key['observed_scope_bucket']]+=1
            group=groups.setdefault(bid,{'id':bid,'grouping':key,'component_ids':[],'contact_ids':set(),
                'edge_neighbor_ids':set(),'existing_related_issues':set(),'source_families':{},'best_rank':{}})
            group['component_ids'].append(identity);group['contact_ids'].update(record['distinct_contact_ids'])
            group['edge_neighbor_ids'].update(record['positive_length_neighbor_ids']);group['existing_related_issues'].update(l['issue'] for l in links)
            for f in families:group['source_families'][sha256(canonical_json(f))]=f
            investigations.append(record)
    if len(investigations)!=95174 or {r['component'] for r in investigations}!=set(component_ids):
        raise ValueError('Incomplete full investigation accounting')
    attach_rank_positions(investigations);queues=semantic_ranks(investigations)
    rank_by_id={r['component']:r['rank_positions'] for r in investigations};batches=[]
    for bid in sorted(groups):
        g=groups[bid];g['component_ids'].sort();g['component_count']=len(g['component_ids'])
        g['component_ids_sha256']=sha256(canonical_json(g['component_ids']))
        for field in ('contact_ids','edge_neighbor_ids','existing_related_issues'):g[field]=sorted(g[field])
        g['source_families']=[g['source_families'][h] for h in sorted(g['source_families'])]
        g['best_rank']={name:min(rank_by_id[c][name] for c in g['component_ids']) for name in ORDER_NAMES}
        extents=[frozen_observations[c]['original_extent_lonlat'] for c in g['component_ids'] if frozen_observations[c]['original_extent_lonlat'] is not None]
        g['original_member_extent_references']={'family':'frozen-reviewed-native','field':'original_extent_lonlat','missing_extent_component_ids':[c for c in g['component_ids'] if frozen_observations[c]['original_extent_lonlat'] is None]}
        g['aggregate_extent_lonlat']=None if not extents else [min(e[0] for e in extents),min(e[1] for e in extents),max(e[2] for e in extents),max(e[3] for e in extents)]
        g['aggregate_extent_scope']='bounding envelope of recorded member extents; dateline or disconnected membership may span a broad region'
        g['responsible_role']='engineering-processing-reproduction' if g['grouping']['work_kind']=='processing-reproduction-and-source-comparison' else 'GEO-source-research'
        g['research_question']='Authenticate consumed source product and neighboring contact geometry/vintages; distinguish source mismatch, recorded processing, genuine water and unresolved evidence. No fill or owner assignment.'
        g['engineering_question']='Reproduce recorded recipe for this full coordinated source/contact family; demonstrate exact before/after geometry and native-cell scope before any proposed repair.'
        g['dispatch_status']='triaged-backlog-needs-canonical-scope-and-live-claim-check'
        g['acceptance']=['Classify every member with evidence and explicit unknowns.','Preserve all complete contact subjects and shared source closure.','Unknown is acceptable in evidence collection, not evidence of global repair completion.','Reuse archived closed predecessors and coexist with broader regional semantic reviews.']
        batches.append(g)
    validate_batch_membership(batches,component_ids)
    operational=operational_batches(batches)
    for record in investigations:
        annotations[record['component']]['rank_positions']=record['rank_positions']
        annotations[record['component']]['investigation_orders']=record['investigation_orders']
    outputs['complete-investigation-annotations']=write_parts(out,'complete-investigation-annotations',[annotations[i] for i in sorted(annotations)])
    outputs['batches']=write_parts(out,'batches',batches)
    outputs['operational-batches']=write_parts(out,'operational-batches',operational)
    outputs['source-product-contexts']=write_parts(out,'source-product-contexts',source_rows)
    outputs['issue-rosters']=write_parts(out,'issue-rosters',strong)
    outputs['weaker-issue-context']=write_parts(out,'weaker-issue-context',weaker)
    outputs['rejected-issue-declarations']=write_parts(out,'rejected-issue-declarations',rejected)
    report={'version':'worldatlas-worldwide-native-batches-v1','executed_code_commit':code_commit,
        'frozen_measurement_commit':C,'accepted_inventory_commit':M,'accepted_context_commit':H,
        'component_count':len(component_ids),'context_count':len(contexts),'batch_count':len(batches),
        'operational_batch_count':len(operational),
        'complete_component_roster_sha256':sha256(canonical_json(sorted(component_ids))),
        'complete_context_roster_sha256':sha256(canonical_json(sorted(contexts))),
        'inputs':list(inputs.pins.values()),'outputs':outputs,'native_cohorts':grid_reports,
        'triage_counts':dict(sorted(triage_counts.items())),'rank_views':queues,
        'executed_project_modules':executed_modules,
        'complete_investigation_view':{'count':len(investigations),'original_complete_rows':prior['outputs']['investigations'],
            'view':'Read every original investigation, authenticate row_index/file/row hashes, then join its one annotation and referenced native observation/validated issue rosters by exact component ID. Original fields remain available at their archived vintage; annotations carry the new triage/rank/batch assessment.',
            'annotation_roster_sha256':sha256(canonical_json(sorted(annotations))),
            'original_fields_preserved':True,'original_context_transport':'All original fields preserved in accepted full expanded contexts; ordinary preservation proof accompanies final evidence.'},
        'prioritized_dispatch_candidates':dispatch_candidates(operational),
        'all_state_issue_snapshot':{**descriptor(str(issue_path.relative_to(ROOT)),issue_encoded),
            'uncompressed_bytes':len(issue_raw),'uncompressed_sha256':sha256(issue_raw),
            'pages':len(pages),'strong_rosters':len(strong),'weaker_rosters':len(weaker),
            'atomic_snapshot':False,'live_claim_eligibility':'not-established-by-issue-snapshot'},
        'software':software,
        'limits':['No whole component, surface, water, administrative or source authority inferred from one cell.',
            'Frozen reviewed native materialization was not the runtime-selected legacy grid.',
            'Selected repository native comparison uses frozen component geometry; successor cohort pending accepted complete successor handoff.',
            'Every original investigation and context retained; archived grid/water fields remain archived.',
            'Disjoint complete batches are coordinated research/reproduction scopes, not approved repair or automatically claimable issues.']}
    (out/'report.json').write_bytes(canonical_json(report))
    print(json.dumps({'components':len(component_ids),'contexts':len(contexts),'batches':len(batches),'triage':report['triage_counts']}),flush=True)

if __name__=='__main__':main()

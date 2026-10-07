"""Frozen complete two-subject correction proposal; never activates current data."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess,sys
import shapely,numpy
from shapely.geometry import shape,mapping
from shapely import union_all
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from evidence.immutable import canonical_json,deterministic_gzip,descriptor,safe_path
from evidence.geometry import canonical_prepared_land,METHOD,PREPARED_DOMAIN
from reader import load,digest,checked_file
from kernel import TARGETS,exact_addition,complete_neighbor_relations,exact_two_feature_replacements
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('eastern_regression',ROOT/'scripts/check-geographic-regression.py');regression=importlib.util.module_from_spec(spec);sys.modules[spec.name]=regression;spec.loader.exec_module(regression)
EXPECTED_G={'atlas:physical:CAN-103:QUE':'b8b357848262d2ccb59b0e9823439c76f329e5dc9baa7678fa0e5bdfb23b1265','atlas:physical:CAN-114:NFL':'172a25d939353bed6168c950cb0f9aaba75e7ff770aad053c7e36c963a6dc98e'}
NODE='/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'

def authenticate_code(commit):
    if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Exact execution commit before Git')
    files={Path(__file__).resolve(),P/'input-index.json',ROOT/'scripts/check-prepared.mjs'}
    for module in list(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            path=Path(file).resolve()
            if path.is_relative_to(ROOT)and path.suffix in ('.py','.mjs'):files.add(path)
    pins=[]
    for path in sorted(files):
        relative=safe_path(str(path.relative_to(ROOT)))
        entry=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-z',commit,'--',relative]).decode().rstrip('\0')
        fields=entry.split('\t')
        if len(fields)!=2 or fields[1]!=relative or not fields[0].startswith(('100644 blob ','100755 blob ')):raise ValueError('Executed code must be ordinary committed file')
        raw=subprocess.check_output(['git','-C',str(ROOT),'cat-file','blob',fields[0].split()[2]])
        if path.is_symlink()or path.read_bytes()!=raw:raise ValueError('Actual executed code bytes differ: '+relative)
        pins.append({'commit':commit,**descriptor(relative,raw)})
    return pins

def footprint_hash(features):
    script="import fs from 'node:fs';import {footprintHash} from './scripts/check-prepared.mjs';process.stdout.write(footprintHash(JSON.parse(fs.readFileSync(0))));"
    return subprocess.check_output([NODE,'--input-type=module','-e',script],cwd=ROOT,input=(json.dumps(list(features.values()),ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()).decode()

def run(commit,target):
    code=authenticate_code(commit)
    if sys.version_info[:3]!=(3,12,14)or shapely.__version__!='2.1.2'or shapely.geos_version_string!='3.13.1'or numpy.__version__!='2.3.5':raise ValueError('Pinned numerical runtime required')
    if target.exists()or any(x.is_symlink()for x in [target,*target.absolute().parents]):raise ValueError('Fresh ordinary output directory required')
    data=load(P,ROOT);world=data['world'];subjects=data['receipt']['world']['fixedpoint_current_subject_ids'];retired=data['retired'];native=data['native']
    print(json.dumps({'step':'complete-inputs','world':len(world),'inputs':data['receipt']['ordinary_inputs']}),flush=True)
    prepared={};seams=[]
    for n,(identity,f)in enumerate(sorted(world.items())):
        contacts=[]
        prepared[identity]=canonical_prepared_land(shape(f['geometry']),seam_contacts=contacts)
        seams.extend({'location_id':identity,**contact}for contact in contacts)
        if n and n%10000==0:print(json.dumps({'step':'complete-prepared-world','features':n}),flush=True)
    native_groups={}
    for f in native:native_groups.setdefault(f['properties']['ECOREGION_ID'],[]).append(f)
    corrections=[];geometries={};neighbors=[]
    for identity,cid in TARGETS.items():
        if digest(canonical_json(data['components'][cid]['geometry']))!=EXPECTED_G[identity]:raise ValueError('Exact Main-approved whole gap geometry changed')
        feature=world[identity];metadata=feature['properties']['metadata'];eco=metadata['ecoregion_id'];native_members=native_groups[eco]
        if len(native_members)!=1:raise ValueError('Two approved source assignments require exact untouched single native record')
        original=shape(native_members[0]['geometry']);gap=shape(data['components'][cid]['geometry']);old=shape(feature['geometry'])
        cohort=[world[s]for s in subjects if s.rsplit(':',1)[1]==identity.rsplit(':',1)[1]];mids={m for f in cohort for m in f['properties']['metadata']['source_member_ids']};parents=[f for f in retired if f['id']in mids]
        if {f['id']for f in parents}!=mids:raise ValueError('Full current source/member closure changed')
        for parent in parents:
            if not shape(parent['geometry']).is_valid:raise ValueError('Invalid original parent envelope operand')
        envelope=union_all([shape(f['geometry'])for f in parents]);new,evidence=exact_addition(identity,cid,old,gap,original,envelope)
        covering=[]
        for eid,records in native_groups.items():
            geom=union_all([shape(f['geometry'])for f in records])
            if not geom.is_valid:raise ValueError('Invalid native region prevents full unique-source proof')
            if geom.covers(gap):covering.append(eid)
        if covering!=[eco]:raise ValueError('Whole194 native source uniqueness changed')
        physical=data['physics'][cid]['complete_support']
        if not shape(physical['mapped_land_support']['geometry']).equals(gap):raise ValueError('Whole physical mapped-land support differs from G')
        for name,row in physical.items():
            if name=='mapped_land_support':continue
            rows=row.values()if name=='hierarchy_disagreements'else[row]
            if any(not shape(v['geometry']).is_empty for v in rows):raise ValueError('Physical outside/water/contradictory/unreconstructed context present')
        relations=complete_neighbor_relations(identity,canonical_prepared_land(old),canonical_prepared_land(new),list(prepared.items()))
        if len(relations)!=6:raise ValueError('Full six-neighbor coordinated closure changed')
        neighbors.append({'subject_id':identity,'complete_relations':relations})
        geometries[identity]=mapping(new)
        corrections.append({'subject_id':identity,'component_id':cid,'source_id':metadata['source_id'],'complete_native_source_ids':covering,'source_scope':'Main-approved physical-reference portion correction only','cohort_current_ids':sorted(f['id']for f in cohort),'cohort_retired_ids':sorted(mids),'pointsets':evidence,'geometry_sha256_before':digest(canonical_json(feature['geometry'])),'geometry_sha256_after':digest(canonical_json(mapping(new))),'component_geometry_sha256':digest(canonical_json(data['components'][cid]['geometry'])),'historical_cause':'unknown','historical_transfer':False})
        print(json.dumps({'step':'exact-construction','subject':identity,'neighbors':len(relations),'gain_equals_whole_G':True,'loss_empty':True}),flush=True)
    after={f['id']:f for f in exact_two_feature_replacements(list(world.values()),geometries)}
    for identity in world:
        if identity not in TARGETS and canonical_json(world[identity])!=canonical_json(after[identity]):raise ValueError('Other feature canonical bytes changed')
        if world[identity]['properties']!=after[identity]['properties']:raise ValueError('Source properties/identity changed')
    report=regression.compare(world,after)
    if report['status']!='no-new-regression'or report['regressions']!=0 or report['changed_location_ids']!=sorted(TARGETS):raise ValueError('Complete whole-world geometry regression failed')
    before_footprints=footprint_hash(world);after_footprints=footprint_hash(after)
    release=data['inputs'].json('data/geographic-releases/releases-v7-repacked-gzip.json.gz')['releases'][-1]
    if release['footprints_sha256']!=before_footprints or release['version']!=7:raise ValueError('Actual old release/full current world mismatch')
    contexts={}
    for suffix,expected in [('QUE',(55,434)),('NFL',(37,610))]:
        cohort={s for s in subjects if s.endswith(':'+suffix)};rows=[f for f in data['all_families']if cohort.intersection(f['contact_ids'])]
        ids={c for f in rows for c in f['component_ids']}
        if (len(rows),len(ids))!=expected:raise ValueError('Complete regional contact family context changed')
        contexts[suffix]={'complete_families':rows,'complete_component_ids':sorted(ids)}
    target.mkdir(parents=True)
    outputs=[]
    def write(name,value,preserve_geometry_order=False):
        raw=(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()if preserve_geometry_order else canonical_json(value)
        if len(raw)>32*1024**2:raise ValueError('Full output decoded cap')
        enc=deterministic_gzip(raw)if name.endswith('.gz')else raw
        with(target/name).open('xb')as f:f.write(enc)
        outputs.append({**descriptor(name,enc),'decoded_bytes':len(raw),'decoded_sha256':digest(raw)})
    write('corrections.json.gz',corrections);write('neighbors.json.gz',neighbors);write('full-source-scope.json.gz',{'current':[world[s]for s in subjects],'retired':retired,'native':data['native_scope']})
    write('full-four-family-context.json.gz',{'families':data['families'],'components':[data['components'][c]for c in sorted(data['components'])],'physics':[data['physics'][c]for c in sorted(data['physics'])],'dispositions':[{'component_id':c,'status':'proposed-whole-addition'if c in TARGETS.values()else'unchanged-unresolved'}for c in sorted(data['components'])]})
    write('complete-regional-contact-context.json.gz',contexts);write('whole-world-geographic-regression.json.gz',report);write('whole-world-prepared-validation.json.gz',{'method':METHOD,'domain':PREPARED_DOMAIN,'feature_count':len(prepared),'feature_geometry_sha256':digest(canonical_json([[i,digest(canonical_json(mapping(g)))]for i,g in sorted(prepared.items())])),'all_original_zero_area_periodic_seam_contacts':seams,'errors':[]})
    oldpart=data['inputs'].json('data/geography/part-29.json');proposed={**oldpart,'features':[after[f['id']]for f in oldpart['features']]};write('proposed-part-29.json.gz',proposed,preserve_geometry_order=True)
    write('crosswalk.json.gz',{'changed_ids':sorted(TARGETS),'removed_ids':[],'added_ids':[],'reused_ids':sorted(set(world)-set(TARGETS)),'before_footprints_sha256':before_footprints,'after_footprints_sha256':after_footprints,'archives':[{'id':i,'feature':world[i]}for i in sorted(TARGETS)],'relationships':[{'kind':'source-backed-physical-envelope-correction','before_ids':[i],'after_ids':[i],'history_transfer':False,'identity_pairs':[{'before_id':i,'after_id':i}]}for i in sorted(TARGETS)],'history_transfer':False,'source_evidence':[{'url':world[i]['properties']['metadata']['source_url'],'source_sha256':digest(data['native_source_files']['aafc-ecoregions.geojson']),'subject_id':i}for i in sorted(TARGETS)],'geometry_stage_validated':True,'historical_claims_transferred':False},preserve_geometry_order=True)
    write('release-footprint-proposal.json',{'before_release':release,'proposed_version':8,'proposed_footprints_sha256':after_footprints,'membership_and_hierarchy':'unchanged; successor registry construction and native/context activation required in PR2','activated':False,'published':False})
    if code!=authenticate_code(commit):raise ValueError('Executed module closure changed during complete run')
    write('report.json',{'version':1,'issue':1295,'stage':'complete-two-target-proposal-only','execution_commit':commit,'executed_project_modules':code,'inputs':data['receipt'],'software':{'python':sys.version,'numpy':numpy.__version__,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'node':subprocess.check_output([NODE,'--version']).decode().strip()},'counts':{'world':49625,'changed':2,'unchanged':49623,'families':4,'components':64,'unchanged_unresolved_components':62,'current_scope':24,'retired_scope':477,'native_source_regions':24,'neighbor_relations':12},'outputs':outputs[:],'before_footprints_sha256':before_footprints,'after_footprints_sha256':after_footprints,'current_pointers_activated':False,'limits':['Main source-envelope fit is limited to the two approved physical-region references, not legal administrative authority.','Historical cause, other gap repairs and water truth are not inferred.','PR2 successor release/native/context/selection/certificate/content acceptance remains required. No deployment.']})
    print(json.dumps({'status':'complete-proposal','outputs':len(outputs),'changed':2,'regressions':0}),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args();run(a.commit,a.out)

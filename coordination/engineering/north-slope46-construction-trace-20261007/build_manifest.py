"""Issue1353 complete ordinary ledger; no source queries or geometry operations."""
import gzip,hashlib,io,json,pathlib,subprocess
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREFIX=str(HERE.relative_to(ROOT))+'/'
BASE='162f13f76ccae7ac026e075331d2b7b10e1d63ab'
SCIENCE='1208538e0ae9dba868bcf9fffc34301ea825b588'
WORKER='01a10893-2a57-72e0-aa08-5c36088d5206'
LIMIT=33554432

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
def descriptor(path):
    if path.is_symlink()or not path.is_file()or path.stat().st_size>LIMIT:raise ValueError('Ordinary bounded final file required')
    raw=path.read_bytes();pin={'path':str(path.relative_to(ROOT)),'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes','role':'evidence'}
    if path.suffix=='.gz':
        with gzip.GzipFile(fileobj=io.BytesIO(raw))as handle:decoded=handle.read(LIMIT+1)
        if len(decoded)>LIMIT:raise ValueError('Decoded final ordinary bound')
        pin.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
    return pin

def main():
    index=json.loads((HERE/'input-index.json').read_bytes());source=index['source_files']
    if len(source)!=246 or len({p['path']for p in source})!=246 or sum(p['bytes']for p in source)!=237274443:raise ValueError('Complete246 input closure differs')
    tree_raw=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-z',BASE,'--',*[p['path']for p in source]])
    tree={x.split(b'\t',1)[1].decode():x.split(b'\t',1)[0].decode().split()for x in tree_raw.split(b'\0')if x}
    for p in source:
        if tree.get(p['path'])!=[p['mode'],'blob',p['blob']]:raise ValueError('Historical whole body not identical at declared ancestor baseline '+p['path'])
    baseline=[{**{k:p[k]for k in ('path','bytes','sha256')},'hash_kind':'file-bytes','role':'original-source',**{k:p[k]for k in ('uncompressed_bytes','uncompressed_sha256')if k in p}}for p in source]
    issue=json.loads((HERE/'issue-snapshot.json').read_bytes());contract=json.loads(issue['body'].split('<!-- worldatlas-work:v1',1)[1].split('-->',1)[0]);pins=contract['evidence_quality']['pins'];pin_files={}
    for name,value in pins.items():
        matches=[p['path']for p in source if p['sha256']==value]
        if not matches:raise ValueError('Actual required baseline pin missing '+name)
        pin_files[name]=next((p for p in matches if not p.endswith('.bin')),matches[0])
    post_path=HERE/'v/post-controls-final.json'
    if post_path.exists():
        post=json.loads(post_path.read_bytes())
        if post.get('outcome')!='passed' or post.get('actual_controls')!=11 or any(r.get('outcome')!='passed'for r in post['controls']):raise ValueError('Missing actual supplementary helper/reader controls')
        for kind in ('positive-control','negative-control'):
            path=HERE/('v/retained-exact-point-diagnosis-'+kind+'.json')
            value=json.loads(path.read_bytes());value['separately_executed_supplementary_controls']=post
            path.write_bytes(canonical(value))
    paths=[p for p in sorted(HERE.rglob('*'))if p.is_file()and not any(n in ('.cache','__pycache__')for n in p.relative_to(HERE).parts)and p.name!='evidence-quality.json']
    outputs=[descriptor(p)for p in paths];budget=sum(p['bytes']for p in baseline+outputs)
    if budget>268435456 or len(baseline)+len(outputs)>512:raise ValueError('Actual complete ordinary admission overflow')
    report=json.loads((HERE/'r1/report.json').read_bytes());replay=json.loads((HERE/'v/reproducibility.json').read_bytes())
    if replay['outcome']!='passed'or replay['run_one_sha256']!=replay['run_two_sha256']:raise ValueError('Actual two complete scientific trees required')
    sources=[]
    for identity,url,role,vintage,terms in (
      ('original-gshhg237-physical-source','https://www.soest.hawaii.edu/pwessel/gshhg/','Complete retained original GSHHG native source records, pointsets, hierarchy, periodic frames and distribution member/terms custody through original physical source aliases.','GSHHG2.3.7 release2017; heterogeneous underlying observations, WDBII lake/river misregistration and unresolved temporal applicability.','Original distributed LGPL/COPYING/LICENSE and README wording retained with their conflict; no new interpretation of permission or factual authority.'),
      ('original-usa-adm2-geoboundaries','https://www.geoboundaries.org/','Whole original consumed USAADM2 source and complete retained catalogue/individual attribution; exact3233 source records are provenance, not a new territory/water finding.','Registry represented2018; immutable original product and metadata retained; temporal/source fitness unapproved.','Original registry Public Domain claim and geoBoundaries derivative attribution retained; no newly verified government/source-authority assertion.'),
      ('original-v7-physical-routing-diagnosis','https://github.com/ChengshuLi/WorldAtlas/tree/'+BASE+'/coordination/engineering/complete-numeric-closure-diagnosis-20261007','Complete original candidate/context reconstruction, all45 numeric products, original physical/routing reports and full scoped queries; immutable source observations retained.','Audited c6 v7 geometry, original104 physical operations, actual019 routing and bec numeric delivery; repository delivery is not a new physical observation.','Original underlying source terms/credits remain bound by246 full ordinary files and their original-vintage relations.'),
      ('original-north-slope-processing-provenance','https://github.com/ChengshuLi/WorldAtlas/blob/'+BASE+'/scripts/refine-remote.py','Whole current contact, semantic source metadata/report and original recipe as provenance only; historical adaptation is not executed or causally established.','North Slope reference adapted using recorded RESOLVE407 Arctic coastal tundra; original observation date/complete historical execution inputs remain unresolved.','Original source credits/terms are retained without approval of ecological, administrative, political or dated-water facts.')):
        sources.append({'id':identity,'url':url,'role':role,'vintage':vintage,'retrieved_at':'2026-10-07; actual complete source reads and original delivery/commit/mode/OID/hash relations in input-index and both execution reports.','license':{'status':'unknown','terms':terms},'retention':'restoration-only','verification':'unverified','temporal_status':'unknown','restoration':'All246 existing whole ordinary input bodies remain at the declared ancestor with identical mode/OID; input-index retains the original commit/path/encoded+decoded SHA and supported complete-byte source/candidate reconstruction. No hash-only payload or new download.','limit':'Source/date/precision/registration/invalid/seam/physical and legal authority remain unapproved; local numerical construction evidence does not establish Atlas missing dry land, water, ownership or repair.'})
    fields=[('complete-components','/scope_components',46),('numeric-siblings','/numeric_siblings',28),('nonnumeric-siblings','/nonnumeric_siblings',18),('complete-local-queries','/actual_query_replays',209),('complete-pointset-objects','/geometry_objects',776),('original-nine-mapping-matches','/statuses/original-mappings-matched',46)]
    methods=[{'id':'literal104-stage-observation','kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Unmodified original104 alternating_support with scoped Python observation hook; retain exact ordered original and fresh query pieces, all whole native/periodic sources, all4 level unions, every support/intermediate/footprint and final6+3 mapping. Complete-source operands restore only exact authenticated native record/frame. Two actual committed1208538 full46 runs; original numeric diagnoses remain literal.','software':'Python3.12.14 NumPy2.3.5 Shapely2.1.2 GEOS3.13.1 pyproj3.7.2; actual18-file/import closure and9 runtime file pins retained in both reports.','units':'whole original binary64 geometry bytes and component/query/pointset counts; no new area/distance source measurement'},
      {'id':'retained-exact-point-diagnosis','kind':'measurement','description':'Unchanged accepted exact-predicate helper/caps applied only after canonical equality of all6+3 original mappings. Retain all invalid/unsupported/nontriangle cases and exact original vertex/rational triangle centroid witnesses; exact point contradiction does not certify a whole polygon or corrected partition.','software':'Unchanged accepted kernel.py/exact_predicates.py bytes; original IEEE754 points interpreted as exact rationals in OGC:CRS84 x=longitude,y=latitude.','units':'Exact source-relative point states and retained stage correspondence; no epsilon, normalization or coordinate edits'}]
    validation=[{'method_id':m,'kind':k,'outcome':'passed','evidence_path':PREFIX+'v/'+m+'-'+k+'.json'}for m in ('literal104-stage-observation','retained-exact-point-diagnosis')for k in ('positive-control','negative-control')]
    validation.append({'method_id':'literal104-stage-observation','kind':'reproducibility','outcome':'passed','evidence_path':PREFIX+'v/reproducibility.json'})
    manifest={'version':1,'issue':1353,'lane':'engineering','worker_id':WORKER,'subject_ids':['atlas:physical:01966024a7da3c19f62b'],'subject_ids_sha256':sha(json.dumps(['atlas:physical:01966024a7da3c19f62b'],separators=(',',':')).encode()),'baseline':{'commit':BASE,'files':baseline,'pins':pins,'pin_files':pin_files,'subject_files':{'atlas:physical:01966024a7da3c19f62b':'data/geography/part-25.json'}},'sources':sources,'outputs':outputs,'methods':methods,'validation':validation,'metrics':[{'id':name,'value':value,'unit':'complete retained identities or query relations','vintage':'archived','evaluation_commit':SCIENCE,'input_sha256':sha((HERE/'scope.json').read_bytes())}for name,pointer,value in fields],'metric_bindings':[{'metric_id':name,'path':PREFIX+'r1/report.json','json_pointer':pointer}for name,pointer,value in fields],'summaries':[],'conclusions':[{'status':'unresolved','source_ids':[s['id']for s in sources],'text':'Complete stage capture/diagnosis is delivered for all46/209, with original6+3 mappings reproduced for every sibling. All4 earlier replay mismatches are preserved and resolve after exact original whole-source operands are restored. Captured original candidate.difference(footprint) retains local exact outside-candidate witnesses in the two demonstrations. This is a construction discrepancy, not evidence of Atlas missing land or a supported repair. All source, registration, date, invalid, seam, nonnumeric and other residue prerequisites remain explicit. Parent1202 repair/prevention obligations stay open.'}],'stages':{'research':'complete','implementation':'implemented','geographic_approval':'not-requested'},'commands':['At exact immutable1208538e0ae9dba868bcf9fffc34301ea825b588 with18original/import bindings and9runtime body pins, run controls.py then run.py --commit 1208538e0ae9dba868bcf9fffc34301ea825b588 --out ABSENT_OWNED_CACHE --input-only, then run the same run.py twice with distinct absent outputs. Actual commands/cwd/PIDs/times/exits are in v.','Run verify.py for full byte/reference readback only; no third original operator or point-query cohort.'],'change_receipts':[{'path':str(p.relative_to(ROOT)),'status':'added'}for p in paths]+[{'path':PREFIX+'evidence-quality.json','status':'added'}]}
    (HERE/'evidence-quality.json').write_bytes(canonical(manifest));print(json.dumps({'status':'built-not-yet-trusted-admitted','ordinary_descriptors':len(baseline)+len(outputs),'encoded_bytes':budget,'changed_paths':len(outputs)+1,'maximum_decoded_body':max(p.get('uncompressed_bytes',p['bytes'])for p in baseline+outputs),'manifest_sha256':sha(canonical(manifest))}))
if __name__=='__main__':main()

"""Build the bounded evidence receipt from immutable original descriptors and completed vintages."""
import copy, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OWN='research/geography/japan-report-integrity-1342-20261008'
OLD='research/geography/japan-nine-gap-family-source-fitness-20261007'
BASE='d2e4261462ee1d322cec61c29595d78c6f1b2a8e'
ids=sorted(json.loads((ROOT/OLD/'inputs/immutable-scope-and-inputs.json').read_text())['contacts'])
def sha(b): return hashlib.sha256(b).hexdigest()
def file_record(path,role='research-output'):
    raw=(ROOT/path).read_bytes(); row={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes','role':role}
    if path.endswith('.gz'):
        import gzip
        decoded=gzip.decompress(raw); row.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
    return row
old=json.loads((ROOT/OLD/'evidence-quality.json').read_text())
# Pin only the complete inputs actually consumed: all 75 original packet files,
# every indexed world part scanned for global ID uniqueness, hierarchy, and helpers.
import subprocess
paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',BASE,OLD+'/'],text=True).splitlines()
files=[]
for path in paths:
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path])
    files.append({'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
if len(files)!=75 or sum(x['bytes'] for x in files)!=22072824: raise ValueError('Original 75-file roster differs')
idx_raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':data/world-index.json']);idx=json.loads(idx_raw)
extra_paths=['data/world-index.json']+['data/'+p for p in idx['parts']]+['data/hierarchy.json','scripts/evidence/immutable.py']
for path in extra_paths:
    raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path]);files.append({'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
by={x['path']:x for x in files}
extra={
 OLD+'/inputs/immutable-scope-and-inputs.json':(OLD+'/inputs/immutable-scope-and-inputs.json','61069cc6d7727238c552c4f25de9cfa1e7fec7608dc74bcb84605de1620e6414'),
 OLD+'/inputs/existing-physical-row-scope.json':(OLD+'/inputs/existing-physical-row-scope.json','70c424d2ccd38442dceb4f585da08cc6bb4dd8e88d8af5bb849fc192120a6518'),
 OLD+'/results/source-overlays.json':(OLD+'/results/source-overlays.json','2c326ee027c6b4f5ea196e39daca657b493a51f9cf7834bee46a4ca7a9973804'),
 OLD+'/results/source-fitness-table.json':(OLD+'/results/source-fitness-table.json','72ce7765076eb94f195de4e3f80cd521528c12e14c63ffc92c040e4ab2d5484d'),
 OLD+'/methods/build_source_fitness_table.py':(OLD+'/methods/build_source_fitness_table.py','1c867bd02cc1e42207ac0a7cddaf7b320be1b8eda292b7e4f61189c5a3c2535a'),
 OLD+'/inputs/runtime-freeze.json':(OLD+'/inputs/runtime-freeze.json','547fb73c9e70b2033ad810d88a8a4125c14a88f33718684ff36421d4550f04b1'),
 'audited_world_index':('data/world-index.json','a62d4a74f0f969e228dfcdeb2797bb689ce9836c2498cadd31ed622ad2c38c03'),
 'scoped_part_11':('data/geography/part-11.json','d1b2fb15c9427497de740eb33a529ef382b58cb319028f2aa38f5878de4c9b02'),
 'scoped_part_12':('data/geography/part-12.json','24b44617b0164913f598c94c2c1b36e1a2321f0456644cc20e7f2856955b03f7'),
 'report_immutable_helper':('scripts/evidence/immutable.py','a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46'),
 'report_hierarchy_snapshot':('data/hierarchy.json','568301690ef231a85856666b57876a5efe8d8c7c6e671a56d81307b2dc28b80b')}
for key,(path,digest) in extra.items():
    if path not in by or by[path]['sha256']!=digest: raise ValueError('Unexpected/absent baseline file: '+path)
subject_files={identity:[] for identity in ids}
for part in idx['parts']:
    path='data/'+part; raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path])
    for identity in ids:
        if identity.encode() in raw: subject_files[identity].append(path)
for identity,hit in subject_files.items():
    if len(hit)!=1: raise ValueError('Contact identity not unique in complete index: '+identity)
    subject_files[identity]=hit[0]
m={'version':1,'issue':1496,'lane':'geography','worker_id':'01a10947-7d6e-7ba2-98a1-a9f91dedabfc','subject_ids':ids,'subject_ids_sha256':sha(json.dumps(ids,ensure_ascii=False,separators=(',',':')).encode()),'baseline':{'commit':BASE,'files':files,'pins':{k:v[1] for k,v in extra.items()},'pin_files':{k:v[0] for k,v in extra.items()},'subject_files':subject_files}}
m['sources']=[
 {'id':'mlit-n03-2017','url':'https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2017/N03-170101_GML.zip','role':'Nationwide Japanese administrative/coastline source; used here only through the complete retained PR #1342 overlay report.','vintage':'N03 v2.3, 2017-01-01 reference','retrieved_at':'2026-10-07T06:54:39Z','license':{'status':'redistributable','terms':'Prior packet captured the product-specific 2017 commercial-use indication and legacy terms allowing attributed copying/redistribution subject to stated limitations; no broader present-day or underlying third-party rights determination.'},'retention':'restoration-only','verification':'unverified','temporal_status':'reference','restoration':'The original nationwide ZIP is 242211059 bytes; retrieve from the official URL and verify SHA256 a649b4099c1b0df80a6fb9ed087b594ed75ae9a92e9511cecdb6463d1480c6fb before native-source reanalysis. This repair consumes the pinned retained overlay report instead.','limit':'Native source archive exceeds the file cap and was not freshly read/recomputed; results are authenticated as retained report values only.'},
 {'id':'geoboundaries-jpn-adm2-products','url':'https://github.com/wmgeolab/geoBoundaries/tree/9469f09/releaseData/gbOpen/JPN/ADM2','role':'Current Atlas identity/geometry records and the prior packet source comparison context; no new native geoBoundaries measurements here.','vintage':'2017 metadata label; source update 2023-01-19 and build 2023-12-12 in prior packet','retrieved_at':'2026-10-06T23:40:00Z','license':{'status':'redistributable','terms':'Prior packet retains attribution/per-feature citations and source license metadata; this repair does not redistribute a new source copy.'},'retention':'restoration-only','verification':'unverified','temporal_status':'reference','restoration':'Use the complete retained source products, pointers and citations in the original Japan source-fitness packet.','limit':'Metadata year does not prove effective geometry date, positional accuracy or legal authority.'}]
m['outputs']=[]
for path in [OWN+'/README.md',OWN+'/methods/reconcile_source_fitness_table.py',OWN+'/methods/build_evidence_quality.py',OWN+'/tests/test_reconcile.py',OWN+'/receipts/two-run-equality.json',OWN+'/receipts/run-seven-eight-preliminary-equality.json',OWN+'/receipts/final-two-run-equality.json',OWN+'/receipts/superseded-vintages.json',OWN+'/receipts/late-failure.json',OWN+'/receipts/late-failure-stderr.txt',OWN+'/receipts/late-failure-final.json',OWN+'/receipts/late-failure-final-stderr.txt',OWN+'/receipts/late-failure-pinned-helper.json',OWN+'/receipts/late-failure-pinned-helper-stderr.txt',OWN+'/vintages/superseded-history.json.gz']:
    if (ROOT/path).is_file(): m['outputs'].append(file_record(path))
for vintage in ('run-nine-20261008','run-ten-20261008'):
    d=ROOT/OWN/'vintages'/vintage
    if d.exists():
        for name in sorted(x.name for x in d.iterdir() if x.is_file()): m['outputs'].append(file_record(OWN+'/vintages/'+vintage+'/'+name))
source_hash='2c326ee027c6b4f5ea196e39daca657b493a51f9cf7834bee46a4ca7a9973804'
validation=json.loads((ROOT/OWN/'vintages/run-nine-20261008/validation.json').read_text())
m['methods']=[{'id':'pinned-report-transfer','kind':'geography','description':'Authenticate original packet/scope/target geometry and complete retained overlay roster, then bind every MLIT component area by source code, record ordinal/number, component identity and intersection geometry hash. No native-source geometry recalculation.','software':'Python 3.7.3 runtime in this workspace; standard library JSON/hashlib/subprocess and baseline-pinned immutable.py; report-level assertions only.','units':'Exact retained source values in JGD2011 geographic square degrees; not square metres. Identity/count checks are counts, not geographic truth.','axis_order':'longitude-latitude','crs':'MLIT retained product EPSG:6668 JGD2011 geographic; no coordinate operation executed.','area_method':'Transfer of retained overlay intersection_area_jgd2011_degrees2 by exact source/target identity; no area recomputation.','distance_method':'Not calculated.'}]
scope_hash='61069cc6d7727238c552c4f25de9cfa1e7fec7608dc74bcb84605de1620e6414'
vals=[('mlit_candidate_area_records',37,'records',source_hash),('components',28,'components',scope_hash),('families',9,'families',scope_hash),('current_contacts',21,'contacts',scope_hash),('mlit_candidate_area_min',validation['transfer']['min'],'square degrees',source_hash),('mlit_candidate_area_max',validation['transfer']['max'],'square degrees',source_hash)]
m['metrics']=[{'id':i,'value':v,'unit':u,'vintage':'baseline','input_sha256':ih,'evaluation_commit':BASE} for i,v,u,ih in vals]
m['summaries']=[{'metric_id':i,'value':v,'unit':u,'text':{'mlit_candidate_area_records':'All retained candidate MLIT area rows transferred after exact identity binding.','components':'Complete detector-component scope.','families':'Complete source-fitness family scope.','current_contacts':'Complete current Atlas ADM2 contact scope.','mlit_candidate_area_min':'Smallest retained positive angular area, not a physical-area measurement.','mlit_candidate_area_max':'Largest retained positive angular area, not a physical-area measurement.'}[i]} for i,v,u,ih in vals]
m['conclusions']=[
 {'text':'The prior table drops the complete retained MLIT angular area field on all 37 candidate intersections; the new table copies the corresponding source report values while preserving the other table fields.','status':'supported','source_ids':['mlit-n03-2017']},
 {'text':'The reported areas are in square degrees in a JGD2011 geographic CRS and must not be interpreted as square metres.','status':'supported','source_ids':['mlit-n03-2017']},
 {'text':'The retained MLIT measurements have not been freshly authenticated against the oversized native source archive in this repair.','status':'unresolved','source_ids':['mlit-n03-2017']},
 {'text':'Administrative intersections do not establish physical classification, cause, legal ownership, territorial approval or permission to publish/import geometry.','status':'unresolved','source_ids':['mlit-n03-2017','geoboundaries-jpn-adm2-products']}]
m['stages']={'research':'complete','implementation':'proposed','geographic_approval':'unapproved'}
m['commands']=['python3 research/geography/japan-report-integrity-1342-20261008/methods/reconcile_source_fitness_table.py --vintage run-nine-20261008','python3 research/geography/japan-report-integrity-1342-20261008/methods/reconcile_source_fitness_table.py --vintage run-ten-20261008','python3 -m unittest discover -s research/geography/japan-report-integrity-1342-20261008/tests -v','node scripts/evidence-quality.mjs research/geography/japan-report-integrity-1342-20261008/evidence-quality.json']
# Keep the large reviewed whole-file inventories compact: one complete descriptor per line.
files=m['baseline']['files']; outputs=m['outputs']
compact=copy.deepcopy(m); compact['baseline']['files']='__COMPACT_BASELINE_FILES__'; compact['outputs']='__COMPACT_OUTPUTS__'
rendered=json.dumps(compact,indent=2,ensure_ascii=False)
def block(rows,indent):
    pad=' '*indent
    return '[\n'+',\n'.join(pad+json.dumps(row,ensure_ascii=False,separators=(',',':')) for row in rows)+'\n'+(' '*(indent-2))+']'
rendered=rendered.replace('"__COMPACT_BASELINE_FILES__"',block(files,6)).replace('"__COMPACT_OUTPUTS__"',block(outputs,4))
(ROOT/OWN/'evidence-quality.json').write_bytes((rendered+'\n').encode())
print('wrote',len(files),'baseline files',len(outputs),'outputs')

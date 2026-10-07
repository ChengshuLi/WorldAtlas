"""Mechanical evidence manifest for original custody; no scientific data generation."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

O='coordination/engineering/global-physical-sources-20261006';R=Path.cwd();B='9ec87025b8d7355a893924fb26c8152a205f0be2'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def desc(path,raw):
 row={'path':path,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'}
 if path.endswith('.gz'):
  decoded=gzip.decompress(raw);row.update(uncompressed_bytes=len(decoded),uncompressed_sha256=sha(decoded))
 return row
pins={
 'audited_successor_report':('coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json','3d95a15d3797943290997c9a16fede48e6eb6e0941b0071a5fcd410375c49d46'),
 'current_component_delta':('coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz','21ad3c832ef294cae76d5e6603e61313fc2890a1a5653667caef8665374de460'),
 'existing_lossless_codec':('scripts/evidence/immutable.py','b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd')}
base=[]
for name,(path,pin) in pins.items():
 raw=subprocess.check_output(['git','show',B+':'+path]);assert sha(raw)==pin;base.append(desc(path,raw))
cat=json.loads((R/O/'catalogue.json').read_bytes());source_paths={p['path'] for p in cat['parts']}
files=sorted(p for p in (R/O).rglob('*') if p.is_file() and p.name!='evidence-quality.json')
outputs=[dict(desc(p.relative_to(R).as_posix(),p.read_bytes()),role='evidence') for p in files if p.relative_to(R).as_posix() not in source_paths]
report=json.loads((R/O/'run-one/report.json').read_bytes());reportdesc=next(p for p in outputs if p['path']==O+'/run-one/report.json')
metrics=[];bindings=[]
for identity,key,unit in [('native-records','records','records'),('native-coordinate-pairs','coordinate_pairs','pairs'),('archive-members','archive_members','members'),('original-container-unknowns','container_unknowns','records'),('unclosed-original-records','unclosed','records')]:
 metrics.append(dict(id=identity,value=report['counts'][key],unit=unit,vintage='archived',input_sha256=reportdesc['sha256'],evaluation_commit='f778478cc6f4995b0e603dafb8560fce5436ab92'))
 bindings.append(dict(metric_id=identity,path=reportdesc['path'],json_pointer='/counts/'+key))
manifest={
 'version':1,'issue':1261,'lane':'engineering','worker_id':'01a112b0-1bc7-7343-8411-07b91825d3f9','subject_ids':[],'subject_ids_sha256':sha(b'[]'),
 'baseline':{'commit':B,'files':base,'pins':{k:v[1] for k,v in pins.items()},'pin_files':{k:v[0] for k,v in pins.items()}},
 'sources':[{'id':'gshhg-2.3.7-original-binary','url':cat['original_url'],'role':'Complete original18-member binary ZIP; full gshhs_f.b native nested polygon operand, complete other original members retained without political/source approval.','vintage':'Distributed2.3.7 archive,15June2017; older underlyingWVS/WDBII dates and modern accuracy remain uncertain.','retrieved_at':'2026-10-07T00:47:46.835462Z to00:48:05.475694Z; full HTTP acquisition receipt retained.','license':{'status':'redistributable','terms':'Exact distributed LICENSE.TXT grants use/copy/distribution with notices and states LGPLv3 or later; historical README says v3 or earlier. Both exact originals and COPYING.LESSERv3 retained, no conflicting wording silently resolved. LICENSE references COPYINGv3 absent from the actualZIP; no original member invented.'},'retention':'retained','verification':'unverified','temporal_status':'unknown','limit':'Source physical truth/current water/registration/effective dates/political authority not verified; original native-byte custody only.','files':[dict(p,role='original-source') for p in cat['parts']]}],
 'outputs':outputs,'methods':[{'id':'original-gshhg-custody','kind':'generator','helper_version':'worldatlas-evidence-preparation-v1','description':'Authenticate complete ordinary original ZIP fragments, every original whole member and every original native record/coordinate-byte identity; retain exact header/container/ancestor/seam flags without geometry transformations. Complete two immutable executions and direct whole-source row readback.','software':'Python3.12.14; existing immutable.py wholeSHA b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd; nativebig-endian int32, ZIP CRC/hash validation.','units':'exact bytes, native records and integer microdegree coordinates; no area/distance/geographic validity measurement.'}],
 'validation':[dict(method_id='original-gshhg-custody',kind=kind,outcome='passed',evidence_path=O+'/'+filename) for kind,filename in [('positive-control','positive-control.json'),('negative-control','negative-control.json'),('reproducibility','reproducibility.json')]],
 'metrics':metrics,'metric_bindings':bindings,'summaries':[],'conclusions':[{'text':'Complete original byte custody and native record inventory retained; global physical comparison remains the secondPR on1261, with no physical/political approval.','status':'unresolved','source_ids':['gshhg-2.3.7-original-binary']}],
 'stages':{'research':'partial','implementation':'implemented','geographic_approval':'not-requested'},
 'commands':['python -B '+O+'/custody.py --repo . --commit f778478cc6f4995b0e603dafb8560fce5436ab92 --output .cache/gshhg-new-run','python -B '+O+'/controls.py --output .cache/gshhg-new-controls.json','python -B '+O+'/verify.py --repo . --output .cache/gshhg-new-readback.json'],
 'change_receipts':[dict(path=p.relative_to(R).as_posix(),status='added') for p in files]+[dict(path=O+'/evidence-quality.json',status='added')]}
(R/O/'evidence-quality.json').write_bytes((json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n').encode())
print('Descriptors',len(base)+len(cat['parts'])+len(outputs),'declared bytes',sum(x['bytes'] for x in base+cat['parts']+outputs),'changes',len(files)+1)

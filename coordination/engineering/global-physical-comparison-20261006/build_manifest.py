"""Mechanical delivery receipt; no polygon or scientific generation."""
import gzip,hashlib,json,pathlib,subprocess
R=pathlib.Path.cwd();O='coordination/engineering/global-physical-comparison-20261006';HERE=R/O
B='f8f99612e4d83d561b370189a1969c3e4301a1e3';SCI='104091cfecd9c83a53f3e6e62f95b0a0c8074351'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()
def desc(path,body,compressed=False):
 d=dict(path=path,bytes=len(body),sha256=sha(body),hash_kind='file-bytes')
 if compressed or path.endswith('.gz'):
  raw=gzip.decompress(body);d.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
 assert d['bytes']<=33554432 and d.get('uncompressed_bytes',0)<=33554432
 return d
config=json.loads((HERE/'input-config.json').read_bytes());inputs=config['inputs']
source_kinds={'archive_part','source_terms','source_catalogue'}
base=[];source=[]
for entry in inputs:
 body=subprocess.check_output(['git','show',B+':'+entry['path']]);d=desc(entry['path'],body,'uncompressed_bytes'in entry)
 assert all(d.get(k)==entry[k] for k in ('bytes','sha256','uncompressed_bytes','uncompressed_sha256')if k in entry)
 (source if entry['kind']in source_kinds else base).append(d)
primary=[]
for entry in config['primary_documentation']:
 path=O+'/'+entry['path'];body=(R/path).read_bytes();d=desc(path,body)
 assert d['sha256']==entry['sha256'] and d['bytes']==entry['bytes'];primary.append(d)
source_paths={d['path']for d in source+primary}
files=sorted(p for p in HERE.rglob('*')if p.is_file() and '__pycache__'not in p.parts and p.name!='evidence-quality.json')
outputs=[dict(desc(p.relative_to(R).as_posix(),p.read_bytes()),role='evidence')for p in files if p.relative_to(R).as_posix()not in source_paths]
report_path=O+'/results/report.json';report=json.loads((R/report_path).read_bytes());report_desc=next(d for d in outputs if d['path']==report_path)
metrics=[];bindings=[]
values=[('complete-components',report['component_count'],'components','/component_count'),('original-native-records',report['source_record_count'],'records','/source_record_count')]
values +=[(key,count,'components','/statuses/'+key)for key,count in report['statuses'].items()]
for identity,value,unit,pointer in values:
 metrics.append(dict(id=identity,value=value,unit=unit,vintage='archived',input_sha256=report_desc['sha256'],evaluation_commit=SCI))
 bindings.append(dict(metric_id=identity,path=report_path,json_pointer=pointer))
source_rows=[dict(id='gshhg-2.3.7-original-binary',url='https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-bin-2.3.7.zip',role='Complete original native nested polygon operands and exact original terms, reused from actually merged PR1265; all188612 records consumed.',vintage='Distributed2.3.7,15June2017; older underlying WVS/WDBII observation dates unresolved.',retrieved_at='2026-10-07T00:47:46.835462Z to00:48:05.475694Z; reused unchanged from f8f99612e4d83d561b370189a1969c3e4301a1e3.',license=dict(status='redistributable',terms='Exact original LICENSE.TXT grants distribution with notices and states LGPLv3 or later; README says v3 or earlier. Original conflict and absence of original COPYINGv3 preserved; no source terms silently resolved.'),retention='retained',verification='unverified',temporal_status='unknown',limit='Physical truth, observation dates, resolution, known shoreline registration, missing river widths, political authority and historical applicability remain unverified; native invalid Maine record2380 and source container/frame uncertainty retained.',files=[dict(d,role='original-source')for d in source]),dict(id='gmt-6.5-native-reader-primary-context',url='https://github.com/GenericMappingTools/gmt/tree/6da8ee2db90cb8e5dc0f2b6e80c875c4fd38e433/src/gshhg',role='Separately dated original native longitude/container header interpretation and exact license context; not replacement GSHHG original members.',vintage='Immutable GMT6.5 tag commit6da8ee2db90cb8e5dc0f2b6e80c875c4fd38e433.',retrieved_at='2026-10-07; actual per-body HTTP/UTC records in primary/receipt.json.',license=dict(status='redistributable',terms='Exact GMT LICENSE.TXT, COPYINGv3 and COPYING.LESSERv3 retained with notices; source/license bodies are separately dated from original GSHHG archive.'),retention='retained',verification='unverified',temporal_status='unknown',limit='Native-reader interpretation context does not approve physical water, effective dates, political ownership or source fitness.',files=[dict(d,role='original-source')for d in primary])]
methods=[dict(id='complete-nested-source-comparison',kind='measurement',description='All95173 whole components, complete original native inputs, explicit GMT longitude frames, whole nestedL1-L4 partitions and witnesses; no political assignment or absent-water=dryland. Mixed collections preserve complete polygon and contact parts; exact covers reference authenticated whole pointsets. Original invalid and contradictory/container/numerical uncertainties remain unknown.',software='Python3.12.14; NumPy2.3.5; Shapely2.1.2; GEOS3.13.1; exact frozen104 code/runtime and complete dependency closure retained.',axis_order='longitude-latitude',crs='EPSG:4326',area_method='WGS84 straight-source-edge ellipsoidal integral',distance_method='WGS84 inverse geodesic',units='degree coordinates, planar degree-squared diagnostics, WGS84 literal-edge16point quadrature square-metres; source-relative support only.'),dict(id='five-field-lossless-delivery',kind='generator',helper_version='worldatlas-evidence-preparation-v1',description='Only five duplicated metadata/hash fields restored from complete ordinary current records and original native byte positions; each full decoded and deterministic-gzip original shard restores exact size/SHA twice. No geometry operations.',software='Separately committed eceb3ca2 adapter with unchanged scientific104 dependencies and existing immutable.py lossless codec.',units='whole bytes, source/native record identities, SHA256; no new physical measurement.')]
validation=[]
for method in methods:
 for kind in ['positive-control','negative-control']+(['reproducibility']if method['kind']=='generator'else[]):
  filename=method['id']+'-'+kind+'.json'
  validation.append(dict(method_id=method['id'],kind=kind,outcome='passed',evidence_path=O+'/verification/'+filename))
pins={};pin_files={}
for name,kind in [('current_component_delta','components_delta'),('audited_successor_report','audit_report'),('existing_reconstructor','reconstruction_code')]:
 row=next(d for d in inputs if d['kind']==kind);pins[name]=row['sha256'];pin_files[name]=row['path']
codec_path='scripts/evidence/immutable.py';codec_raw=subprocess.check_output(['git','show',B+':'+codec_path]);codec_desc=desc(codec_path,codec_raw);assert codec_desc['sha256']=='b7ff607b7774595788396e94f08fc29d750e4032624eb93732a5735c1ddcf7fd';base.append(codec_desc);pins['existing_lossless_codec']=codec_desc['sha256'];pin_files['existing_lossless_codec']=codec_path
manifest=dict(version=1,issue=1261,lane='engineering',worker_id='01a112b0-1bc7-7343-8411-07b91825d3f9',subject_ids=[],subject_ids_sha256=sha(b'[]'),baseline=dict(commit=B,files=base,pins=pins,pin_files=pin_files),sources=source_rows,outputs=outputs,methods=methods,validation=validation,metrics=metrics,metric_bindings=bindings,summaries=[],conclusions=[dict(text='Complete frozen worldwide source-relative comparisons and original input/output closure retained. All physical source-fitness/date/precision/authority conclusions remain unresolved; no repair or political assignment approved.',status='unresolved',source_ids=[s['id']for s in source_rows])],stages=dict(research='partial',implementation='implemented',geographic_approval='not-requested'),commands=['python -B '+O+'/run.py --execution '+SCI+' --out ABSOLUTE_FRESH_OWNED_CACHE_DIR --receipt ABSOLUTE_FRESH_OWNED_CACHE_RECEIPT --log ABSOLUTE_FRESH_OWNED_CACHE_LOG','python -B '+O+'/transport.py --transport-commit eceb3ca202e95d12a0c837ae24e621add59e0cc4 --source ABSOLUTE_COMPLETE_SCIENCE --out ABSOLUTE_FRESH_OWNED_CACHE_DIR --receipt ABSOLUTE_FRESH_OWNED_CACHE_RECEIPT'],change_receipts=[dict(path=p.relative_to(R).as_posix(),status='added')for p in files]+[dict(path=O+'/evidence-quality.json',status='added')])
(HERE/'evidence-quality.json').write_bytes(canonical(manifest))
all_desc=base+source+primary+outputs
assert len(all_desc)<=512 and sum(d['bytes']for d in all_desc)<=268435456
print(json.dumps(dict(descriptors=len(all_desc),encoded_bytes=sum(d['bytes']for d in all_desc),changed_files=len(files)+1,metrics=len(metrics))))

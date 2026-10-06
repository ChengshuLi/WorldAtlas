#!/usr/bin/env python3
"""Audit independent EKATTE member vintages and reproduce prior outputs locally only."""
from __future__ import annotations
import argparse, contextlib, datetime as dt, hashlib, io, json, os, pathlib, re, shutil, subprocess, zipfile

ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=pathlib.Path(__file__).resolve().parent
PRIOR=ROOT/'data/regional-review/regional-review-aa0be1f8b58caec6'
ISSUE_SNAPSHOT=OWN/'source/issue-snapshot.json'
CLAIM_RECEIPT=OWN/'source/claim-receipt.json'
SOURCE_COMMIT='90f04d30cf773b5be538bc3d85d4d9051768deef'
BASELINE_COMMIT='9593d2f46953233db3614622ffe54da1336925fd'
ARCHIVE_PATH=PRIOR/'source/NSI-EKATTE-export-20261005.zip'
EXPECTED_ARCHIVE='6d848e467493f4d6ec6c1c9081bf51266ad888dc8f232c3d1fd2b0a265ace77d'
EXPECTED_PRODUCTS={
 'bulgaria-municipality-crosswalk.csv':(94358,'8e16f596cc7805d8841a77d40ef202efe7c34f60acbaa5d6c66d19cd0a61a6c9'),
 'bulgaria-full-source-roster.csv':(61666,'9bf598322c17f5cbf0be86e859bb126533e6e8685f0748df047c391ed459eb94'),
 'bulgaria-audit-summary.json':(2539,'a915b4478bcd822bae51576c16c0a65f5a136157c6a1ad6d1a5369b21e34a928'),
}
DATE_FIELD='Данните са актуални към'
EXPORT_FIELD='Дата и час на изготвяне на справката'

def sha(raw:bytes)->str: return hashlib.sha256(raw).hexdigest()
def git_blob(commit,path): return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
def parse_member_metadata(member:str,raw:bytes)->dict:
 rows=json.loads(raw)
 if not isinstance(rows,list) or not rows or not isinstance(rows[-1],dict): raise ValueError(f'{member}: final metadata row missing')
 row=rows[-1]; date_raw=row.get(DATE_FIELD); export_raw=row.get(EXPORT_FIELD)
 date_iso=dt.datetime.strptime(date_raw,'%d/%m/%Y').date().isoformat() if date_raw else None
 export=dt.datetime.strptime(export_raw,'%d/%m/%Y %H:%M') if export_raw else None
 return {'member':member,'record_rows_excluding_metadata':len(rows)-1,
  'data_reference_raw':date_raw,'data_reference_date':date_iso,
  'export_timestamp_raw':export_raw,'export_date':export.date().isoformat() if export else None,
  'export_time':export.strftime('%H:%M') if export else None,
  'timezone':'unspecified by archive','data_reference_status':'known' if date_iso else 'unknown',
  'export_timestamp_status':'known' if export else 'unknown'}
def execute_original_twice():
 """Run exact original source twice, redirecting only three products to ignored scratch."""
 script=PRIOR/'reproduce.py'; code=script.read_text(encoding='utf-8')
 scratch=OWN/'.local-only'
 if scratch.exists(): raise RuntimeError('local scratch already exists; preserve and inspect it before rerunning')
 scratch.mkdir()
 physical={
  'OUT = PACKET / "validation/bulgaria-municipality-crosswalk.csv"':f'OUT = Path({str(scratch/"bulgaria-municipality-crosswalk.csv")!r})',
  'FULL_OUT = PACKET / "validation/bulgaria-full-source-roster.csv"':f'FULL_OUT = Path({str(scratch/"bulgaria-full-source-roster.csv")!r})',
  'SUMMARY_OUT = PACKET / "validation/bulgaria-audit-summary.json"':f'SUMMARY_OUT = Path({str(scratch/"bulgaria-audit-summary.json")!r})',
 }
 for old,new in physical.items():
  if old not in code: raise RuntimeError('original output assignment changed: '+old)
  code=code.replace(old,new,1)
 # Keep the historically published logical path strings while directing bytes into private scratch.
 code=code.replace('str(FULL_OUT.relative_to(ROOT))',repr('data/regional-review/regional-review-aa0be1f8b58caec6/validation/bulgaria-full-source-roster.csv'),1)
 code=code.replace('str(OUT.relative_to(ROOT))',repr('data/regional-review/regional-review-aa0be1f8b58caec6/validation/bulgaria-municipality-crosswalk.csv'),1)
 first=None; records=[]
 try:
  for run in (1,2):
   for name in EXPECTED_PRODUCTS:
    target=scratch/name
    if target.exists(): target.unlink()
   with contextlib.redirect_stdout(io.StringIO()): exec(compile(code,str(script),'exec'),{'__name__':'__main__','__file__':str(script)})
   current={}
   for name,(size,want) in EXPECTED_PRODUCTS.items():
    raw=(scratch/name).read_bytes(); got=sha(raw)
    if len(raw)!=size or got!=want: raise RuntimeError(f'{name} differs from retained historical output: {len(raw)} {got}')
    current[name]={'bytes':len(raw),'sha256':got}
   records.append(current)
   if run==1: first=current
   elif current!=first: raise RuntimeError('original products differ between fresh runs')
  return {'runs':2,'equal':records[0]==records[1],'historical_hash_match':True,'products':records[0],
   'output_redirection':'Only the three exact output paths were redirected; logical path strings were preserved. Original files were never opened for writing.',
   'row_level_outputs':'written only to ignored local scratch during reproduction, then removed'}
 finally:
  if scratch.exists(): shutil.rmtree(scratch)
def verify_existing_output_control():
 sentinel_dir=OWN/'.output-exists-control'
 if sentinel_dir.exists(): raise RuntimeError('output-control scratch already exists; preserve and inspect it')
 sentinel_dir.mkdir(); marker=sentinel_dir/'preserve.txt'; marker.write_text('leave unchanged\n',encoding='utf-8'); before=sha(marker.read_bytes())
 try:
  run=subprocess.run([os.sys.executable,str(pathlib.Path(__file__).resolve()),'--output-dir',sentinel_dir.name],cwd=ROOT,capture_output=True,text=True)
  if run.returncode==0 or 'refusing to replace existing evidence output directory' not in run.stderr: raise RuntimeError('pre-existing output control did not refuse the destination')
  if sha(marker.read_bytes())!=before or sorted(p.name for p in sentinel_dir.iterdir())!=['preserve.txt']: raise RuntimeError('pre-existing output control changed sentinel or emitted partial output')
  return {'name':'existing-evidence-output-sentinel','outcome':'passed','exit_code':run.returncode,'existing_files_unchanged':True,'reason':run.stderr.strip()}
 finally:
  shutil.rmtree(sentinel_dir)

def verify():
 issue=json.loads(ISSUE_SNAPSHOT.read_text(encoding='utf-8')); body=issue['body']; marker='<!-- worldatlas-work:v1\n'
 work=json.loads(body.split(marker,1)[1].split('\n-->',1)[0]); eq=work['evidence_quality']; ids=eq['subject_ids']
 if len(ids)!=213 or len(set(ids))!=213: raise ValueError('issue scope must contain exactly 213 unique subjects')
 if work['owned_paths']!=['data/regional-review/bgr-register-vintage-417-erratum/']: raise ValueError('issue owned path changed')
 # All declared pins resolve from the producing merge, without substitution from current main.
 pin_rows=[]
 for spec,want in sorted(eq['pins'].items()):
  commit,path=spec.split(':',1); raw=git_blob(commit,path); got=sha(raw)
  if got!=want: raise ValueError(f'issue pin mismatch: {spec}')
  pin_rows.append({'commit':commit,'path':path,'bytes':len(raw),'sha256':got})
 if len(pin_rows)!=17: raise ValueError('expected the 17 declared baseline/archive inputs')
 issue_scope=json.loads((PRIOR/'source/issue-scope.json').read_text(encoding='utf-8'))
 if set(ids)!=set(issue_scope['member_location_ids']) or len(issue_scope['member_location_ids'])!=213: raise ValueError('new issue subjects differ from preserved #417 roster')
 # Validate archive identity and read every complete ZIP member; decoded payloads stay in memory.
 archive_bytes=ARCHIVE_PATH.read_bytes(); archive_hash=sha(archive_bytes)
 if archive_hash!=EXPECTED_ARCHIVE: raise ValueError('NSI original archive hash mismatch')
 member_rows=[]; decoded={}; total=0
 with zipfile.ZipFile(io.BytesIO(archive_bytes)) as z:
  infos=z.infolist()
  if len(infos)!=12 or len({i.filename for i in infos})!=12: raise ValueError('archive member roster changed')
  for info in infos:
   raw=z.read(info); total+=len(raw)
   if len(raw)>32*1024*1024: raise ValueError('archive member exceeds evidence byte budget')
   decoded[info.filename]=raw
   member_rows.append({'name':info.filename,'compressed_bytes':info.compress_size,'decoded_bytes':len(raw),'sha256':sha(raw)})
 if total!=4712618: raise ValueError(f'complete decoded archive size changed: {total}')
 if not {'ek_obst.json','ek_obl.json'}<=set(decoded): raise ValueError('consumed complete register members are absent')
 municipality=parse_member_metadata('ek_obst.json',decoded['ek_obst.json'])
 district=parse_member_metadata('ek_obl.json',decoded['ek_obl.json'])
 if municipality['record_rows_excluding_metadata']!=265 or district['record_rows_excluding_metadata']!=28: raise ValueError('register row count changed')
 if (municipality['data_reference_date'],district['data_reference_date'])!=('2023-12-12','2015-10-05'): raise ValueError('member-specific reference dates differ from exact archive bytes')
 if municipality['export_date']!='2026-10-05' or district['export_date']!='2026-10-05': raise ValueError('member export date changed')
 # Synthetic separate-member control: a changed date stays attached to its own member.
 synthetic_rows=json.loads(decoded['ek_obl.json']); synthetic_rows[-1][DATE_FIELD]='01/02/2011'
 synthetic_raw=json.dumps(synthetic_rows,ensure_ascii=False,separators=(',',':')).encode('utf-8')
 synthetic=parse_member_metadata('synthetic/ek_obl.json',synthetic_raw)
 if synthetic['data_reference_date']!='2011-02-01' or synthetic['data_reference_date']==municipality['data_reference_date']: raise ValueError('synthetic member date was collapsed')
 missing_rows=json.loads(decoded['ek_obl.json']); missing_rows[-1].pop(DATE_FIELD,None)
 unknown=parse_member_metadata('synthetic/missing-date.json',json.dumps(missing_rows,ensure_ascii=False).encode())
 if unknown['data_reference_status']!='unknown' or unknown['data_reference_date'] is not None: raise ValueError('missing date was not kept unknown')
 original=execute_original_twice()
 output_control=verify_existing_output_control()
 release=json.loads((PRIOR/'evidence-quality.json').read_text())
 # Confirm the previous evidence labels one shared vintage; this erratum only corrects that interpretation.
 source=next(s for s in release['sources'] if s['id']=='nsi-ekatte-current-register')
 findings={'version':1,'issue':1191,'worker_id':json.loads(CLAIM_RECEIPT.read_text())['claim']['worker_id'],
  'baseline_commit':BASELINE_COMMIT,
  'issue_scope':{'count':len(ids),'member_location_ids_sha256':issue_scope['member_location_ids_sha256'],'all_subjects_match_preserved_213_id_roster':True},
  'source_archive':{'path':'data/regional-review/regional-review-aa0be1f8b58caec6/source/NSI-EKATTE-export-20261005.zip','bytes':len(archive_bytes),'sha256':archive_hash,'retrieval_url':'https://www.nsi.bg/nrnm/ekatte/zip/download?files_type=json','landing_page':'https://www.nsi.bg/nrnm/ekatte/index','members_count':len(member_rows),'decoded_bytes_all_members':total},
  'register_members':[municipality,district],
  'previous_manifest_source_vintage':source.get('vintage'),
  'interpretation':'The two complete NSI table members have different data-reference dates; their separate 2026-10-05 export timestamps do not make the reference dates contemporaneous. The retained 2019 geometry-to-register crosswalk is lexical/code evidence against those distinct register-member vintages, not a current legal-parent or polygon proof.',
  'original_reproduction':original,
  'controls':{'positive_actual_member_dates':'passed','synthetic_district_date':{'outcome':'reported-separately','member':synthetic['member'],'data_reference_date':synthetic['data_reference_date'],'fixture_sha256':sha(synthetic_raw)},'missing_member_date':{'outcome':'unknown-not-imputed','member':unknown['member'],'date':None},'outputs_exclusive':'see control-results.json'}}
 archive_manifest={'version':1,'issue':1191,'source_archive_sha256':archive_hash,'member_count':len(member_rows),'decoded_bytes_total':total,'members':member_rows,
  'retention':'Member bytes are read from the already-retained original archive and hashed in memory; no extracted member copies are committed.'}
 return findings,archive_manifest,{'version':1,'issue':1191,'controls':[{'name':'separate-member-date-positive-control','outcome':'passed','actual_dates':['2023-12-12','2015-10-05']},{'name':'synthetic-different-member-date','outcome':'passed','synthetic_date':'2011-02-01','did_not_inherit_municipality_date':True},{'name':'missing-date','outcome':'passed','missing_value_remains_unknown':True},{'name':'two-run-historical-products','outcome':'passed','product_hashes_match_retained_values':True},output_control]},original

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',default='evidence'); args=ap.parse_args()
 rel=pathlib.Path(args.output_dir)
 if rel.is_absolute() or '..' in rel.parts or rel == pathlib.Path('.') or '\\' in args.output_dir: raise SystemExit('output-dir must be a new relative directory inside the owned packet')
 dest=(OWN/rel).resolve()
 if dest.parent != OWN.resolve() and OWN.resolve() not in dest.parents: raise SystemExit('output-dir escapes the owned packet')
 if dest.exists(): raise SystemExit('refusing to replace existing evidence output directory')
 findings,archive_manifest,controls,original=verify()
 try:
  dest.mkdir(exist_ok=False)
  values={'member-vintage-findings.json':findings,'archive-member-manifest.json':archive_manifest,'control-results.json':controls,'reproduction-record.json':{'version':1,'issue':1191,**original}}
  for name,value in values.items():
   with (dest/name).open('x',encoding='utf-8') as f: json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
 except Exception:
  if dest.exists(): shutil.rmtree(dest)
  raise
 print(json.dumps({'evidence_dir':str(dest.relative_to(ROOT)),'members':12,'decoded_bytes':4712618,'scope_ids':213,'register_dates':[x['data_reference_date'] for x in findings['register_members']],'historical_runs':2,'products':original['products']},indent=2))
if __name__=='__main__': main()

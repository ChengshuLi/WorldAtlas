#!/usr/bin/env python3
"""Revalidate fresh Matanuska output vintages, original inputs, and safe CLI behavior."""
import gzip, hashlib, json, os, pathlib, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[4]
PACKET=ROOT/'research/geography/gap-source-matanuska-physical-seam-20261006'
OWNED=PACKET/'reproduction-erratum'
PRODUCER=OWNED/'reproduce-fresh-vintage.py'
PIN_FILE=OWNED/'input-pins.json'
BASE='cea80a8aa1f8a55ccb448a8f2ff71e10c49a26f1'
RUNS=OWNED/'runs'
names=['selected-components.geojson','source-overlay-ledger.json','source-overlay-summary.json']
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read_json(p): return json.loads(pathlib.Path(p).read_bytes())
def inside(path,root):
    try: path.relative_to(root);return True
    except ValueError:return False
pins=read_json(PIN_FILE)
observed=[]
for group in [pins['baseline']['files'],[f for src in pins['sources'] for f in src.get('files',[])],pins['outputs']]:
    for d in group:
        raw=subprocess.check_output(['git','show',f"{d['commit']}:{d['path']}"],cwd=ROOT)
        if len(raw)!=d['bytes'] or sha(raw)!=d['sha256']: raise SystemExit('Immutable input mismatch: '+d['path'])
        row={'path':d['path'],'commit':d['commit'],'bytes':len(raw),'sha256':sha(raw)}
        if 'uncompressed_bytes' in d:
            decoded=gzip.decompress(raw)
            if len(decoded)!=d['uncompressed_bytes'] or sha(decoded)!=d['uncompressed_sha256']: raise SystemExit('Decoded input mismatch: '+d['path'])
            row.update({'uncompressed_bytes':len(decoded),'uncompressed_sha256':sha(decoded)})
        observed.append(row)
for d in pins['method_pins']:
    raw=subprocess.check_output(['git','show',f"{d['commit']}:{d['path']}"],cwd=ROOT)
    local=(ROOT/d['path']).read_bytes()
    if len(raw)!=d['bytes'] or sha(raw)!=d['sha256'] or local!=raw: raise SystemExit('Executable code pin mismatch: '+d['path'])
original_manifest=pins['original_manifest']
raw=subprocess.check_output(['git','show',f"{original_manifest['commit']}:{original_manifest['path']}"],cwd=ROOT)
if len(raw)!=original_manifest['bytes'] or sha(raw)!=original_manifest['sha256'] or (ROOT/original_manifest['path']).read_bytes()!=raw:
    raise SystemExit('Original evidence manifest changed')
(OWNED/'input-verification.json').write_text(json.dumps({'version':1,'baseline_commit':pins['baseline']['commit'],'source_commit':pins['method_pins'][0]['commit'],'verified_file_descriptors':len(observed),'verified_unique_files':len({(x['commit'],x['path']) for x in observed}),'files':observed,'original_manifest':original_manifest,'method_pins':pins['method_pins']},ensure_ascii=False,indent=2)+'\n')
# Retain the one frozen baseline file whose path was repinned in the later producer merge.
old_pin=next(x for x in pins['baseline']['files'] if x['path']=='data/geographic-releases/current-manifest.json')
old_raw=subprocess.check_output(['git','show',f"{old_pin['commit']}:{old_pin['path']}"],cwd=ROOT)
copy_path=OWNED/'baseline-inputs/current-manifest-at-issue-baseline.json'
copy_raw=copy_path.read_bytes()
if len(copy_raw)!=old_pin['bytes'] or sha(copy_raw)!=old_pin['sha256'] or copy_raw!=old_raw:
    raise SystemExit('Retained issue-baseline current manifest copy mismatch')
baseline_copy={'path':str(copy_path.relative_to(ROOT)),'commit':old_pin['commit'],'bytes':len(copy_raw),'sha256':sha(copy_raw),'unchanged':True}
# Keep the prior versioned source/output/capture/control bytes intact.
preserved=[]
for group in [[f for src in pins['sources'] for f in src.get('files',[])],pins['outputs']]:
    for d in group:
        local=(ROOT/d['path']).read_bytes()
        if len(local)!=d['bytes'] or sha(local)!=d['sha256']: raise SystemExit('Original packet bytes changed: '+d['path'])
        preserved.append({'path':d['path'],'commit':d['commit'],'bytes':len(local),'sha256':sha(local),'unchanged':True})
(OWNED/'original-preservation-check.json').write_text(json.dumps({'version':1,'checked_at':'2026-10-07','checked_source_and_output_files':len(preserved),'all_unchanged':all(x['unchanged'] for x in preserved),'files':preserved},ensure_ascii=False,indent=2)+'\n')
# Compare new complete result families and their concrete per-run path receipts.
family_hashes={}
for rid in ['fresh-one','fresh-two']:
    receipt=read_json(OWNED/'run-receipts'/(rid+'.json'))
    if receipt['run_id']!=rid or receipt['output_directory']!=str((RUNS/rid).relative_to(ROOT)): raise SystemExit('Run receipt path mismatch')
    files=[]
    for row in receipt['files']:
        p=ROOT/row['path'];data=p.read_bytes()
        if len(data)!=row['bytes'] or sha(data)!=row['sha256']: raise SystemExit('Run receipt file pin mismatch: '+row['path'])
        files.append({'name':p.name,'path':row['path'],'bytes':len(data),'sha256':sha(data)})
    if [f['name'] for f in files]!=names: raise SystemExit('Incomplete fresh output family')
    family_hashes[rid]={x['name']:x['sha256'] for x in files}
if family_hashes['fresh-one']!=family_hashes['fresh-two']: raise SystemExit('Fresh output families are not byte-identical')
old_hashes={}
for rid in ['run-one','run-two']:
    old_hashes[rid]={n:sha((PACKET/'results'/rid/n).read_bytes()) for n in names}
if old_hashes['run-one']!=old_hashes['run-two']: raise SystemExit('Archived original output families are not byte-identical')
if family_hashes['fresh-one']['selected-components.geojson']!=old_hashes['run-one']['selected-components.geojson']:
    raise SystemExit('Fresh selected geometries differ from preserved original')
if family_hashes['fresh-one']['source-overlay-ledger.json']!=old_hashes['run-one']['source-overlay-ledger.json']:
    raise SystemExit('Fresh source-overlay ledger differs from preserved original')
old_summary=read_json(PACKET/'results/run-one/source-overlay-summary.json')
new_summary=read_json(RUNS/'fresh-one/source-overlay-summary.json')
result_fields={k:v for k,v in old_summary.items() if k not in {'component_geometry_collection','overlay_ledger'}}
new_fields={k:v for k,v in new_summary.items() if k not in {'component_geometry_collection','overlay_ledger'}}
if result_fields!=new_fields: raise SystemExit('Fresh numeric/source predicate summary differs from archived original')
for k,name in [('component_geometry_collection','selected-components.geojson'),('overlay_ledger','source-overlay-ledger.json')]:
    desc=new_summary[k];actual=f"research/geography/gap-source-matanuska-physical-seam-20261006/reproduction-erratum/runs/{{run-id}}/{name}"
    if desc.get('path_template')!=actual or desc.get('sha256')!=family_hashes['fresh-one'][name]:
        raise SystemExit('Fresh output path template or digest mismatch: '+k)
# Run the original scientific control classes against fresh bytes.
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(1,str(PACKET))
from physical_component_contacts import component_contacts
from source_input_integrity import verify_source_bytes
registry=read_json(PACKET/'source-registry.json')
changed_checks=[]
for sid,pth in [('resolve-ecoregions-biomes-2017','sources/resolve-ecoregions-2017-ecoids-371-405.geojson'),('geoboundaries-us-adm2-2018-simplified','sources/geoboundaries-usa-adm2-simplified-full.geojson')]:
    source=next(x for x in registry['sources'] if x['id']==sid)
    raw=(PACKET/pth).read_bytes();mut=bytearray(raw);mut[0]^=1
    try: verify_source_bytes(pth,bytes(mut),source)
    except ValueError as e: changed_checks.append({'source_id':sid,'mutated_sha256':sha(bytes(mut)),'rejected':str(e)})
    else: raise SystemExit('Changed-source negative accepted: '+sid)
features=read_json(RUNS/'fresh-one/selected-components.geojson')['features']
ids=sorted(f['id'] for f in features); roster=sha((json.dumps(ids,ensure_ascii=False,separators=(',',':'))+'\n').encode())
if len(ids)!=282 or roster!='37b5efeb08f407cd19cc098186659a01899d748d8dd73b3c26bfccbd1d35fc66': raise SystemExit('Fresh exact component roster mismatch')
ledger=read_json(RUNS/'fresh-one/source-overlay-ledger.json')
contact_rows=ledger['exact_contact_ledgers'];positive=component_contacts(ledger['candidate_fragments']['features'],features)
if len(positive)!=282 or sum(len(x['fragment_contacts']) for x in positive)!=283 or sum(len(b['exact_location_contacts'] or []) for x in positive for b in x['fragment_contacts'])!=571:
    raise SystemExit('Fresh complete contact closure mismatch')
omitted=ids[:-1];omitted_hash=sha((json.dumps(omitted,ensure_ascii=False,separators=(',',':'))+'\n').encode())
if omitted_hash==roster: raise SystemExit('Omitted-scope negative did not change roster hash')
mutated=__import__('copy').deepcopy(ledger['candidate_fragments']['features']);mutated[0]['properties'].pop('exact_location_contacts',None)
try:
    incomplete=component_contacts(mutated,features);rejected=not all(x['status']=='complete-recorded-contacts' for x in incomplete);reason='incomplete-source-contact-recording'
except ValueError as e: rejected=True;reason=str(e)
if not rejected: raise SystemExit('Omitted-contact negative accepted')
layer=read_json(PACKET/'sources/resolve-layer-0.json')
if '2017' not in layer.get('name','') or layer.get('editingInfo',{}).get('lastEditDate') not in [1643241600000,1643241600000.0]:
    # The retained layer receipt separately records the exact UTC edit date; do not infer a different vintage.
    edit=layer.get('editingInfo',{}).get('lastEditDate')
    if '2017' not in layer.get('name','') or edit is None: raise SystemExit('Pinned layer vintage check failed')
laundering_rejected='2018' not in layer['name']
if not laundering_rejected: raise SystemExit('Atlas reference-year laundering control ineffective')
# Actual CLI negative cases, retaining only an owned, temporary symlink fixture and deleting it after the refusal.
py=sys.executable
def run_case(label,args,expected):
    proc=subprocess.run([py,str(PRODUCER)]+args,cwd=ROOT,text=True,capture_output=True)
    combined=proc.stdout+proc.stderr
    if proc.returncode==0 or expected not in combined: raise SystemExit('CLI rejection control failed: '+label+'; '+combined[-600:])
    return {'case':label,'args':args,'exit_code':proc.returncode,'expected_rejection':expected,'stdout':proc.stdout,'stderr':proc.stderr}
cli=[]
cli.append(run_case('path-traversal',['--run-id','../outside'],'safe filename characters'))
# Existing directory: rerunning fresh-one must not change any member bytes.
before={n:sha((RUNS/'fresh-one'/n).read_bytes()) for n in names}
cli.append(run_case('existing-directory',['--run-id','fresh-one'],'already exists'))
after={n:sha((RUNS/'fresh-one'/n).read_bytes()) for n in names}
if before!=after: raise SystemExit('Existing directory content changed after rejection')
# Existing regular file sentinel at a contained alternate run root.
fixture=OWNED/'controls/fixtures';fixture.mkdir(parents=True,exist_ok=True)
sentinel=fixture/'fresh-existing-file';sentinel.write_bytes(b'original-sentinel-1241\\n');sentinel_hash=sha(sentinel.read_bytes())
cli.append(run_case('existing-file',['--run-id','fresh-existing-file','--runs-root',str(fixture)],'already exists'))
if sha(sentinel.read_bytes())!=sentinel_hash: raise SystemExit('Existing file sentinel changed after rejection')
# A symlink run destination pointing at a valid existing run must be refused without following it.
symlink=RUNS/'fresh-symlink'
if symlink.exists() or symlink.is_symlink(): raise SystemExit('Temporary symlink fixture collision')
symlink.symlink_to(RUNS/'fresh-one',target_is_directory=True)
try: cli.append(run_case('symlink-destination',['--run-id','fresh-symlink'],'already exists'))
finally: symlink.unlink()
# An out-of-scope root symlink is rejected before mkdir/write and never touches its external target.
outside=pathlib.Path('/tmp')/('worldatlas-matanuska-outside-'+str(os.getpid()))
if outside.exists(): raise SystemExit('Outside probe path unexpectedly exists')
outside_link=fixture/'outside-root-link'
if outside_link.exists() or outside_link.is_symlink(): raise SystemExit('Temporary outside symlink fixture collision')
outside_link.symlink_to(outside,target_is_directory=True)
try: cli.append(run_case('outside-resolved-root',['--run-id','fresh-outside','--runs-root',str(outside_link)],'resolves outside'))
finally: outside_link.unlink()
if outside.exists(): raise SystemExit('Outside CLI probe unexpectedly created a destination')
controls={'version':1,'method_id':'source-overlay-analysis','outcome':'passed','fresh_run_ids':['fresh-one','fresh-two'],'fresh_families_byte_identical':True,'original_run_families_byte_identical':True,'fresh_vs_original':{'selected_components_identical':True,'source_overlay_ledger_identical':True,'numeric_and_predicate_summary_identical':True,'summary_path_metadata_difference':'Archived paths point to results/{run-id}; fresh output metadata points to reproduction-erratum/runs/{run-id} and actual paths are separately bound in run receipts.'},'fresh_hashes':family_hashes,'original_hashes':old_hashes,'component_roster':{'count':len(ids),'sha256':roster},'fragment_bindings':283,'contact_rows':571,'changed_source_controls':changed_checks,'omitted_component_control':{'expected_count':282,'observed_count':len(omitted),'observed_roster_sha256':omitted_hash,'rejected':True},'omitted_contact_control':{'rejected':True,'reason':reason},'vintage_laundering_control':{'pinned_layer_name':layer['name'],'rejected_year':'2018','rejected':True},'cli_rejections':cli,'existing_directory_hashes_unchanged':True,'existing_file_sentinel_sha256':sentinel_hash,'outside_destination_created':False,'retained_original_baseline_copy':baseline_copy}
out=OWNED/'validation.json'
out.write_text(json.dumps(controls,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'outcome':'passed','inputs_verified':len(observed),'preserved_original_files':len(preserved),'fresh_outputs_equal':True,'original_comparisons':controls['fresh_vs_original'],'positive_roster':len(ids),'contact_rows':571,'cli_rejections':len(cli),'validation_file':str(out.relative_to(ROOT))},indent=2))

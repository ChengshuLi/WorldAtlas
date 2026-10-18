import copy,gzip,hashlib,json,pathlib,subprocess,sys,tempfile,os
# Usage: python -I -S -B verify-reconstruction.py PACKET_DIRECTORY FIXTURE_ROOT LOCATORS_JSON
P=pathlib.Path(sys.argv[1]);F=pathlib.Path(sys.argv[2]);manifest=json.loads(pathlib.Path(sys.argv[3]).read_text())
script=P/'held-row-diagnostic-repro.mjs';packetfile=P/'held-row-exception-packet.json';packet=json.loads(packetfile.read_text());old=json.loads((P/'centre-contact-results.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
for pin in manifest['source_and_evidence_inputs']:
 f=F/'payloads'/pathlib.Path(pin['path']).name if 'family' in pin else F/'evidence'/pin['country']/'source-evidence.json'
 b=f.read_bytes();assert len(b)==pin['bytes'] and sha(b)==pin['sha256'];oid=pin.get('git_blob_oid',pin.get('blob'));assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
 if 'decoded_sha256' in pin:assert sha(gzip.decompress(b))==pin['decoded_sha256']
assert sha(script.read_bytes())==packet['reproduction_artifact']['sha256']
def run(p=packetfile,f=F,h=F/'native-grid.mjs',lat=F/'native-row-latitudes.f64le'):
 env=dict(os.environ);env.pop('NODE_OPTIONS',None);env.pop('NODE_PATH',None)
 return subprocess.run(['node',str(script),'--packet',str(p),'--fixture-root',str(f),'--helper',str(h),'--latitudes',str(lat)],env=env,text=True,capture_output=True)
def normalized(doc):
 result={k:doc[k] for k in ['method','size','latitude_bytes']};result['results']=[]
 for r in doc['results']:
  v={k:r[k] for k in ['country','owner','target','cell','positive','derived_base_geometry_contact','positive_geometry_sha256','derived_base_geometry_sha256','source_evidence_commit','diagnostic_rule_sha256']}
  v['positive_source']={k:r['positive_source'][k] for k in ['source_id','name','feature_ordinal','decoded_bytes','decoded_sha256']}
  v['exclusions']=[]
  for e in r['exclusions']:
   keys=['source_index','source_id','geometry_sha256','relation'] if e['source_id']=='inline-archive-only' else ['negative_ordinal','source_id','feature_ordinal','feature_id','decoded_bytes','decoded_sha256','geometry_sha256','relation']
   v['exclusions'].append({k:e[k] for k in keys})
  result['results'].append(v)
 return result
r=run();assert r.returncode==0,r.stderr
actual=json.loads(r.stdout);assert normalized(actual)==normalized(old),'scientific output differs'
checks=[]
with tempfile.TemporaryDirectory(prefix='hnd-nic-adverse-') as tmp:
 t=pathlib.Path(tmp)
 def refuse(name,expected,**kw):
  q=run(**kw);assert q.returncode!=0 and expected in q.stderr,(name,q.returncode,q.stderr);checks.append(name)
 h=t/'helper.mjs';h.write_bytes((F/'native-grid.mjs').read_bytes()+b'\n');refuse('altered helper bytes','Native helper SHA-256',h=h)
 lat=t/'latitudes.f64le';v=bytearray((F/'native-row-latitudes.f64le').read_bytes());v[0]^=1;lat.write_bytes(v);refuse('altered normative latitude','Normative latitude vector size or SHA-256',lat=lat)
 p=t/'packet.json';v=copy.deepcopy(packet);v['rows'][0]['original_key']['owner_index']+=1;p.write_text(json.dumps(v));refuse('changed original owner target','Target binding mismatch',p=p)
 f=t/'fixture';(f/'payloads').mkdir(parents=True);(f/'evidence').symlink_to(F/'evidence',target_is_directory=True)
 for source in (F/'payloads').iterdir():
  destination=f/'payloads'/source.name
  if source.name=='gb-HND-ADM2-000.bin.gz':destination.write_bytes(gzip.compress(gzip.decompress(source.read_bytes()),mtime=1))
  else:destination.symlink_to(source)
 refuse('changed complete positive source bytes','Whole source body mismatch',f=f)
 for name,change in [
  ('changed reported contact relation',lambda v:v['results'][0]['positive'].__setitem__('relation','outside')),
  ('changed reported geometry digest',lambda v:v['results'][0].__setitem__('derived_base_geometry_sha256','0'*64)),
  ('omitted negative operand',lambda v:v['results'][0]['exclusions'].pop()),
  ('changed negative source identity',lambda v:v['results'][1]['exclusions'][0].__setitem__('source_id','gb:HND:ADM1:wrong'))]:
  v=copy.deepcopy(actual);change(v);assert normalized(v)!=normalized(old),name;checks.append(name)
receipt={'script_sha256':sha(script.read_bytes()),'packet_sha256':sha(packetfile.read_bytes()),'new_execution_node':subprocess.check_output(['node','--version'],text=True).strip(),'positive_scientific_projection_equal':True,'row_count':len(actual['results']),'negative_operand_count':sum(len(x['exclusions']) for x in actual['results']),'controls':checks,'negative_controls':len(checks),'excluded_from_projection':['Top-level historical evidence_pins and original added Git locators: independently authenticated externally','source_path: local basename versus public repository path','stored encoding/bytes/hash: CRI ADM2 now authenticated gzip; original used decoded materialization','narrative limitations string'],'limits':'This executes the published reconstruction against authenticated existing inputs. It is not an original invocation receipt or source/physical/native-qualification producer replay. Complete source-evidence bodies are authenticated externally against their exact published Git blobs before execution.'}
print(json.dumps(receipt,indent=2))

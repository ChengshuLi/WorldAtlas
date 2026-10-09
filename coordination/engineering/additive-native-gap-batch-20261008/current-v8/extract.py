from pathlib import Path
import json,gzip,hashlib,subprocess,array,sys
R=Path('/Users/chengshuli/world-atlas-workspace'); O=Path(__file__).resolve().parent
W=R/'WorldAtlas'; H='f2b129423c04d32b4b47ea36abae198651c50dae'
B=R/'.cache/1295-normal-consumer-materialization-20261008/image-df881'; base=B/'data/canonical-grid/eastern-v8'
sha=lambda b:hashlib.sha256(b).hexdigest()
write=lambda p,v:p.write_text(json.dumps(v,sort_keys=True,separators=(',',':'))+'\n')
pins=[]
def git(path):
 b=subprocess.check_output(['git','-C',str(W),'show',H+':'+path]); meta=subprocess.check_output(['git','-C',str(W),'ls-tree',H,'--',path],text=True).split()
 assert meta[0]=='100644' and meta[1]=='blob';pins.append({'commit':H,'path':path,'mode':meta[0],'blob':meta[2],'bytes':len(b),'sha256':sha(b)});return b
sel=json.loads(git('data/ownership-selection.json')); raw=git('data/canonical-grid/eastern-v8/manifest.json');m=json.loads(raw)
assert sha(raw)==sel['sha256']=='a71edb65cbd7986e245f626e8a34b70e12c12d081ca24fc936bdd84e1bb07885'
assert (base/'manifest.json').read_bytes()==raw
p=json.load(open(R/'.cache/root1523-baseline-resolution-20261008/input-plan-v2.json'))
mp=B/'.cache/1295-canonical-j1UONR/canonical-objects/canonical-path-map.json'; mapraw=mp.read_bytes();assert sha(mapraw)==p['canonical_pathmap_pin']['sha256'];mapping=json.loads(mapraw)
# Authenticate the original transport container rather than relying only on a cache filename.
ns='coordination/engineering/eastern-two-gap-repair-native-20261007/canonical-products/'
idx=json.loads(git(ns+'index.json')); d=idx['parts'][0]; enc=git(ns+d['path']); dec=gzip.decompress(enc)
assert sha(enc)==d['sha256'] and len(enc)==d['bytes'] and sha(dec)==d['decoded_sha256'] and len(dec)==d['decoded_bytes']
f=idx['files'][0];assert f['path']=='canonical-path-map.json' and dec[f['offset']:f['offset']+f['bytes']]==mapraw
bindings={q['target']:q for q in mapping['logical_targets']}; used=[]
def load(d):
 target='data/canonical-grid/eastern-v8/'+d['path'];bind=bindings[target]; raw=(base/d['path']).read_bytes(); decoded=gzip.decompress(raw)
 assert len(raw)==d['bytes']==bind['bytes'] and sha(raw)==d['sha256']==bind['sha256']
 assert len(decoded)==d['decoded_bytes'];assert d['encoding']=='byte-shuffle'
 n=d['words'];assert len(decoded)==n*4
 out=bytearray(n*4)
 for j in range(4):out[j::4]=decoded[j*n:(j+1)*n]
 assert sha(out)==d['decoded_sha256']; words=array.array('I');words.frombytes(out)
 if sys.byteorder!='little':words.byteswap()
 (O/Path(d['path']).name).write_bytes(raw)
 used.append({'manifest_descriptor':d,'canonical_binding':bind,'whole_encoded_and_decoded_verified':True,'gzip_transport_decoded_sha256':sha(decoded),'unshuffled_canonical_words_sha256':sha(out)})
 return words
rowsd=next(d for d in m['parts'] if d['kind']=='rows'); rows=load(rowsd)
window_raw=(R/'.cache/root1523-alaska13-owner-window-plan.json').read_bytes();assert sha(window_raw)=='b3c7dba23d0d4394fa34dd5199a31bfcedce56d239318e12459fb6a2a39279af';window=json.loads(window_raw);assert len(window['rows'])==len({v['component_id']for v in window['rows']})==13;ys=sorted({y for v in window['rows']for y in range(v['row_start'],v['row_end'])});assert sum(v['row_end']-v['row_start']for v in window['rows'])==125 and len(ys)==125;required=[(y,rows[y*2],rows[y*2+1])for y in ys]
lo=min(a*2 for y,a,n in required);hi=max((a+n)*2 for y,a,n in required)
parts=[d for d in m['parts'] if d['kind']=='runs' and d['offset']<hi and d['offset']+d['words']>lo]
arrays=[(d,load(d)) for d in parts]; output=[]
for y,a,n in required:
 spans=[];previous=0
 for i in range(a,a+n):
  ds=[(d,w) for d,w in arrays if d['offset']<=i*2 and i*2+1<d['offset']+d['words']];assert len(ds)==1
  d,w=ds[0];k=i*2-d['offset'];v,z=w[k],w[k+1];mask=(1<<m['coordinateBits'])-1
  s=v&mask;e=(z&mask)+1;owner=(v>>m['coordinateBits'])+(z>>m['coordinateBits'])*(1<<(32-m['coordinateBits']))
  assert previous<=s<e<=m['size'] and owner>0;previous=e;spans.append([s,e,owner])
 output.append({'y':y,'first_run':a,'run_count':n,'complete_owner_intervals':spans})
for name in ['pixel-grid.js','pixel-ownership.js','ownership-codec.js']:(O/name).write_bytes(git('src/'+name))
write(O/'complete-owner-rows.json',output)
write(O/'receipt.json',{'operation':'complete-selected-native-owner-row-exclusion','selected_manifest_sha256':sel['sha256'],'selected_release':sel['release_id'],'immutable_commit':H,'window_plan_sha256':sha(window_raw),'windows':window['rows'],'row_scope':ys,'all_rows_complete':True,'complete_run_count':sum(r['run_count']for r in output),'candidate_cells':[],'source_approval_or_release_activation':False,'immutable_git_pins':pins,'canonical_path_map_sha256':sha(mapraw),'whole_assets':used,'limits':['Whole125rows and all existing owner intervals; no candidate rasterization/newassignment, no source approval.']})
print(json.dumps({'complete_rows':len(output),'complete_runs':sum(r['run_count']for r in output),'run_parts':len(parts),'candidate_windows':13,'receipt':str(O/'receipt.json')}))

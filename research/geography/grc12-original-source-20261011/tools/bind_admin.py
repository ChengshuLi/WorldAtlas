"""Authenticate complete original source products and exact retained GRC rows."""
import gzip,hashlib,io,json,pathlib,resource,subprocess,sys,time
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[3];OWN=HERE.parent.relative_to(ROOT).as_posix();BASE='6a99a7606b9c2d11ac8cd093610653d4cd5d1382';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a])
def main():
 head,vintage=sys.argv[1:];start=time.monotonic()
 if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Exact HEAD required')
 controls=[OWN+'/tools/bind_admin.py',OWN+'/roster.json','scripts/evidence/immutable.py'];pins=[]
 for p in controls:
  b=(ROOT/p).read_bytes()
  if b!=git('show',head+':'+p):raise ValueError('Unfrozen control')
  pins.append({'path':p,'bytes':len(b),'sha256':sha(b),'hash_kind':'file-bytes'})
 ns={'__name__':'grc_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')};exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns);base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=128*1024**2);canon=ns['canonical_json']
 dest=ns['NewVintage'](base,OWN+'/',vintage,['comparison-rows.json','consumed-source.geojson','source-metadata.json','receipt.json']);roster=json.loads(base.pinned_bytes(OWN+'/roster.json'));inputs=[]
 def read(p,pin=None,decode=False):
  line=git('ls-tree','-z',BASE,'--',p).decode().rstrip('\0');fields,path=line.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,path)!=('100644','blob',p):raise ValueError('Nonordinary immutable body')
  base.admit(BASE+':'+p,int(git('cat-file','-s',oid)));b=git('cat-file','blob',oid);d={'commit':BASE,'path':p,'mode':mode,'git_blob_oid':oid,'bytes':len(b),'sha256':sha(b)}
  if pin:
   for k in ['bytes','sha256','git_blob_oid']:
    if k in pin and pin[k]!=d[k]:raise ValueError('Whole source pin mismatch')
  if decode:
   size=pin['uncompressed_bytes'] if pin and 'uncompressed_bytes' in pin else int.from_bytes(b[-4:],'little');base.admit('decoded:'+p,size)
   with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:b=f.read(size+1)
   if len(b)!=size or pin and 'uncompressed_sha256' in pin and sha(b)!=pin['uncompressed_sha256']:raise ValueError('Decoded source pin mismatch')
   d.update(uncompressed_bytes=len(b),uncompressed_sha256=sha(b))
  inputs.append(d);return b
 selected={}
 for p in sorted({r['source_row']['path'] for r in roster['members']}):
  wanted=[r for r in roster['members'] if r['source_row']['path']==p];rows=json.loads(read(p,wanted[0]['source_row'],True));ids=[r['component'] for r in rows]
  if len(ids)!=len(set(ids)):raise ValueError('Duplicate original comparison identity')
  for w in wanted:
   r=rows[w['source_row']['ordinal']]
   if r['component']!=w['component_id'] or r['full_component_feature_sha256']!=w['full_feature_sha256'] or r['component_geometry_sha256']!=w['geometry_sha256'] or r['family']!=w['family'] or r['uniquely_covering_compatible_recorded_subject']!=w['target']:raise ValueError('Original comparison row drift')
   selected[r['component']]=r
 product=roster['source_products'][0];source=read(product['parts'][0]['path'],product['parts'][0],True)
 if sha(source)!=product['whole_sha256'] or len(source)!=product['original_bytes']:raise ValueError('Consumed source whole bytes differ')
 data=json.loads(source)
 if len(data['features'])!=326:raise ValueError('Incomplete source feature roster')
 registry=json.loads(read('data/administrative-sources.json'));catalogue=json.loads(read('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'));entry=next(r for r in catalogue['products'] if r['key']=='gb:GRC:ADM3')
 if entry['original_sha256']!=sha(source) or registry['gb:GRC:ADM3']['sha256']!=sha(source):raise ValueError('Consumed original catalogue mismatch')
 receipt={'execution_commit':head,'baseline':BASE,'components':len(selected),'source_inputs':inputs,'logical_consumed_input_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'elapsed_seconds':time.monotonic()-start,'limits':['Original whole source-cover observations are provisional, not accepted physical or legal truth.']}
 if receipt['peak_rss_bytes']>512*1024**2:raise ValueError('RSS exceeded')
 dest.publish_bytes({'comparison-rows.json':canon([selected[r['component_id']] for r in roster['members']]),'consumed-source.geojson':source,'source-metadata.json':canon({'source_id':'gb:GRC:ADM3','registry_record':registry['gb:GRC:ADM3'],'catalogue_record':entry}),'receipt.json':canon(receipt)})
 print(json.dumps({k:receipt[k] for k in ['components','logical_consumed_input_bytes','peak_rss_bytes','elapsed_seconds']}))
if __name__=='__main__':main()

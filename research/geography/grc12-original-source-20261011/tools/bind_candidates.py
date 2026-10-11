"""Authenticate the bounded original Greek candidate cohort without new GIS."""
import gzip, hashlib, io, json, pathlib, resource, subprocess, sys, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OWN=HERE.parent.relative_to(ROOT).as_posix()
BASE='6a99a7606b9c2d11ac8cd093610653d4cd5d1382'
INDEX='coordination/engineering/physical-gap-components-1005-20261005-local19/custody-v1/index.json'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def main():
 start=time.monotonic();head,vintage=sys.argv[1:]
 if git('rev-parse','HEAD').decode().strip()!=head:raise ValueError('Require exact execution HEAD')
 controls=[OWN+'/tools/bind_candidates.py',OWN+'/roster.json',OWN+'/issue.json','scripts/evidence/immutable.py'];pins=[]
 for name in controls:
  raw=(ROOT/name).read_bytes()
  if raw!=git('show',head+':'+name):raise ValueError('Unfrozen input')
  pins.append({'path':name,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
 ns={'__name__':'grc_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')}
 exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns)
 base=ns['Baseline'](ROOT,head,pins,max_phase_bytes=128*1024**2)
 for name in controls:base.pinned_bytes(name)
 original=json.loads(base.pinned_bytes(OWN+'/roster.json'));wanted={r['component_id']:r for r in original['members']}
 if len(wanted)!=12:raise ValueError('Changed twelve-member original scope')
 issue=json.loads(base.pinned_bytes(OWN+'/issue.json'))
 if issue['number']!=1733 or not all(cid in issue['body'] for cid in wanted):raise ValueError('Original issue scope mismatch')
 dest=ns['NewVintage'](base,OWN+'/',vintage,['original-components.json','candidate-bindings.json','receipt.json'])
 inputs=[]
 def read(name,pin=None):
  tree=git('ls-tree','-z',BASE,'--',name).decode().rstrip('\0');fields,actual=tree.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,actual)!=('100644','blob',name):raise ValueError('Nonordinary original body')
  size=int(git('cat-file','-s',oid));base.admit(BASE+':'+name,size);raw=git('cat-file','blob',oid)
  if pin and (len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']):raise ValueError('Original whole bytes differ')
  d={'commit':BASE,'path':name,'mode':mode,'git_blob_oid':oid,'bytes':len(raw),'sha256':sha(raw)}
  if pin:
   base.admit('decoded:'+name,pin['uncompressed_bytes'])
   with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:raw=stream.read(pin['uncompressed_bytes']+1)
   if len(raw)!=pin['uncompressed_bytes'] or sha(raw)!=pin['uncompressed_sha256']:raise ValueError('Original whole decoded body differs')
   d.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
  inputs.append(d);return json.loads(raw),d
 index,_=read(INDEX);selected={r['path'] for r in original['candidate_products']};chosen=[x for x in index['aliases'] if '/components-v3/components-' in x['original']['path'] and x['payload'] in selected]
 if len(chosen)!=7:raise ValueError('Incomplete original candidate product inventory')
 found={}
 for x in chosen:
  body,pin=read(x['payload'],x['original']);rows=body['features']
  if len({f['id'] for f in rows})!=len(rows):raise ValueError('Duplicate original candidate')
  for ordinal,f in enumerate(rows):
   if f['id'] not in wanted:continue
   cid=f['id'];c=wanted[cid];fh=sha(ns['canonical_json'](f));gh=sha(ns['canonical_json'](f['geometry']))
   if cid in found or fh!=c['full_feature_sha256'] or gh!=c['geometry_sha256'] or ordinal!=c['candidate_custody']['ordinal']:raise ValueError('Original candidate/comparison identity drift')
   found[cid]={'component_id':cid,'feature':f,'feature_sha256':fh,'geometry_sha256':gh,'containing_original_product':pin,'logical_original_product':x['original'],'feature_ordinal':ordinal,'retained_detector_area_m2':f['properties']['measured_fragment_area_sum_m2']}
 if set(found)!=set(wanted):raise ValueError('Missing original candidate')
 rows=[found[cid] for cid in wanted]
 receipt={'execution_head':head,'baseline':BASE,'kind':'original-candidate-custody-and-retained-metric-join','components':len(rows),'inputs':inputs,'logical_input_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'elapsed_seconds':time.monotonic()-start,'limits':['Original detector area is inherited, not fresh area or approved repair area.','No new GIS, source acceptance, native integration or current-truth approval.']}
 if receipt['peak_rss_bytes']>512*1024**2:raise ValueError('Process reservation exceeded')
 dest.publish({'original-components.json':[r['feature'] for r in rows],'candidate-bindings.json':rows,'receipt.json':receipt})
 print(json.dumps({k:receipt[k] for k in ['components','logical_input_bytes','peak_rss_bytes','elapsed_seconds']}))
if __name__=='__main__':main()

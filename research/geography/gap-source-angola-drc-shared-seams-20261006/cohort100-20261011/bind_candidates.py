"""Authenticate original candidate bytes and detector areas for the complete cohort."""
import gzip
import hashlib
import io
import json
import pathlib
import resource
import subprocess
import sys
import time
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
 script=(HERE/'bind_candidates.py').relative_to(ROOT).as_posix();roster=(HERE/'roster.json').relative_to(ROOT).as_posix()
 classification=OWN+'/vintages/cohort100-original-classification-001/original-comparison-rows.json'
 pins=[]
 for name in [script,roster,classification,'scripts/evidence/immutable.py']:
  raw=(ROOT/name).read_bytes()
  if raw!=git('show',head+':'+name):raise ValueError('Unfrozen input')
  pins.append({'path':name,'bytes':len(raw),'sha256':sha(raw),'hash_kind':'file-bytes'})
 ns={'__name__':'candidate_immutable','__file__':str(ROOT/'scripts/evidence/immutable.py')}
 exec(compile(git('show',head+':scripts/evidence/immutable.py'),ns['__file__'],'exec'),ns)
 base=ns['Baseline'](ROOT,head,pins);base.pinned_bytes(script)
 original=json.loads(base.pinned_bytes(roster));comparisons=json.loads(base.pinned_bytes(classification));want=set(original['candidate_ids']);byid={r['comparison']['component']:r['comparison'] for r in comparisons}
 dest=ns['NewVintage'](base,OWN+'/',vintage,['original-candidates.json','receipt.json'])
 inputs=[]
 def read(name,pin=None):
  tree=git('ls-tree','-z',BASE,'--',name).decode().rstrip('\0');fields,actual=tree.split('\t');mode,kind,oid=fields.split()
  if (mode,kind,actual)!=('100644','blob',name):raise ValueError('Nonordinary original body')
  size=int(git('cat-file','-s',oid));base.admit(BASE+':'+name,size);raw=git('cat-file','blob',oid)
  if pin and (len(raw)!=pin['bytes'] or sha(raw)!=pin['sha256']):raise ValueError('Original whole bytes differ')
  d={'commit':BASE,'path':name,'mode':mode,'blob':oid,'bytes':len(raw),'sha256':sha(raw)}
  if pin:
   base.admit('decoded:'+name,pin['uncompressed_bytes'])
   with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:raw=stream.read(pin['uncompressed_bytes']+1)
   if len(raw)!=pin['uncompressed_bytes'] or sha(raw)!=pin['uncompressed_sha256']:raise ValueError('Original whole decoded body differs')
   d.update(uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
  inputs.append(d)
  if sum(base.consumed.values())>128*1024**2-4*1024**2:raise ValueError('Complete metadata phase exceeded')
  return json.loads(raw),d
 index,indexpin=read(INDEX);chosen=[x for x in index['aliases'] if '/components-v3/components-' in x['original']['path']]
 if len(chosen)!=11:raise ValueError('Incomplete original candidate inventory')
 found={}
 for x in chosen:
  body,pin=read(x['payload'],x['original']);rows=body['features']
  if len({f['id'] for f in rows})!=len(rows):raise ValueError('Duplicate original candidate')
  for ordinal,f in enumerate(rows):
   if f['id'] not in want:continue
   cid=f['id'];c=byid[cid];fh=sha(ns['canonical_json'](f));gh=sha(ns['canonical_json'](f['geometry']))
   if cid in found or fh!=c['full_component_feature_sha256'] or gh!=c['component_geometry_sha256']:raise ValueError('Original candidate/comparison identity drift')
   found[cid]={'component_id':cid,'feature':f,'feature_sha256':fh,'geometry_sha256':gh,'containing_original_product':pin,'logical_original_product':x['original'],'feature_ordinal':ordinal,'retained_detector_area_m2':f['properties']['measured_fragment_area_sum_m2']}
 if set(found)!=want:raise ValueError('Missing original candidate')
 rows=[found[cid] for cid in original['candidate_ids']]
 receipt={'execution_head':head,'baseline':BASE,'kind':'original-candidate-custody-and-retained-metric-join','components':len(rows),'inputs':inputs,'logical_input_bytes':sum(base.consumed.values()),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'elapsed_seconds':time.monotonic()-start,'limits':['Original detector area is inherited, not a fresh area measurement or accepted repair area.','No new GIS, source acceptance, native integration or current-truth approval.']}
 if receipt['peak_rss_bytes']>256*1024**2:raise ValueError('Process reservation exceeded')
 dest.publish({'original-candidates.json':rows,'receipt.json':receipt})
 print(json.dumps({k:receipt[k] for k in ['components','logical_input_bytes','peak_rss_bytes','elapsed_seconds']}))
if __name__=='__main__':main()

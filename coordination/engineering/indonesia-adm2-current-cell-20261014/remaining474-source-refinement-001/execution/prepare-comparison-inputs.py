"""Literal source acquisition/request assembly; no geographic predicate."""
import collections,gzip,hashlib,json,os,subprocess
from pathlib import Path
R=Path.cwd();O=Path(__file__).resolve().parent
E=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_NO_REPLACE_OBJECTS='1');G=['git','-c','protocol.allow=never','--git-dir=/Users/chengshuli/world-atlas-workspace/WorldAtlas/.git']
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):
 b=p.read_bytes();return {'path':str(p.resolve()),'bytes':len(b),'sha256':sha(b)}
heldpath=R/'idn-remaining19590-native-preparation-001/foreign2924/held-original-rows.json';held=json.load(open(heldpath));provenance=json.load(open(R/'idn-remaining19590-native-preparation-001/foreign-exclusion-provenance.json'))
requests=[]
for row in held['rows']:
 for a,z,owner in row['runs']:
  for x in range(a,z):requests.append({'id':f'repair:{owner}:{row["y"]}:{x}','original_package':'repair','country':'TLS'if owner in [22947,22839,23013]else'MYS','owner':owner,'y':row['y'],'x':x,'original_held_interval':[row['y'],a,z,owner],'original_request_custody':pin(heldpath),'original_foreign_source_indices':provenance['owner_to_source_indices'][str(owner)],'original_held_reason':'territorial_exclusion_cells'})
assert len(requests)==474
p=R/'source-conflict-evidence-borneo/exact-native-centres.json';borneo=json.load(open(p))
for i,r in enumerate(borneo['cells']):requests.append({'id':f'conflict:Borneo:{i}:{r["y"]}:{r["x"]}','original_package':'conflict','country':'MYS','y':r['y'],'x':r['x'],'original_record':r,'original_request_custody':pin(p)})
p=R/'source-conflict-evidence-timor-png/exact-six-centres.json';timor=json.load(open(p))
for i,r in enumerate(timor['centres']):
 for x in range(r['start'],r['end']):requests.append({'id':f'conflict:TimorPNG:{i}:{r["y"]}:{x}','original_package':'conflict','country':'PNG'if any(s.startswith('gb:PNG:')for s in r['competing_stable_subject_ids'])else'TLS','y':r['y'],'x':x,'original_record':r,'original_request_custody':pin(p)})
assert len(requests)==501 and len({r['id']for r in requests})==501
(O/'exact501-original-requests.json').write_text(json.dumps({'requests':requests,'counts':dict(collections.Counter((r['original_package']+':'+r['country'])for r in requests))},indent=2)+'\n')
catalog=json.loads(subprocess.check_output(G+['cat-file','blob','09afab19371f0814da61e79e5f310c5fb2405b6d'],env=E));families=[]
fullfiles={'gb:MYS:ADM1':O/'geoBoundaries-MYS-ADM1.geojson','gb:MYS:ADM2':O/'geoBoundaries-MYS-ADM2.geojson','gb:TLS:ADM1':R/'idn-remaining474-source-research-001/worker5-timor14/worker6-followup-001/geoBoundaries-TLS-ADM1.geojson','gb:TLS:ADM2':R/'idn-remaining474-source-research-001/worker5-timor14/worker6-followup-001/geoBoundaries-TLS-ADM2.geojson','gb:PNG:ADM3':R/'idn-physical-remainder80712-001/worker5-remainder-verification/fly1-same-release-source/geoBoundaries-PNG-ADM3.geojson'}
# TLSADM2 is appended when its sole source author supplies the exact acquired body.
for key,p in fullfiles.items():
 product=next(x for x in catalog['products']if x['key']==key);assert len(product['parts'])==1;part=product['parts'][0];b=subprocess.check_output(G+['show','f7c358326d776398bc1cffe84df81eac7033091c:'+part['path']],env=E,stderr=subprocess.PIPE);assert len(b)==part['bytes']and sha(b)==part['sha256'];decoded=gzip.decompress(b);assert sha(decoded)==product['original_sha256'];oldpath=O/(key.replace(':','-')+'-original-consumed.json');oldpath.write_bytes(decoded);old=json.loads(decoded);full=json.load(open(p));om={x['properties']['shapeID']:x['properties']for x in old['features']};fm={x['properties']['shapeID']:x['properties']for x in full['features']};assert om==fm
 families.append({'key':key,'country':key.split(':')[1],'original':pin(oldpath),'full':pin(p),'original_corpus_part':part,'recorded_consumed_url':product['recorded_consumed_url'],'license':product['recorded_license'],'represented_year_claim':product['source_represented_year_claim'],'actual_original_features':len(om),'actual_full_features':len(fm),'all_feature_properties_identical':True,'advertised_feature_count':product.get('advertised_feature_count')})
config={'kind':'same-release-unsimplified-vs-original-consumed-native-observation-only','kernel':json.load(open(O/'accepted-native-kernel-pin.json')),'requests':pin(O/'exact501-original-requests.json'),'normative_latitudes':pin(R/'idn-aru21line-cell-effects-001/normative-native-row-latitudes.f64le.gz'),'normative_decoded_bytes':262166*8,'normative_decoded_sha256':'66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23','grid_size':262166,'families':families,'limits':['Native source-format comparison only; no ownership winner, authority, repair, hold clearance or legal border is assigned.','Original complete consumed simplified families remain unchanged and retained. Full-resolution bodies are actual same9469f09 release, not a new country treaty.','All family members at all original country-scoped centres are tested; emerging competing features and exact boundary ties are retained.']}
(O/'comparison-config.json').write_text(json.dumps(config,indent=2)+'\n');print(json.dumps({'requests':config['requests'],'counts':dict(collections.Counter(r['original_package']+':'+r['country']for r in requests)),'families':[(f['key'],f['actual_full_features'])for f in families]},indent=2))

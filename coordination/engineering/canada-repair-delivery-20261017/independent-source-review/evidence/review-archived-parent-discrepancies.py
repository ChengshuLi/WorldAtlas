import json,gzip,pathlib,subprocess,hashlib
from shapely.geometry import shape
from shapely import make_valid
W=pathlib.Path.cwd();H=subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
def raw(p):return subprocess.check_output(['git','-c','protocol.allow=never','show',H+':'+p])
def js(p):return json.loads(raw(p))
cat=js('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json');pins={}
def features(key):
 r=next(p for p in cat['products']if p['key']==key);pieces=[]
 for p in r['parts']:
  b=raw(p['path']);assert len(b)==p['bytes']and hashlib.sha256(b).hexdigest()==p['sha256'];d=gzip.decompress(b);assert len(d)==p['uncompressed_bytes']and hashlib.sha256(d).hexdigest()==p['uncompressed_sha256'];pieces.append(d)
 d=b''.join(pieces);assert len(d)==r['original_bytes']and hashlib.sha256(d).hexdigest()==r['original_sha256'];pins[key]={'feature_count':r['feature_count'],'bytes':len(d),'sha256':r['original_sha256']};fs=json.loads(d)['features'];assert len(fs)==r['feature_count'];return fs
admin1=[(f['properties'],make_valid(shape(f['geometry'])))for f in features('gb:CAN:ADM1')];can3={'gb:CAN:ADM3:'+f['properties']['shapeID']:f for f in features('gb:CAN:ADM3')};archive=json.loads(gzip.decompress(raw('data/geographic-migration-archive.json.gz')));archived={f['id']:f for f in archive['locations']};units={f['id']:f for f in archive['units']};mismatches=json.load(open(W/'.scratch/remainder-archive-inventory.json'))['area_mismatches'];rows=[]
for m in mismatches:
 a=archived[m['id']];f=can3[m['id']];g=make_valid(shape(f['geometry']));oldg=make_valid(shape(a['geometry']));parent=units[a['parent_id']];hits=[]
 for p,pg in admin1:
  v=g.intersection(pg).area
  if v>0:hits.append({'name':p['shapeName'],'original_id':p['shapeID'],'fraction_of_ADM3_original':v/g.area,'fraction_of_archived_geometry':oldg.intersection(pg).area/oldg.area})
 hits.sort(key=lambda r:-r['fraction_of_ADM3_original']);rows.append({**m,'name':f['properties']['shapeName'],'archived_parent':parent,'archived_metadata':a['metadata'],'original_ADM1_overlaps':hits})
res={'kind':'independent-five-archived-parent-discrepancy-source-check','baseline':H,'source_pins':pins,'rows':rows,'limits':['Pinned full-source polygon overlay demonstrates geographic consistency, not exact pre-adaptation input identity or current legal boundary approval. Archive parent metadata belongs to an older reference stage.']};(W/'.scratch/archived-parent-discrepancies.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({'source_pins':pins,'rows':[{k:r[k]for k in ['id','name','expected_area','metadata_area','original_ADM1_overlaps']}for r in rows]},indent=2))

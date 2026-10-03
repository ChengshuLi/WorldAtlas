#!/usr/bin/env python3
"""Independent source reconstruction and streamed candidate overlap verification."""
import argparse,gzip,hashlib,importlib.util,json,pathlib,sys,tarfile
sys.dont_write_bytecode=True
from shapely import STRtree,normalize
from shapely.geometry import shape
from shapely.ops import unary_union
from majority import canonical
from ellipsoidal_area import area

def read(p):
 p=pathlib.Path(p);return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def exact(actual,expected,label):
 if not actual.is_valid or actual.is_empty or not expected.is_valid or normalize(canonical(actual)).wkb!=normalize(canonical(expected)).wkb:raise ValueError('Source footprint mismatch: '+label)
def check_overlap(candidate,other,identifier):
 overlap=area(candidate.intersection(other))
 if overlap>.001:raise ValueError('Candidate positive-area overlap: '+identifier+' ('+str(overlap)+' m2)')
def validate(root,stage):
 root=pathlib.Path(root).resolve();stage=pathlib.Path(stage).resolve();composition=read(stage/'composition.json');deltas=composition['replacement_deltas'];by_id={d['id']:d for d in deltas}
 if len(by_id)!=6:raise ValueError('Expected six distinct retained geometry replacements')
 # Independently replay coast and inland-water assembly from original source bytes.
 cook=load(root/'data/macro-improvements/cook-restoration/prepare.py','cook_source_replay');osm={x['name']:x for x in read(root/'data/macro-improvements/macro-coverage-oceania/osm-sources.json')};dry,cookproof=cook.coast(osm['Manihiki']);exact(shape(by_id['COK-4961']['after_feature']['geometry']),dry,'Manihiki')
 europe=load(root/'data/macro-improvements/europe-asia-restoration/produce.py','europe_source_replay');base=root/'data/macro-improvements/europe-asia-restoration';inputs=read(base/'source-inputs.json');evaluation=root/inputs['evaluation_directory']
 for filename,pin in inputs['evaluation_files'].items():
  if hashlib.sha256((evaluation/filename).read_bytes()).hexdigest()!=pin:raise ValueError('Source evaluation bytes changed')
 queries={q['name']:q for q in read(evaluation/'modern-coastline-index.json')};source_evidence=[{'url':cookproof['url'],'source_sha256':cookproof['source_raw_sha256'],'license':cookproof['license'],'attribution':cookproof['attribution'],'supported_from':2026,'supported_to':2027}]
 with tarfile.open(evaluation/'geometry-and-modern-sources.tar.gz')as archive:
  for group in read(base/'decisions.json.gz')['location_decisions']:
   if not group['existing_location_id']:continue
   identifier=group['existing_location_id'];parts=[]
   for candidate in group['staged_components']:
    geometry,proof=europe.source_geometry(candidate,queries[candidate['query']],archive);parts.append(geometry);source_evidence.append({'url':proof['source_url'],'source_sha256':proof['source_xml_sha256'],'license':proof['license'],'attribution':proof['attribution'],'supported_from':2026,'supported_to':2027})
   modern=unary_union(parts);old=shape(by_id[identifier]['before_feature']['geometry']);expected=modern if group['group_key']in ['CocosSouth','DiegoGarcia']else unary_union([old,modern]);exact(shape(by_id[identifier]['after_feature']['geometry']),expected,identifier)
 additions=read(stage/'creation/geography/source-restoration-additions.json')['features'];candidates=[d['after_feature']for d in deltas]+additions;geoms=[canonical(shape(f['geometry']))for f in candidates];tree=STRtree(geoms);ids={f['id']:i for i,f in enumerate(candidates)};count=0
 for part in read(stage/'creation/world-index.json')['parts']:
  for f in read(stage/'creation'/part)['features']:
   count+=1;geometry=canonical(shape(f['geometry']))
   for index in tree.query(geometry,predicate='intersects'):
    if candidates[int(index)]['id']!=f['id']:check_overlap(geoms[int(index)],geometry,f['id'])
 # Archived predecessors cannot become new identities; existing-ID revisions retain their own archives.
 archives=read(root/'data/macro-improvements/oceania-restoration/retained-identity-scan.json.gz')['files'];creation_geoms=[canonical(shape(f['geometry']))for f in additions];creationtree=STRtree(creation_geoms);archived_count=0;archivepins=[]
 for row in archives:
  if 'archive'not in row['path']:continue
  file=root/row['path']
  if hashlib.sha256(file.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Archived predecessors changed')
  archivepins.append(row)
  for entry in read(file).get('locations',[]):
   feature=entry.get('feature',entry);geometry=canonical(shape(feature['geometry']));archived_count+=1
   for index in creationtree.query(geometry,predicate='intersects'):check_overlap(creation_geoms[int(index)],geometry,feature['id'])
 if count!=49623:raise ValueError('Final candidate inventory changed')
 return {'verified':True,'retained_geometry_replacements':6,'current_locations_checked':count,'archived_polygons_checked':archived_count,'creation_candidates':34,'area_tolerance_m2':.001,'source_evidence':source_evidence,'archive_pins':archivepins,'history_transfer':False,'regional_interiors_approved':False,'published':False}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--root',required=True);a.add_argument('--stage',required=True);a.add_argument('--output',required=True);args=a.parse_args();result=validate(args.root,args.stage);pathlib.Path(args.output).write_text(json.dumps(result,separators=(',',':')));print(json.dumps({k:v for k,v in result.items()if k not in ['source_evidence','archive_pins']}))

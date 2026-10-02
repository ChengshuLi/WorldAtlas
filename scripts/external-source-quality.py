"""Validate a complete source-quality plan and expose it without geographic mutation."""
import importlib.util,json,pathlib,hashlib,re
spec=importlib.util.spec_from_file_location('namibia_annotations',pathlib.Path(__file__).with_name('prepare-namibia-source-annotations.py'))
annotations=importlib.util.module_from_spec(spec);spec.loader.exec_module(annotations)
def validated_reviews(data,features,units):
 path=data/'namibia-source-quality-annotations.json'
 if not path.exists():return {'profiles':{},'locations':{},'groups':{},'manifest':[]}
 plan=annotations.read(path)
 annotations.validate_against_current(plan,features,list(units.values()) if isinstance(units,dict) else units)
 for proof in plan['profile_review']['public_evidence_files']:
  proofpath=pathlib.Path(proof['path'])
  if proofpath.is_absolute() or '..' in proofpath.parts:raise ValueError('Unsafe source evidence path')
  if annotations.file_hash(data/proofpath)!=proof['sha256']:raise ValueError('Stale source evidence: '+proof['path'])
 return {'profiles':{plan['profile_review']['country']:plan['profile_review']},
  'locations':{r['id']:r['metadata_patch']['source_quality_review'] for r in plan['feature_annotations']},
  'groups':{r['id']:r['metadata_patch']['source_quality_review'] for r in plan['group_annotations']},
  'manifest':[{'path':path.name,'sha256':annotations.file_hash(path),'counts':plan['counts'],
   'application':'External review records only; canonical geography and histories unchanged'}]}

def source_country_codes(feature):
 """Retain source territories separately from normalized sovereignty labels."""
 p=feature['properties'];m=p.get('metadata',{});values=[feature.get('id',''),m.get('source_id','')]+m.get('source_member_ids',[])
 codes=set()
 for value in values:
  match=re.search(r'gb:([A-Z]{3}):',value) or re.fullmatch(r'([A-Z]{3})[-+]\d+(?:\?)?',value)
  if match:codes.add(match.group(1))
 return sorted(codes)

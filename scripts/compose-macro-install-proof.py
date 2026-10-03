#!/usr/bin/env python3
"""Produce compound installer receipts from independently validated ordered children."""
import argparse,copy,hashlib,json,pathlib

def read(p):return json.loads(pathlib.Path(p).read_bytes())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,value):pathlib.Path(p).write_text(json.dumps(value,separators=(',',':'),ensure_ascii=False))
def compose(stage):
 stage=pathlib.Path(stage).resolve();reference=read(stage/'reference-receipt.json');composition=read(stage/'composition.json');replacement=read(stage/'replacement-migration/migration-receipt.json');creation=read(stage/'creation-migration/migration-receipt.json');validation=read(stage/'independent-validation.json');summary=read(stage/'preparation-summary.json')
 if validation['verified']is not True or reference.get('reference_only')is not True or replacement.get('geometry_stage_validated')is not True or creation.get('geometry_stage_validated')is not True or summary['published']is not False or replacement['after_footprints_sha256']!=creation['before_footprints_sha256']or any(r['historical_claims_transferred']is not False for r in [replacement,creation,reference]):raise ValueError('Unvalidated or contradictory ordered child proofs')
 changed=set(replacement['changed_ids']);added=set(creation['added_ids']);before=set(replacement['reused_ids'])|changed
 if len(changed)!=6 or len(added)!=34 or replacement['added_ids']or replacement['removed_ids']or creation['changed_ids']or creation['removed_ids']or set(creation['reused_ids'])!=before:raise ValueError('Unexpected compound mutation scope')
 # Child replacement originals include modern reference corrections. Installer
 # aggregate originals must be the exact installed features BEFORE those labels.
 archives=[{'id':d['id'],'feature':d['original_pre_reference_feature']}for d in composition['replacement_deltas']]
 if set(a['id']for a in archives)!=changed:raise ValueError('Exact installed originals missing')
 proofs=copy.deepcopy(creation['creation_proofs'])
 for proof in proofs:
  proof['source']['path']='creation-migration/'+proof['source']['path'];file=(stage/proof['source']['path']).resolve()
  if not file.is_relative_to(stage)or sha(file)!=proof['source']['sha256']:raise ValueError('Creation wrapper escaped or changed')
 receipt={'version':1,'geometry_stage_validated':True,'historical_claims_transferred':False,'before_hierarchy_sha256':reference['before_hierarchy_sha256'],'after_hierarchy_sha256':sha(stage/'creation/hierarchy.json'),'before_footprints_sha256':replacement['before_footprints_sha256'],'after_footprints_sha256':creation['after_footprints_sha256'],'changed_ids':sorted(changed),'removed_ids':[],'added_ids':sorted(added),'reused_ids':sorted(before-changed),'archives':archives,'added_features':creation['added_features'],'creation_proofs':proofs,'relationships':replacement['relationships']+creation['relationships'],'source_evidence':replacement['source_evidence']+creation['source_evidence'],'metadata_reference_receipt':{'path':'reference-receipt.json','sha256':sha(stage/'reference-receipt.json')},'ordered_geometry_manifest_required':True,'source_repair_scope':'Six same-ID dry-land corrections followed by34 genuine source-backed creations; modern names require separate pinned metadata receipt. No transfer of historical evidence, no regional interior approval.','scientific_validation_sha256':sha(stage/'independent-validation.json')}
 descriptor={'version':1,'before_footprints_sha256':receipt['before_footprints_sha256'],'after_footprints_sha256':receipt['after_footprints_sha256'],'manifests':[{'path':name+'/index.json','sha256':sha(stage/(name+'/index.json'))}for name in ['replacement-migration','creation-migration']],'metadata_receipts':[{'path':'reference-receipt.json','sha256':sha(stage/'reference-receipt.json')}]}
 write(stage/'aggregate-source-receipt.json',receipt);write(stage/'geometry-proofs.json',descriptor)
 return {'aggregate_source_receipt_sha256':sha(stage/'aggregate-source-receipt.json'),'geometry_proofs_sha256':sha(stage/'geometry-proofs.json'),'before_footprints_sha256':receipt['before_footprints_sha256'],'after_footprints_sha256':receipt['after_footprints_sha256'],'changed_ids':6,'added_ids':34,'removed_ids':0,'exact_current_original_archives':6,'source_creation_proofs':34,'history_transfer':False}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--stage',required=True);args=a.parse_args();print(json.dumps(compose(args.stage)))

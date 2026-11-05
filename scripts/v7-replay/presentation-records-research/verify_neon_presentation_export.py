#!/usr/bin/env python3
"""Validate an independently authenticated Neon export against pinned R2 readbacks."""
import argparse
import hashlib
import json
from pathlib import Path
import verify_presentation_release as parity

ASSET_FILES={'proposal':('proposal.json','proposal'),'water_presentation':('water-presentation.json','water'),'references':('review-references.json','reference')}
PIN_KEYS={'source_id','version','r2_bucket','r2_key','sha256','size_bytes'}
CODE_FILES={'release_verifier':'verify_presentation_release.py','neon_verifier':'verify_neon_presentation_export.py','export_sql':'export_presentation_release.sql','schema_sql':'presentation_release_schema.sql'}

def check_code_pins(manifest):
    pins=manifest.get('code_pins')
    if not isinstance(pins,dict) or set(pins)!=set(CODE_FILES):
        raise ValueError('invalid verifier code pins')
    here=Path(__file__).resolve().parent
    for name,file in CODE_FILES.items():
        if parity.digest(parity.bounded(here/file,1<<20))!=pins[name]:
            raise ValueError('verifier code pin mismatch: '+name)

def valid_pin(pin):
    return (isinstance(pin,dict) and set(pin)==PIN_KEYS
            and all(isinstance(pin[k],str) and pin[k] for k in ('source_id','version','r2_bucket','r2_key'))
            and isinstance(pin['sha256'],str) and len(pin['sha256'])==64
            and all(c in '0123456789abcdef' for c in pin['sha256'])
            and type(pin['size_bytes']) is int and pin['size_bytes']>=0)

def string_tree(value):
    # This presentation-only v1 format contains only strings, arrays and objects.
    # It avoids ambiguous JSONB numeric serialization in this historical export.
    if isinstance(value,str): return True
    if isinstance(value,list): return all(string_tree(x) for x in value)
    if isinstance(value,dict): return all(isinstance(k,str) and string_tree(v) for k,v in value.items())
    return False

def canonical_records(records):
    if not isinstance(records,dict) or not string_tree(records):
        raise ValueError('presentation records must contain only strings, arrays and objects')
    return (json.dumps(records,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf8')

def verify(snapshot_path,snapshot_sha,manifest_path,manifest_sha,manifest_source_pin_sha,input_dir,project,branch,database,code_revision):
    if not isinstance(code_revision,str) or len(code_revision)!=40 or any(c not in '0123456789abcdef' for c in code_revision):
        raise ValueError('invalid code revision')
    snapshot_raw=parity.bounded(snapshot_path, 8<<20)
    if parity.digest(snapshot_raw)!=snapshot_sha: raise ValueError('Neon export hash mismatch')
    snapshot=parity.strict_json(snapshot_raw)
    if not isinstance(snapshot,dict) or set(snapshot)!={'schema','origin','release','assets'} or snapshot['schema']!='worldatlas-neon-presentation-export-v1':
        raise ValueError('invalid Neon export')
    if snapshot['origin']!={'project_id':project,'branch_id':branch,'database':database}:
        raise ValueError('wrong Neon origin assertion')
    release=snapshot['release']
    if not isinstance(release,dict) or release.get('release_kind')!='historical_review_presentation':
        raise ValueError('not historical presentation')
    if release.get('manifest_sha256')!=manifest_sha:
        raise ValueError('release/manifest pin mismatch')
    manifest_raw=parity.bounded(manifest_path,1<<20)
    if parity.digest(manifest_raw)!=manifest_sha: raise ValueError('manifest hash mismatch')
    manifest=parity.strict_json(manifest_raw)
    if release.get('release_id')!=manifest.get('release_id'):
        raise ValueError('release ID mismatch')
    if release.get('code_revision')!=code_revision or manifest.get('code_revision')!=code_revision:
        raise ValueError('code revision mismatch')
    if manifest.get('schema')!='worldatlas-presentation-parity-manifest-v2' or not isinstance(manifest.get('sources'),dict) or set(manifest['sources'])!=set(ASSET_FILES):
        raise ValueError('manifest lacks exact source identities')
    check_code_pins(manifest)
    if not isinstance(snapshot['assets'],dict) or set(snapshot['assets'])!=set(ASSET_FILES)|{'manifest'}:
        raise ValueError('invalid source asset set')
    manifest_asset=snapshot['assets']['manifest']
    if not isinstance(manifest_asset,dict) or not valid_pin({k:manifest_asset.get(k) for k in PIN_KEYS}):
        raise ValueError('invalid manifest source asset')
    manifest_pin={k:manifest_asset[k] for k in PIN_KEYS}
    pin_bytes=(json.dumps(manifest_pin,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode('utf8')
    if parity.digest(pin_bytes)!=manifest_source_pin_sha:
        raise ValueError('manifest source identity pin mismatch')
    if manifest_asset['source_id']!=release.get('manifest_source_id') or manifest_asset['version']!=release.get('manifest_source_version') or manifest_asset['sha256']!=manifest_sha or manifest_asset['size_bytes']!=len(manifest_raw):
        raise ValueError('manifest source binding mismatch')
    source_pins=release.get('source_pins')
    if not isinstance(source_pins,dict) or set(source_pins)!=set(ASSET_FILES):
        raise ValueError('invalid release source pins')
    for name,(filename,prefix) in ASSET_FILES.items():
        asset=snapshot['assets'][name]
        pin=source_pins[name]
        manifest_pin=manifest['sources'].get(name)
        if not valid_pin(pin) or not valid_pin(manifest_pin):
            raise ValueError('invalid typed source pin: '+name)
        if not isinstance(asset,dict) or any(not parity.equal_json(asset.get(k),pin[k]) for k in PIN_KEYS):
            raise ValueError('asset row and release pin disagree: '+name)
        if not parity.equal_json(manifest_pin,pin):
            raise ValueError('manifest/source identity mismatch: '+name)
        if asset['source_id']!=release.get(prefix+'_source_id') or asset['version']!=release.get(prefix+'_source_version'):
            raise ValueError('asset foreign key mismatch: '+name)
        if not all(isinstance(asset[k],str) and asset[k] for k in ('source_id','version','r2_bucket','r2_key','sha256')) or type(asset['size_bytes']) is not int or asset['size_bytes']<0:
            raise ValueError('invalid asset metadata')
        raw=parity.bounded(Path(input_dir)/filename,8<<20)
        if len(raw)!=asset['size_bytes'] or parity.digest(raw)!=asset['sha256'] or manifest['assets'].get(name)!=asset['sha256']:
            raise ValueError('R2 readback mismatch: '+name)
    records_raw=canonical_records(release.get('records'))
    if parity.digest(records_raw)!=release.get('records_sha256') or manifest['assets'].get('records')!=release.get('records_sha256'):
        raise ValueError('canonical JSONB records mismatch')
    if parity.bounded(Path(input_dir)/'presentation-records-local.json',8<<20)!=records_raw:
        raise ValueError('exported records bytes differ from Neon')
    result=parity.verify(manifest_path,manifest_sha,input_dir)
    check_code_pins(manifest)
    result['status']='presentation-export-parity-verified-not-authenticated-or-deployed'
    result['neon_export_sha256']=snapshot_sha
    result['limitations'].append('Origin is an assertion: the caller must independently authenticate the Neon query result, source-identity pin, R2 readbacks, and code revision.')
    result['limitations'].append('On-disk code hashes are integrity checks, not authentication of already executing Python or Node bytes.')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','snapshot-sha256','manifest','manifest-sha256','manifest-source-pin-sha256','input-dir','project','branch','database','code-revision'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.snapshot,a.snapshot_sha256,a.manifest,a.manifest_sha256,a.manifest_source_pin_sha256,a.input_dir,a.project,a.branch,a.database,a.code_revision),sort_keys=True))


#!/usr/bin/env python3
"""Negative controls for the exact admission functions used by reconcile.py."""
import hashlib, importlib.util, io, json, pathlib, shutil, subprocess, zipfile
from datetime import datetime, timezone
import numpy as np

BASE=pathlib.Path(__file__).absolute().parent
REPO=BASE.parents[2]
OLD='research/geography/namibia-angola-sentinel2-followup-20261007/'
PACKET='f513f7d6cb5fb088c1fca0238d915426a14ecfa8'

def blob(path): return subprocess.check_output(['git','show',f'{PACKET}:{path}'],cwd=REPO)
def admit_output(path):
    path=pathlib.Path(path)
    try: path.relative_to(BASE)
    except ValueError: raise ValueError('control output escaped owned directory')
    for ancestor in (BASE,*BASE.parents):
        if ancestor.is_symlink(): raise ValueError('symlink in owned path ancestry')
        if ancestor==REPO.parent: break
    parent=path.parent
    while parent!=BASE:
        if parent.is_symlink(): raise ValueError('symlink in control output ancestry')
        if parent.exists() and not parent.is_dir(): raise ValueError('non-directory control output ancestor')
        parent=parent.parent
    if path.is_symlink() or path.exists(): raise FileExistsError('control receipt target already exists')

def rejects(fn):
    try: fn()
    except ValueError: return True
    return False

def main():
    folder=BASE/'controls'; stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'); output=folder/('input-controls-'+stamp+'.json'); probe=folder/('path-probe-'+stamp); target=probe/'target'; link=probe/'link'; [admit_output(x) for x in (output,probe,target,link)]
    probe.mkdir(exist_ok=False); target.mkdir(exist_ok=False); link.symlink_to(target,target_is_directory=True)
    try: admit_output(link/'escaped.json'); raise RuntimeError('symlinked control output parent admitted')
    except ValueError: symlink_parent_rejected=True
    finally: link.unlink(); shutil.rmtree(probe)
    spec=importlib.util.spec_from_file_location('integrity',BASE/'reconcile.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    selected=json.loads(blob(OLD+'inputs/selected-sentinel2-items.json'))['selected_items']
    receipts=json.loads(blob(OLD+'inputs/source-window-receipts.json'))['records']
    ids=[x['id'] for x in selected]; receipt_ids=[x['item_id'] for x in receipts]
    code=mod.read_candidate('reconcile.py')
    result={'control_symlink_parent_rejected':symlink_parent_rejected,'unaltered_executable_pin_accepted':mod.validate_code_bytes(code,mod.SELF_PIN) is None,
      'modified_executable_bytes_rejected':rejects(lambda:mod.validate_code_bytes(code+b'\n# modified after pin\n',mod.SELF_PIN)),
      'duplicate_scene_receipt_rejected':rejects(lambda:mod.validate_roster(ids,receipt_ids[:-1]+[receipt_ids[0]])),
      'missing_scene_receipt_rejected':rejects(lambda:mod.validate_roster(ids,receipt_ids[:-1])),
      'foreign_scene_receipt_rejected':rejects(lambda:mod.validate_roster(ids,receipt_ids[:-1]+['FOREIGN_SCENE']))}
    rec=receipts[0]; path=OLD+rec['npz_path']; raw=blob(path); arrays=mod.bounded_npz(raw)
    original_cb=arrays['component_bits'].copy(); original_tb=arrays['contact_bits'].copy()
    changed={k:v.copy() for k,v in arrays.items()}; changed['component_bits'][0]|=np.uint32(1<<31)
    changed['contact_bits'][0]|=np.uint16(1<<10)
    stream=io.BytesIO(); np.savez_compressed(stream,**changed); altered=stream.getvalue()
    coherent_receipt={**rec,'npz_sha256':hashlib.sha256(altered).hexdigest(),'npz_bytes':len(altered)}
    mod.validate_window_bytes(altered,coherent_receipt,path)
    decoded=mod.bounded_npz(altered)
    result['coherent_receipt_component_bit_corruption_rejected']=rejects(lambda:mod.validate_membership(original_cb,decoded['component_bits'],'control component'))
    result['coherent_receipt_contact_bit_corruption_rejected']=rejects(lambda:mod.validate_membership(original_tb,decoded['contact_bits'],'control contact'))
    wrong={k:v.copy() for k,v in arrays.items()}; wrong['green_dn_10m_2x2']=wrong['green_dn_10m_2x2'][:,:3]
    result['wrong_10m_subpixel_shape_rejected']=rejects(lambda:mod.validate_arrays(wrong))
    stale={**rec,'npz_sha256':'0'*64}
    result['stale_source_window_receipt_rejected']=rejects(lambda:mod.validate_window_bytes(raw,stale,path))
    result['source_window_raw_sha256']=hashlib.sha256(raw).hexdigest()
    result['coherent_altered_source_sha256']=hashlib.sha256(altered).hexdigest()
    if not all(v for k,v in result.items() if k.endswith('_rejected')): raise RuntimeError('input negative control failed')
    encoded=(json.dumps({'version':1,'source_scene':rec['item_id'],'tests':result},sort_keys=True,indent=2)+'\n').encode()
    fd=__import__('os').open(output,__import__('os').O_WRONLY|__import__('os').O_CREAT|__import__('os').O_EXCL,0o600)
    with __import__('os').fdopen(fd,'wb') as stream: stream.write(encoded); stream.flush(); __import__('os').fsync(stream.fileno())
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__': main()

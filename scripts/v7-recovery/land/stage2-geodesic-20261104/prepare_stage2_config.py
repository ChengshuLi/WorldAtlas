#!/usr/bin/env python3
"""Create a hash-pinned fresh stage-2 request, without starting a build.

The caller must obtain and independently authenticate the selected Neon export;
this utility only hashes supplied files. Seed, hint and old assignment artifacts
are not inputs. The generated request is still subject to the disabled gates.
"""
import argparse,json
from pathlib import Path
import checkpoints,orchestrate_stage2 as stage2,verify_inputs

def create(output,inputs,grid,policy_id,policy_version,controls,seed_controls,*,provisional_only=False):
 out=Path(output).resolve();stage2.need(out.parent.is_dir() and not out.exists(),'output must be a new file in an existing directory')
 stage2.need(type(provisional_only) is bool,'invalid provisional mode')
 allowed=(stage2.BASE_INPUTS,stage2.BASE_INPUTS|{'prior_physical_report'}) if provisional_only else (stage2.BASE_INPUTS,)
 stage2.need(isinstance(inputs,dict) and set(inputs) in allowed,'exact fresh input set required')
 stage2.build_stage2.validate_controls(controls)
 guard=lambda:checkpoints.guard(out.parent,controls['minimum_free_bytes']);guard()
 pins={k:stage2.pin(v,guard) for k,v in inputs.items()};stage2.need(all(not out.is_relative_to(Path(p['path']).parent) for p in pins.values()),'config must be outside input directories')
 cfg={'schema':'stage2-fresh-orchestration-v1','grid':grid,'inputs':pins,'policy_id':policy_id,'policy_version':policy_version,'controls':controls,'seed_controls':seed_controls}
 # Validate the same strict shape before creating any output.
 stage2.need(isinstance(grid,dict) and set(grid)=={'width','height','west','north','step'} and type(grid['width']) is int and type(grid['height']) is int and 1<grid['width']<=1000000 and 0<grid['height']<=1000000 and grid['west']==-180 and grid['north']==90 and type(grid['step']) in (int,float) and grid['step']==360/grid['width'] and 90-grid['height']*grid['step']>=-90-1e-8,'invalid global grid')
 stage2.need(isinstance(policy_id,str) and policy_id and isinstance(policy_version,str) and policy_version,'invalid policy')
 stage2.need(isinstance(seed_controls,dict) and set(seed_controls)=={'strip_rows'} and type(seed_controls['strip_rows']) is int and 1<=seed_controls['strip_rows']<=64,'invalid seed controls')
 for pin in pins.values():stage2.build_stage2.pin(pin,guard)
 digest=stage2.write_json(out,cfg);return {'schema':'stage2-fresh-config-receipt-v1','config_sha256':digest,'inputs_sha256':{k:v['sha256'] for k,v in pins.items()},'limitations':['Pinning files does not authenticate a Neon export or approve geographic decisions.','No work or map was created.']}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('spec',help='JSON with inputs, grid, policy_id, policy_version, controls, and seed_controls');p.add_argument('--provisional-only',action='store_true');a=p.parse_args()
 try:
  spec=json.loads(stage2.read_bytes(a.spec));stage2.need(set(spec)=={'inputs','grid','policy_id','policy_version','controls','seed_controls'},'invalid config spec');print(json.dumps(create(a.output,**spec,provisional_only=a.provisional_only),sort_keys=True))
 except Exception as exc:print('error: '+str(exc),file=__import__('sys').stderr);raise SystemExit(1)

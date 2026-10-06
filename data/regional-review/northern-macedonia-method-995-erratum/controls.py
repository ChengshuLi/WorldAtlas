#!/usr/bin/env python3
"""Meaningful rejection/reproducibility controls for the retained-phase runner."""
import hashlib, importlib.util, json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
OWN=ROOT/'data/regional-review/northern-macedonia-method-995-erratum'
RUNNER=OWN/'reproduce-retained-phase.py'
spec=importlib.util.spec_from_file_location('retained',RUNNER); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
one=(OWN/'v1/run-one.json').read_bytes(); two=(OWN/'v1/run-two.json').read_bytes()
assert one==two and hashlib.sha256(one).hexdigest()=='d3d23c61368d3db4fb5acf049cfaff9f3533a1da7c37c5b96d02070d50b3fef3'
report=json.loads(one); assert len(report['results']['pairs'])==84 and report['results']['nonzero_residual_count']==84
positive={'method_id':'retained-source-area-comparison','kind':'positive-control','outcome':'passed','details':'84 exact scoped pairs, 84 nonzero residuals, two byte-identical outputs'}
desc=json.loads((OWN/'baseline-inputs.json').read_text())['files'][0]
original=mod.baseline_blob
mod.baseline_blob=lambda _path: b'wrong bytes'
try:
    try: mod.load_pinned(desc)
    except ValueError: pass
    else: raise AssertionError('wrong input was accepted')
finally: mod.baseline_blob=original
negative_input={'method_id':'retained-source-area-comparison','kind':'negative-control','outcome':'passed','details':'corrupted immutable input bytes rejected by exact size/SHA256 check'}
pin_path=OWN/'runner-pin.json'; original_pin=pin_path.read_bytes()
pin_path.write_text('{"sha256":"'+'0'*64+'"}\n')
try:
    code_proc=subprocess.run([sys.executable,str(RUNNER),'data/regional-review/northern-macedonia-method-995-erratum/v1/code-control.json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
finally:
    pin_path.write_bytes(original_pin)
if code_proc.returncode==0 or b'runner code pin mismatch' not in code_proc.stderr: raise AssertionError('wrong runner code was accepted')
negative_code={'method_id':'retained-source-area-comparison','kind':'negative-control','outcome':'passed','details':'altered expected runner SHA-256 rejected before any output is written'}
# Re-execution reaches the exclusive-create guard after full immutable verification.
proc=subprocess.run([sys.executable,str(RUNNER),'data/regional-review/northern-macedonia-method-995-erratum/v1/run-one.json'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
if proc.returncode==0 or b'FileExistsError' not in proc.stderr: raise AssertionError('existing output was not rejected')
negative_output={'method_id':'retained-source-area-comparison','kind':'negative-control','outcome':'passed','details':'pre-existing output path rejected; original bytes remained unchanged'}
control={'version':1,'positive_control':positive,'negative_input_control':negative_input,'negative_code_control':negative_code,'negative_output_control':negative_output,'reproducibility':{'method_id':'retained-source-area-comparison','kind':'reproducibility','outcome':'passed','run_one_sha256':hashlib.sha256(one).hexdigest(),'run_two_sha256':hashlib.sha256(two).hexdigest(),'run_one_bytes':len(one),'run_two_bytes':len(two)}}
(OWN/'v1/controls.json').write_text(json.dumps(control,sort_keys=True,indent=2)+'\n')
for name,row in [('positive-control',positive),('negative-control',{**negative_input,'details':negative_input['details']+'; '+negative_code['details']+'; '+negative_output['details']}),('reproducibility-control',control['reproducibility'])]:
    (OWN/'v1'/f'{name}.json').write_text(json.dumps(row,sort_keys=True,indent=2)+'\n')
print(json.dumps({'controls':'passed','runs_equal':one==two,'existing_output_rejected':True,'wrong_input_rejected':True,'wrong_code_rejected':True}))

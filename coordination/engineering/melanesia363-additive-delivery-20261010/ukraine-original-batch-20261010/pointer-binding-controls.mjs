// Bounded actual trusted artifact-consumption entry, without scientific replay.
import fs from 'node:fs';import assert from 'node:assert/strict';import {execFileSync} from 'node:child_process';import {createHash} from 'node:crypto';
import {ImmutableReader,readArtifactConsumption} from '../../../../scripts/check-effective-geographic-regression.mjs';
import {nativeBaseSelection,valueSha} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const root=process.cwd(),version=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),read=p=>JSON.parse(fs.readFileSync(p));
const current=read('data/ownership-selection.json'),old=JSON.parse(execFileSync('git',['show','273d6012233f91ecca54e590d4d6e5af0c79d375:data/ownership-selection.json']));
const before=structuredClone(old),after=structuredClone(current);delete before.additive_release;delete after.additive_release;
assert.equal(JSON.stringify(before),JSON.stringify(after));
const reader=()=>new ImmutableReader(root,version),call=selection=>{const r=reader(),manifest=r.json(selection.manifest_path,{expected:selection.sha256});return readArtifactConsumption(r,selection,manifest)};
const reordered=JSON.parse(execFileSync('git',['show','568bfa4c4042ba6f47c0c4558cb2bcf09a46895a:data/ownership-selection.json']));
assert.throws(()=>call(reordered),/Selected source\/policy\/qualification binding differs/);
const accepted=call(current);assert(accepted.certificate&&accepted.sourceCustody);
const side=read(current.additive_release.path);assert.equal(valueSha(side.base_selection),valueSha(nativeBaseSelection(current)));
const report={version:1,checks:3,original_pointer_insertion_order_preserved:true,original_failure_reproduced:true,actual_readArtifactConsumption_passed:true,adjacent_sidecar_canonical_base_binding_passed:true,source_critical_roles:accepted.sourceCustody.source_critical_roles,scientific_operator_replayed:false,pointer_sha256:createHash('sha256').update(fs.readFileSync('data/ownership-selection.json')).digest('hex')};
process.stdout.write(JSON.stringify(report,null,2)+'\n');

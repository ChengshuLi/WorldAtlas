import {ImmutableReader,SelectedGeometrySources} from '../../../scripts/check-effective-geographic-regression.mjs';
import {CURRENT_REBIND_CODE,nativeBaseSelection,requirePriorAdditiveConservation,normaliseRetainedRepairLedger,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {validateCurrentRebindPlan} from '../additive-native-composition-20261009/capture-current-rebind.mjs';

const demand=(value,message)=>{if(!value)throw Error(message);};
const INPUT_DESCRIPTION='coordination/engineering/additive-native-activation-20261009/retained-activation-inputs.json';
const BINDINGS='coordination/engineering/additive-native-activation-20261009/original-target-source-bindings.json';
const PREDECESSOR='coordination/engineering/additive-native-composition-20261009/predecessor-native/selected-native-proof-original.json';

// A data preparation step for the already merged cold entry. It does not mint
// source authority, acquire native words, qualify operating limits or activate
// selection. Actual operating/source custody remains in the existing protocol.
export function prepareSupportedRebindPlan({reader,snapshot,executedCode,originalPatches,limits,
  inputDescriptionPath=INPUT_DESCRIPTION,targetBindingsPath=BINDINGS}) {
  demand(reader instanceof ImmutableReader&&snapshot?.reader===reader,'Actual selected immutable reader required');
  const resolver=new SelectedGeometrySources(snapshot);
  demand(snapshot.manifest.size===262166&&snapshot.manifest.method==='native-linear-evenodd-first-owner-v1'
    &&snapshot.manifest.provenance?.successor_continuation?.issue===1520,
    'Actual selected Arctic successor required; v8/pending draft is not a final activation base');
  const description=reader.json(inputDescriptionPath),bindings=reader.json(targetBindingsPath);
  demand(description.version===1&&description.kind==='retained-additive-activation-input-description-v1'
    &&description.original_inputs.length===2,'Complete retained input description required');
  const original=description.original_inputs.map(pin=>{
    demand(pin.mode==='100644'&&pin.bytes<=33554432,'Ordinary complete original input required');
    const actual=reader.descriptor(pin.path,pin.commit);
    demand(actual.git_blob_oid===pin.git_blob_oid&&actual.bytes===pin.bytes&&actual.mode===pin.mode,'Original input mode/OID/size differs');
    return reader.json(pin.path,{version:pin.commit,expected:pin.sha256});
  });
  const [registry,ledger]=original;
  requirePriorAdditiveConservation(snapshot,registry,ledger);
  demand(registry.kind==='retained-rule-authority-registry-v1'
    &&JSON.stringify(description.original_scope_ids)===JSON.stringify(ledger.scope_ids),'Original complete scope/order changed');
  const rows=[...normaliseRetainedRepairLedger(ledger,registry).rows.values()];
  demand(JSON.stringify(rows.map(row=>row.component_id))===JSON.stringify(description.supported_scope_ids),
    'Retained supported component scope differs');
  const ids=new Set(rows.map(row=>row.target_id));
  demand(bindings.kind==='explicit-current-target-source-binding-readback'
    &&Array.isArray(bindings.source_bindings)&&bindings.source_bindings.length===ids.size
    &&new Set(bindings.source_bindings.map(p=>p.target_id)).size===ids.size
    &&bindings.source_bindings.every(p=>ids.has(p.target_id)&&resolver.paths.includes(p.path)),
    'Missing/foreign/duplicate original target-to-source mapping');
  demand(Array.isArray(originalPatches)&&originalPatches.length===registry.entries.length,
    'Whole original qualified patch roster required');
  const predecessor=reader.descriptor(PREDECESSOR);
  demand(predecessor.bytes===1990604,'Whole original Arctic proof required');
  const plan={version:1,kind:'issued-current-rebind-acquisition-plan-v1',execution_commit:reader.version,
    executed_code:executedCode,base_selection:nativeBaseSelection(snapshot.selection),authority_registry_sha256:valueSha(registry),
    original_rows_sha256:valueSha(rows),original_patch_sha256s:originalPatches.map(valueSha),
    target_sources:bindings.source_bindings,predecessor_proof:{...predecessor,
      sha256:'d8af3b2eaf77f4fa948c01937ccb107f3d7eaa833ea4bac1d4480c633d509794'},limits};
  demand(JSON.stringify(executedCode.map(p=>p.path))===JSON.stringify(CURRENT_REBIND_CODE),
    'Existing exact cold code closure required');
  validateCurrentRebindPlan(plan,{executionCommit:reader.version,baseSelection:nativeBaseSelection(snapshot.selection),
    registry,originalRows:rows,executedCode});
  return plan;
}

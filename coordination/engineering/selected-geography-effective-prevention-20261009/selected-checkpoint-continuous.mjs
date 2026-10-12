// Complete continuous operands from one private, authenticated joint transition.
// Coordinates remain the original whole features; the Python consumer applies
// each vintage's literal additions and its unchanged strict polygon predicates.
import {authenticateTransition, projectSourceFeatures} from './selected-checkpoint.mjs';
import {valueBytes, valueSha} from './selected-neighbor-prevention.mjs';

const FILE = 32 * 1024 * 1024;
const demand = (ok, message) => { if (!ok) throw Error(message); };

// Pure identity join only; it grants no checkpoint or transition authority.
export function completeContinuousFeatures(projection, ids) {
  const inverse = new Map(projection.inverse.map(row => [row.id, row]));
  demand(inverse.size === ids.length && projection.features.length === ids.length,
    'Continuous projection has missing or duplicate source records');
  const features = {};
  for (const feature of projection.features) {
    const id = feature.id ?? feature.properties?.id, row = inverse.get(id);
    demand(typeof id === 'string' && !Object.hasOwn(features, id) && row
      && valueSha(feature) === row.whole_feature_sha256
      && valueSha(feature.geometry) === row.geometry_sha256,
    'Continuous whole-feature/inverse identity differs');
    Object.defineProperty(features, id, {value:feature, enumerable:true});
  }
  demand(JSON.stringify(Object.keys(features).sort()) === JSON.stringify(ids),
    'Continuous projection omitted the complete affected-neighbor closure');
  return features;
}

export function checkpointContinuousOperands({transition, budget}) {
  // Reserve the complete output plus its canonical JSON object/string copies
  // before any source projection. Use the shared qualifier's conservative
  // seven-byte representation allowance; its own retained state is separate.
  authenticateTransition({transition, budget});
  budget.carriedBytes += 7 * FILE;
  const {baseline, candidate, plan} = authenticateTransition({transition, budget});
  const before = projectSourceFeatures({state:baseline, ids:plan.required_ids, budget});
  const after = projectSourceFeatures({state:candidate, ids:plan.required_ids, budget, reuse:before});
  demand(valueSha(before.state_binding) === valueSha(plan.source_bindings.baseline)
    && valueSha(after.state_binding) === valueSha(plan.source_bindings.candidate),
  'Continuous source projection vintage differs from qualified transition');
  const operands = {version:1, kind:'complete-selected-continuous-operands-v1', plan,
    effective_additions:{baseline:baseline.additions, candidate:candidate.additions},
    baseline:completeContinuousFeatures(before, plan.required_ids), candidate:completeContinuousFeatures(after, plan.required_ids)};
  const order = (a,b) => a.source < b.source ? -1 : a.source > b.source ? 1 : a.ordinal - b.ordinal;
  const inverse = [['baseline', before], ['candidate', after]].flatMap(([vintage, projection]) =>
    [...projection.inverse].sort(order).map(row => ({vintage, ...row})));
  const custody = {baseline:{state_binding:before.state_binding, inputs:before.inputs, ...before.custody},
    candidate:{state_binding:after.state_binding, inputs:after.inputs, ...after.custody},
    source_features_reused:before.features === after.features};
  demand(2 * valueBytes({operands, inverse, custody}).length < FILE,
    'Complete checkpoint continuous products exceed original output reserve');
  return {operands, inverse, custody, complete_owners:baseline.certificate.entries.length,
    baseline_execution:baseline.accepted_execution, candidate_execution:candidate.accepted_execution};
}

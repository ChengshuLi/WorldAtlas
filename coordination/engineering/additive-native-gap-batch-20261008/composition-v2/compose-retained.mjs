// Compose complete previously qualified scopes. This does not select a bank or
// grant source authority: the committed selected reader authenticates registry.
import {normaliseRetainedRepairLedger, compareVersionedRepairLedgers, valueSha, valueBytes}
  from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const demand=(ok,message)=>{if(!ok)throw Error(message);};
const same=(a,b)=>valueBytes(a).equals(valueBytes(b));
export function composeRetainedLedgers(members,registry) {
  demand(Array.isArray(members)&&members.length>0,'Missing complete original ledgers');
  const rows=new Map();let parent;
  for(const ledger of members){
    const normalized=normaliseRetainedRepairLedger(ledger,registry);
    if(parent===undefined)parent=ledger.parent_inventory;
    demand(parent&&same(parent,ledger.parent_inventory),'Original inventory denominator differs');
    const entries=registry.entries.filter(entry=>entry.rule_sha256===ledger.rule_sha256);
    demand(ledger.version===1&&entries.length===1,'Require an unambiguous original v1 member authority');
    const entry=entries[0];
    for(const row of ledger.rows){
      demand(!rows.has(row.component_id),'Duplicate original component across complete scopes');
      rows.set(row.component_id,normalized.rows.get(row.component_id)??{
        ...row,authority_sha256:entry.authority_sha256,rule_sha256:entry.rule_sha256});
    }
  }
  const ordered=[...rows.values()].sort((a,b)=>a.component_id.localeCompare(b.component_id));
  const result={version:2,kind:'native-additive-repair-ledger-v2',
    authority_registry_sha256:valueSha(registry),parent_inventory:parent,
    scope_ids:ordered.map(row=>row.component_id),rows:ordered};
  // Normalize actual output and prove every complete effective original row is
  // conserved. Rejected/unresolved rows are also preserved literally above.
  normaliseRetainedRepairLedger(result,registry);
  for(const member of members)compareVersionedRepairLedgers(member,result,{beforeRegistry:registry,afterRegistry:registry});
  return result;
}

// The trusted reader owns this exact pure applicability method.
export {conserveCurrentNativeRows} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

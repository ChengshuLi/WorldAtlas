// Exact coordinate-delta preimage from ee6bceb0d005b3700f585009b9841c11dcb584aa.
import {repairComponentKey,nativeOnlyComponent} from '../../src/native-grid.js';
import {valueSha,coordinateBounds} from '../../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const demand=(ok,message)=>{if(!ok)throw Error(message);};
const same=(a,b)=>a===undefined||b===undefined?a===b:valueSha(a)===valueSha(b);
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
export function deriveCoordinateDelta({certificate,oldAdditions,additions,selection}) {
  const oldById=new Set(oldAdditions.map(repairComponentKey));
  demand(oldById.size===oldAdditions.length && new Set(additions.map(repairComponentKey)).size===additions.length,
    'Duplicate complete primitive identity');
  for (const row of oldAdditions) demand(same(row,additions.find(p => repairComponentKey(p)===repairComponentKey(row))),
    'Old effective primitive/base geometry changed');
  const rows=new Map(certificate.entries.map(row => [row[0],row]));
  for (const row of additions) demand(rows.has(row.target_id) && row.pixelIndex===rows.get(row.target_id)[1]
    && row.base_geometry_sha256===rows.get(row.target_id)[7] && (nativeOnlyComponent(row,valueSha) || row.geometry_sha256===valueSha(row.geometry)),
  'Appended primitive targets a stale base, changed geometry or different owner');
  const changedIds=new Set(additions.filter(row => !oldById.has(repairComponentKey(row))).map(row => row.target_id));
  const entries=certificate.entries.map(row => {
    if (!changedIds.has(row[0])) return row;
    const all=additions.filter(p => p.target_id===row[0]), added=all.filter(p => !oldById.has(repairComponentKey(p)));
    const bounds=(a,b)=>[Math.min(a[0],b[0]),Math.min(a[1],b[1]),Math.max(a[2],b[2]),Math.max(a[3],b[3])];
    let box=row[9].reduce(bounds);
    for(const p of added)for(const next of nativeOnlyComponent(p,valueSha)?[p.native_bounds]:coordinateBounds(p.geometry))box=bounds(box,next);
    const next=[...row]; next[8]=valueSha({base_geometry_sha256:row[7],additions:all});
    next[9]=[box];
    return next;
  });
  const result={...certificate,binding:{...certificate.binding,selection},entries};
  return freeze({certificate:result,changedIds:[...changedIds].sort()});
}

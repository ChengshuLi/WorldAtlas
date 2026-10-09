import assert from 'node:assert/strict';
import fs from 'node:fs';
// Exact production function extraction: sparse author checkout lacks the old full import closure.
const source=fs.readFileSync('coordination/engineering/eastern-two-gap-repair-native-20261007/chained-context.mjs','utf8');
const body=source.slice(source.indexOf('export function verifyRegistryContinuation('),source.indexOf('export function verifyAuthoredValidatorSources('));
const verifyRegistryContinuation=Function('assert',body.replace('export function','function')+';return verifyRegistryContinuation;')(assert);
const originalRaw=fs.readFileSync('scripts/native-ownership/verified-candidates.json'),original=JSON.parse(originalRaw);
const binding={manifest_sha256:'1'.repeat(64),pin:{commit:'2'.repeat(40),path:'coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/native-selection-receipt.json',sha256:'3'.repeat(64),role:'reviewed-exhaustive-native-rule-comparison',installation_approval:false}};
const current={...original,candidates:{...original.candidates,[binding.manifest_sha256]:binding.pin}};
assert.equal(verifyRegistryContinuation(originalRaw,Buffer.from(JSON.stringify(current)),binding).original_entries,Object.keys(original.candidates).length);
let negative=0;function reject(value,b= binding){assert.throws(()=>verifyRegistryContinuation(originalRaw,Buffer.from(JSON.stringify(value)),b));negative++;}
reject(original);assert.throws(()=>verifyRegistryContinuation(originalRaw,Buffer.from(JSON.stringify(current)),undefined));negative++;reject({...current,version:2});reject({...current,extra:true});
const oldKey=Object.keys(original.candidates)[0];reject({...current,candidates:{...current.candidates,[oldKey]:{...original.candidates[oldKey],sha256:'4'.repeat(64)}}});
const removed=structuredClone(current);delete removed.candidates[oldKey];reject(removed);
reject({...current,candidates:{...current.candidates,['5'.repeat(64)]:binding.pin}});
reject(current,{...binding,pin:{...binding.pin,path:'../foreign.json'}});
console.log(JSON.stringify({positive:1,negative,original_entries_preserved:Object.keys(original.candidates).length,limit:'Fixture new pin only; no registration or whole caller qualification'}));

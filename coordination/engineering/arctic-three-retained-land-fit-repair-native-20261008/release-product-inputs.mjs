// Typed ordinary-application input expansion. This carries complete qualified
// product pins; it does not replace any registry, codec or scientific method.
import assert from 'node:assert/strict';
const PREFIX='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/release-v9/';
export function completeReleaseProductInputs(certificate,catalogue){
 assert.equal(catalogue.version,1);assert.equal(catalogue.kind,'qualified-arctic-release-product-roster-v1');assert.equal(catalogue.issue,1520);
 assert(Array.isArray(catalogue.products)&&catalogue.products.length===343);
 const original=certificate.application_inputs;assert(Array.isArray(original));
 const key=p=>(p.space??'root')+':'+p.path;
 assert.equal(new Set(original.map(key)).size,original.length);
 const declared=original.find(p=>key(p)===key(certificate.release_product_catalogue));assert(declared);
 for(const field of ['mode','bytes','sha256','decoded_bytes','decoded_sha256'])assert.equal(declared[field],certificate.release_product_catalogue[field]);
 const names=new Set(original.map(key));
 for(const pin of catalogue.products){
  assert.equal(pin.space??'root','root');assert.equal(pin.mode,'100644');
  assert(typeof pin.path==='string'&&pin.path.startsWith(PREFIX)&&!pin.path.includes('\\'));
  assert(pin.path.split('/').every(p=>p&&p!=='.'&&p!=='..'));
  for(const field of ['bytes','decoded_bytes'])assert(Number.isSafeInteger(pin[field])&&pin[field]>0&&pin[field]<=32*1024*1024);
  for(const field of ['sha256','decoded_sha256'])assert(/^[a-f0-9]{64}$/.test(pin[field]));
  assert(!names.has(key(pin)),'Duplicate or undeclared product alias');names.add(key(pin));
 }
 return [...original,...catalogue.products];
}

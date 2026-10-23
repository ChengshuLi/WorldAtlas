// Captured metadata/body contract for policy tests. This is not a Git checkout:
// descriptors authenticate identities without claiming unread bodies are present.
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const oid=bytes=>createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
const safe=name=>typeof name==='string'&&/^[A-Za-z0-9_./-]+$/.test(name)&&
  !name.startsWith('/')&&name.split('/').every(part=>part&&part!=='.'&&part!=='..');
export function createHistoryReader(value) {
  assert.equal(value.version,1);
  assert.match(value.source_commit,/^[a-f0-9]{40}$/);
  assert(Array.isArray(value.entries)&&Array.isArray(value.bodies));
  const entries=new Map(),bodies=new Map();
  for(const row of value.entries) {
    assert(safe(row.path),'Safe captured path required');
    assert.equal(row.type,'blob');assert.equal(row.mode,'100644');
    assert.match(row.sha,/^[a-f0-9]{40}$/);
    assert(Number.isSafeInteger(row.size)&&row.size>=0,'Exact captured body size required');
    assert(!entries.has(row.path),'Duplicate captured path');
    entries.set(row.path,Object.freeze({...row}));
  }
  for(const row of value.bodies) {
    assert.match(row.sha,/^[a-f0-9]{40}$/);
    assert(!bodies.has(row.sha),'Duplicate captured body');
    const raw=Buffer.from(row.base64,'base64');
    assert.equal(raw.toString('base64'),row.base64,'Canonical captured body encoding required');
    assert.equal(oid(raw),row.sha,'Captured Git body identity differs');
    const roles=[...entries.values()].filter(entry=>entry.sha===row.sha);
    assert(roles.length,'Captured body must have an authenticated descriptor');
    for(const role of roles)assert.equal(raw.length,role.size,'Captured descriptor size differs');
    bodies.set(row.sha,raw);
  }
  return Object.freeze({sourceCommit:value.source_commit,
    entry(name) {assert(safe(name),'Safe captured path required');const row=entries.get(name);return row&&{...row};},
    readBlob(sha) {assert.match(sha,/^[a-f0-9]{40}$/);assert(bodies.has(sha),'Body absent from isolated contract fixture: '+sha);return Buffer.from(bodies.get(sha));},
    readFile(name) {const row=this.entry(name);assert(row,'Path absent from isolated contract fixture: '+name);return this.readBlob(row.sha);},
    hasBody(sha) {return bodies.has(sha);},
    bodyOids() {return [...bodies.keys()];}
  });
}
export function openSelectedHistory({bytes=fs.readFileSync(new URL('./selected-data-history.json.gz',import.meta.url)),
  pin=JSON.parse(fs.readFileSync(new URL('./selected-data-history.json',import.meta.url)))}={}) {
  assert.equal(pin.version,1);
  assert.equal(bytes.length,pin.bytes,'Captured fixture size differs');
  assert.equal(hash(bytes),pin.sha256,'Captured fixture hash differs');
  const value=JSON.parse(gunzipSync(bytes));
  assert.equal(value.source_commit,pin.source_commit,'Captured source identity differs');
  assert.equal(value.entries?.length,pin.descriptors,'Captured descriptor inventory differs');
  assert.equal(value.bodies?.length,pin.bodies,'Captured body inventory differs');
  return createHistoryReader(value);
}
let retained;
export const selectedHistory=()=>retained??=openSelectedHistory();

// Job-local exact byte inverse of the measured copy-range/literal representation.
// Derived from root1394 runtime.py apply_delta, whole SHA
// 69ab4085c780021d92b7eb6b2b3a3db7ef1992b0b208d401edd81478398aa6ab.
// That source was uncommitted review preparation, not an accepted scientific run.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
export const BYTE_CAP = 32 * 1024 * 1024;
export const byteSha = body => createHash('sha256').update(body).digest('hex');
const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
export function verifyWholeBytes(body, pin) {
  assert(Buffer.isBuffer(body));
  assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && pin.bytes <= BYTE_CAP);
  assert(hash(pin.sha256) && ['100644','100755'].includes(pin.mode));
  assert.equal(body.length,pin.bytes);assert.equal(byteSha(body),pin.sha256);
  return body;
}
export function applyBytePatch(commands, target, source) {
  assert(Array.isArray(commands) && commands.length > 0);
  assert(Number.isSafeInteger(target.bytes) && target.bytes >= 0 && target.bytes <= BYTE_CAP);
  assert(hash(target.sha256) && ['100644','100755'].includes(target.mode));
  const pieces=[];let bytes=0;
  for(const command of commands) {
    assert(command && typeof command === 'object' && !Array.isArray(command));
    assert.equal(Object.keys(command).length,1);
    let chunk;
    if(Object.hasOwn(command,'copy')) {
      const row=command.copy;assert(Array.isArray(row) && row.length===3);
      const [name,offset,length]=row;
      assert(typeof name==='string' && name.length>0);
      assert(Number.isSafeInteger(offset) && Number.isSafeInteger(length) && offset>=0 && length>0);
      assert(length<=target.bytes-bytes,'Copy exceeds exact remaining output before lookup');
      const original=source(name);assert(Buffer.isBuffer(original) && original.length<=BYTE_CAP);
      assert(offset<=original.length && length<=original.length-offset,'Escaped source copy range');
      chunk=original.subarray(offset,offset+length);
    }else {
      assert(Object.hasOwn(command,'literal') && typeof command.literal==='string');
      const encoded=command.literal;
      assert(encoded.length%4===0 && /^[A-Za-z0-9+/]*={0,2}$/.test(encoded));
      const decoded=encoded.length/4*3-(encoded.endsWith('==')?2:encoded.endsWith('=')?1:0);
      assert(decoded<=target.bytes-bytes,'Literal exceeds exact remaining output before allocation');
      chunk=Buffer.from(encoded,'base64');assert.equal(chunk.length,decoded);assert.equal(chunk.toString('base64'),encoded);
    }
    bytes+=chunk.length;assert(bytes<=target.bytes);pieces.push(chunk);
  }
  assert.equal(bytes,target.bytes,'Incomplete complete-byte inverse');
  return verifyWholeBytes(Buffer.concat(pieces,bytes),target);
}

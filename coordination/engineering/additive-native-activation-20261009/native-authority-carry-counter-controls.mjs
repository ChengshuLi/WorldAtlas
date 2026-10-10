import assert from 'node:assert/strict';import fs from 'node:fs';
const source=fs.readFileSync(new URL('../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',import.meta.url),'utf8');
const a=source.indexOf(' const carryBytes=value=>{'),z=source.indexOf('\n const sourceCarry=',a);assert(a>=0&&z>a);
const demand=(v,m)=>{if(!v)throw Error(m);};
const carryBytes=new Function('demand','FILE',source.slice(a,z)+';return carryBytes;')(demand,33554432);
for(const value of [null,{s:'é\u0000😀',a:[0,true,null,'quote\"']},new Map([['α',{x:2}]])]){assert(carryBytes(value)>=2*Buffer.byteLength(JSON.stringify(value instanceof Map?[...value]:value)));}
const cycle={};cycle.self=cycle;assert.throws(()=>carryBytes(cycle));assert.throws(()=>carryBytes(new Date()));assert.throws(()=>carryBytes({x:Infinity}));assert.throws(()=>carryBytes('a'.repeat(6000000)));console.log('counter PASS3 conservative size cases+4 refusals; current production counter extracted literal');

import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const html=readFileSync(new URL('../web/index.html',import.meta.url),'utf8');
const source=html.slice(html.indexOf('function keyboardAction('),html.indexOf("window.addEventListener('keydown'"));
const state={};runInNewContext(source,state);
const action=(key,extra={})=>state.keyboardAction({key,...extra});
test('plus, minus and WASD shortcuts',()=>{
 for(const [key,expected] of [['+','in'],['=','in'],['-','out'],['_','out'],['w','north'],['W','north'],['a','west'],['s','south'],['d','east']])assert.equal(action(key),expected);
});
test('does not hijack browser shortcuts or editable fields',()=>{
 for(const extra of [{ctrlKey:true},{metaKey:true},{altKey:true},{isComposing:true},{defaultPrevented:true},{target:{closest:()=>({})}}]) assert.equal(action('w',extra),null);
 assert.equal(action('x'),null);
});

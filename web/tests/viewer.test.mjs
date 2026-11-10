import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import vm from 'node:vm';
import {cellValue,wrapColumn,validateGrid} from '../viewer/grid-data.js';
import {renderPixels} from '../viewer/grid-renderer.js';
import * as legend from '../viewer/legend-model.js';
const read=f=>fs.readFileSync(new URL('../viewer/'+f,import.meta.url),'utf8');
const fixtureCategories = [
  'Africa', 'Asia', 'Europe', 'North America', 'South America', 'Oceania',
  'Atlantic Ocean', 'Pacific Ocean', 'Indian Ocean', 'Arctic Ocean',
].map((name, index) => ({
  id: index + 1, entity_id: index + 1, name, physical_class: 'water',
}));
fixtureCategories.push({
  id: 17, entity_id: 1, name: 'Africa', physical_class: 'land', rgb: [233, 180, 76],
});
class Element{constructor(id=''){this.id=id;this.hidden=false;this.textContent='';this.value='';this.style={};this.attrs={};this.handlers={};this.children=[];this.classList={add(){},remove(){},toggle(){}};this.clientWidth=1000;this.clientHeight=600}addEventListener(t,f){(this.handlers[t]??=[]).push(f)}dispatch(t,e={}){e.target??=this;e.preventDefault??=()=>{e.prevented=true};for(const f of this.handlers[t]||[])f(e);return e}setAttribute(k,v){this.attrs[k]=v}append(...x){this.children.push(...x)}replaceChildren(...x){this.children=[...x]}focus(){this.focused=true}setPointerCapture(){}}
async function fixture(){const names=['map','canvas','status','selection','legend-list','legend-search','legend-clear','legend-panel','legend-toggle','legend-collapse','tool-in','tool-out','tool-world'];const el=Object.fromEntries(names.map(x=>[x,new Element(x)]));el['legend-toggle'].hidden=true;el['legend-clear'].hidden=true;const draws=[];const document={querySelector:s=>el[s.slice(1)],createElement:()=>new Element(),body:new Element('body'),handlers:{},hidden:false,addEventListener(t,f){this.handlers[t]=f},removeEventListener(t){delete this.handlers[t]}};const timers=new Map();let timerId=0;const setTimeout=(fn,ms)=>{assert.equal(ms,5000);timers.set(++timerId,fn);return timerId};const clearTimeout=id=>timers.delete(id);const meta={...JSON.parse(read('config.json')),width:131072,height:54614,step:360/131072,legend:'legend/continents.json',categories:fixtureCategories.map(({id,entity_id,physical_class})=>({id,entity_id,physical_class}))};const rows=Uint32Array.from({length:meta.height+1},(_,i)=>i);const runs=new Uint32Array(meta.height*2);for(let i=0;i<meta.height;i++){runs[2*i]=meta.width;runs[2*i+1]=17}const loadLocalGrid=async()=>({rows,runs});const entries=fixtureCategories.filter(c=>c.physical_class==='water').map(c=>({id:c.entity_id,name:c.name,color:c.id===1?[233,180,76]:meta.water_rgb,count:123}));const fetch=async url=>new Response(JSON.stringify(String(url).endsWith('legend/continents.json')?entries:meta));const createRenderer=()=>({draw:x=>draws.push({...x}),destroy(){}});const ResizeObserver=class{constructor(f){this.f=f}observe(){this.f()}};let app=read('app.js').replace(/^import .*\n/gm,'').replace('import.meta.url',"'https://example.test/review/current/app.js'");const ctx={cellValue,wrapColumn,loadLocalGrid,...legend,createRenderer,document,fetch,URL,Response,location:{href:'https://example.test/'},devicePixelRatio:1,ResizeObserver,setTimeout,clearTimeout,requestAnimationFrame:f=>f(),window:{addEventListener(){}},console,Set,Math};vm.createContext(ctx);await vm.runInContext('(async()=>{'+app+'})()',ctx);return {el,draws,document,timers}}
test('current map controls preserve selection, toggle legend and reset world',async()=>{const {el,draws,document}=await fixture();assert.equal(el.status.textContent,'');assert.equal(el['legend-list'].children.length,10);assert.equal(el['legend-toggle'].hidden,true);el.canvas.dispatch('pointerdown',{pointerId:1,offsetX:500,offsetY:300});assert.equal(el.canvas.focused,true);el.canvas.dispatch('pointerup',{pointerId:1,offsetX:500,offsetY:300});const selected=el.selection.textContent;assert.match(selected,/^Cell 65536, 27307 · 14\.99771°, 0\.00137° · Africa \(land\)$/);assert.doesNotMatch(selected,/longitude|latitude/i);el.canvas.dispatch('pointermove',{pointerId:2,offsetX:100,offsetY:100});assert.equal(el.selection.textContent,selected);el['legend-collapse'].dispatch('click');assert.equal(el['legend-panel'].hidden,true);assert.equal(el['legend-toggle'].hidden,false);el['legend-toggle'].dispatch('click');assert.equal(el['legend-panel'].hidden,false);assert.equal(el['legend-toggle'].hidden,true);el['tool-in'].dispatch('click');const zoomed=draws.at(-1).scale;const tab=el.canvas.dispatch('keydown',{key:'Tab'});const reset=draws.at(-1);assert.equal(tab.prevented,true);assert.ok(reset.scale<zoomed);el['tool-in'].dispatch('click');el['tool-world'].dispatch('click');assert.deepEqual([draws.at(-1).scale,draws.at(-1).ox,draws.at(-1).oy],[reset.scale,reset.ox,reset.oy]);assert.equal(document.handlers.keydown,undefined);assert.equal(el['tool-in'].handlers.keydown,undefined);assert.equal(el.canvas.dispatch('keydown',{key:'Tab',shiftKey:true}).prevented,undefined);el['legend-list'].children[0].dispatch('click');assert.notEqual(draws.at(-1).activeMask,0)});
test('structure, checksum and small native-grid renderer',()=>{const html=read('index.html'),meta=JSON.parse(read('config.json'));assert.doesNotMatch(html,/<aside|id="v2"|id="jump"|Map legend ·|Select any continents/);assert.match(html,/aria-label="Collapse legend"/);assert.doesNotMatch(html,/id="startup-credit"/);assert.match(html,/aria-label="World assignment map\. Click to select a cell\."/);assert.doesNotMatch(html.match(/<header>[\s\S]*?<\/header>/)[0],/OpenStreetMap/);assert.match(read('sources.html'),/OpenStreetMap contributors/);assert.doesNotMatch(read('sources.html'),/© OpenStreetMap/);assert.match(html,/id="map-release"/);assert.doesNotMatch(html,/<details/);assert.match(html,/href="sources\.html"/);assert.doesNotMatch(read('sources.html'),/Partial source summary|approximate replacement|Iceland|SHA-256/);assert.doesNotMatch(read('app.js'),/document\.addEventListener\('keydown'/);assert.deepEqual(meta,{water_rgb:[84,141,183]});const small={width:4,height:2,local_grid:{run_count:4},palette:Array.from({length:32},(_,i)=>[i,i,i])},data={rows:new Uint32Array([0,2,4]),runs:new Uint32Array([2,1,4,2,1,3,4,4])};validateGrid(small,data.rows,data.runs);assert.equal(cellValue(data.rows,data.runs,3,0),2);assert.equal(renderPixels(small,data,4,2,1,0,0).length,8)});
test('legend hover brightens another entity without changing the selection outline', async () => {
  const {el, draws} = await fixture();
  const buttons = () => el['legend-list'].children;
  buttons()[0].dispatch('click');
  const africa = (1 << 1) | (1 << 17);
  const asia = 1 << 2;
  assert.equal(draws.at(-1).activeMask, africa);
  assert.equal(draws.at(-1).outlineMask, africa);

  buttons()[1].dispatch('pointerenter');
  assert.equal(draws.at(-1).activeMask, africa | asia);
  assert.equal(draws.at(-1).outlineMask, africa);
  assert.equal(buttons()[1].attrs['aria-pressed'], 'false');

  buttons()[1].dispatch('pointerleave');
  assert.equal(draws.at(-1).activeMask, africa);
  assert.equal(draws.at(-1).outlineMask, africa);
});
test('viewer uses assets relative to its release bundle',()=>{const html=read('index.html');assert.doesNotMatch(html,/location\.replace/);assert.match(html,/type="module" src="app\.js"/)});

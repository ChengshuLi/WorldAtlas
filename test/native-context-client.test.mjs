import test from 'node:test';
import assert from 'node:assert/strict';
import {prepareNativeLocationContext} from '../src/native-context-client.js';
import {NATIVE_METHOD} from '../src/ownership-method.js';
const feature={id:'reference:A',pixelIndex:8192};
const input={referenceFeatures:[feature],features:[feature]};
function fake(){
 const worker={terminated:0,postMessage(message){this.request=message;},terminate(){this.terminated++;},emit(data){this.onmessage({data});}};
 return worker;
}
const grid=()=>({version:2,size:262166,coordinateBits:19,method:NATIVE_METHOD,rows:new Uint32Array(524332),runs:new Uint32Array(0)});
const owners=[{index:1,id:feature.id,referenceIndex:8192}];
test('native selection waits for matching worker result and terminates after ready',async()=>{
 const worker=fake(),progress=[];
 const ready=prepareNativeLocationContext(input,{workerFactory:()=>worker,onProgress:value=>progress.push(value)});
 const revision=worker.request.revision;
 worker.emit({revision:revision-1,grid:grid(),owners});
 worker.emit({revision,progress:{recomputedRows:7}});
 assert.equal(worker.terminated,0);
 worker.emit({revision,grid:grid(),owners,accounting:{recomputedRows:7}});
 const result=await ready;
 assert.deepEqual(result.context.owners,owners);assert.equal(result.context.features[0],feature);
 assert.equal(worker.terminated,1);assert.deepEqual(progress,[{recomputedRows:7}]);
});
test('selection abort stops actual worker lifecycle and ignores late result',async()=>{
 const worker=fake(),controller=new AbortController();
 const ready=prepareNativeLocationContext(input,{workerFactory:()=>worker,signal:controller.signal});
 controller.abort();await assert.rejects(ready,{name:'AbortError'});assert.equal(worker.terminated,1);
 worker.emit({revision:worker.request.revision,grid:grid(),owners});assert.equal(worker.terminated,1);
});
test('malformed grid, changed display identity, worker failure and callback failure reject without ready map',async()=>{
 for(const response of [{grid:grid(),owners:[{...owners[0],id:'wrong'}]},
  {grid:{...grid(),method:'legacy'},owners},{grid:{...grid(),rows:new Uint32Array(2)},owners},
  {error:'Rejected changed native geometry',errorName:'Error'}]){
  const worker=fake(),ready=prepareNativeLocationContext(input,{workerFactory:()=>worker});
  worker.emit({...response,revision:worker.request.revision});
  await assert.rejects(ready);assert.equal(worker.terminated,1);
 }
 const worker=fake(),ready=prepareNativeLocationContext(input,{workerFactory:()=>worker,onProgress:()=>{throw Error('progress failure');}});
 worker.emit({revision:worker.request.revision,progress:{}});
 await assert.rejects(ready,/progress failure/);assert.equal(worker.terminated,1);
});

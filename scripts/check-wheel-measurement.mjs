import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {wheelTiming} from './wheel-measurement.mjs';
const directory=process.argv[2];if(!directory)throw Error('Provide owned evidence directory');
const fixed=time=>({time,transform:'identity',pane:'identity',frame:'old'});
const positive={frames:[0,16,32,48],events:[{time:20}],transforms:[fixed(0),fixed(16),{...fixed(32),transform:'scaled'},fixed(48)]};
assert.equal(wheelTiming(positive).first_observed_transform_ms,12);
assert.equal(wheelTiming(positive).raf_p95_ms,16);
const negative={frames:[0,16,32,100],events:[{time:20}],transforms:[fixed(0),fixed(16),fixed(32),fixed(100)]};
assert.equal(wheelTiming(negative).first_observed_transform_ms,null);
assert.equal(wheelTiming(negative).frames_over_34ms,1);
const noInput={...positive,events:[]};assert.equal(wheelTiming(noInput).first_observed_transform_ms,null);
for(const [kind,inputs] of [['positive-control',[positive]],['negative-control',[negative,noInput]]]){
 fs.mkdirSync(directory,{recursive:true});
 fs.writeFileSync(path.join(directory,kind+'.json'),JSON.stringify({method_id:'wheel-observation',kind,outcome:'passed',inputs,results:inputs.map(wheelTiming),limit:'Synthetic timing-control vectors validate the arithmetic/detection method; they do not certify input-to-photon latency or physical devices.'},null,2)+'\n');
}
console.log('Known delayed-change and unchanged/no-input controls passed');

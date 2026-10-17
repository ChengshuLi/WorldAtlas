import fs from 'node:fs';import {pathToFileURL,fileURLToPath} from 'node:url';
const checkout=fileURLToPath(new URL('../../../',import.meta.url));
const {compareNativeAdditiveIntervals}=await import(pathToFileURL(checkout+'/scripts/selected-checkpoint-native.mjs'));
const n=Number(process.argv[2]),size=n*2+2,owners=[{id:'A'},{id:'B'}];if(!Number.isSafeInteger(n)||n<1)throw Error('positive intervals');
let visited=0;async function* base(){for(let i=0;i<n;i++){visited++;yield [i*2,i*2+1,1];}}
const before=[[size-1,size,2]],after=[];global.gc?.();const initial=process.memoryUsage(),start=performance.now();
const result=await compareNativeAdditiveIntervals(base(),{y:0,before,after,size,owners});
if(visited!==n||result.checked_rows!==1||result.lost_or_reassigned_cells!==1||result.intervals.length!==1||result.intervals[0].start!==size-1)throw Error('dense row result mismatch');
console.log(JSON.stringify({intervals:n,rows:1,size,visited,result,milliseconds:performance.now()-start,initial,final:process.memoryUsage(),maxRSS_KiB:process.resourceUsage().maxRSS},null,2));

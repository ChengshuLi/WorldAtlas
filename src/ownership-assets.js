import {unshuffleOwnershipBytes,decodeOwnershipVarints} from './ownership-codec.js';
// Versioned static ownership assets. Uint32 words are encoded little-endian.
export async function loadOwnershipAssets(manifest,fetcher=fetch){
  if(manifest.version!==1&&manifest.version!==2)throw new Error('Unsupported ownership asset version');
  const coordinateBits=Math.ceil(Math.log2(manifest.size)),wordsPerRun=manifest.version===2?2:4;
  if(!Number.isInteger(manifest.size)||manifest.size<2||manifest.size>2**31||!Number.isSafeInteger(manifest.runWords)||manifest.runWords<0||manifest.runWords%wordsPerRun||(manifest.version===2&&manifest.coordinateBits!==coordinateBits)||!Array.isArray(manifest.parts))throw Error('Invalid ownership manifest');
  const output={version:manifest.version,coordinateBits,size:manifest.size,rows:new Uint32Array(manifest.size*2),runs:new Uint32Array(manifest.runWords)};
  for(const kind of ['rows','runs']){
    let offset=0;
    for(const part of manifest.parts.filter(p=>p.kind===kind).sort((a,b)=>a.offset-b.offset)){
      if(!Number.isSafeInteger(part.offset)||!Number.isSafeInteger(part.words)||part.words<=0||part.offset!==offset||!part.path)throw Error('Incomplete or overlapping ownership assets');
      offset+=part.words;
    }
    if(offset!==output[kind].length)throw Error('Incomplete ownership assets');
  }
  if(manifest.parts.some(p=>p.kind!=='rows'&&p.kind!=='runs'))throw Error('Unknown ownership asset kind');
  const loadPart=async part=>{
    const response=await fetcher(`./${part.path}`);if(!response.ok)throw new Error('Pixel map could not load');
    const compressed=new Uint8Array(await response.arrayBuffer());
    const raw=compressed[0]===31&&compressed[1]===139?await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():compressed.buffer;
    let words;
    if(part.encoding==='byte-shuffle')words=unshuffleOwnershipBytes(new Uint8Array(raw),part.words);
    else if(part.encoding==='row-varint'){
      if(part.kind!=='runs'||manifest.version!==2)throw Error('Varint transport requires compact ownership runs');
      words=decodeOwnershipVarints(new Uint8Array(raw),{rows:output.rows,offset:part.offset,words:part.words,coordinateBits,size:output.size});
    }else{
      if(part.encoding&&part.encoding!=='uint32-le')throw Error('Unsupported ownership transport encoding');
      if(raw.byteLength!==part.words*4)throw new Error('Incomplete ownership asset');words=new Uint32Array(raw);
    }
    output[part.kind].set(words,part.offset);
  };
  // Row-local delta streams depend on the complete immutable row table.
  await Promise.all(manifest.parts.filter(part=>part.kind==='rows').map(loadPart));
  await Promise.all(manifest.parts.filter(part=>part.kind==='runs').map(loadPart));
  let offset=0;
  for(let y=0;y<output.size;y++){
    if(output.rows[y*2]!==offset)throw Error('Invalid ownership row offset');
    offset+=output.rows[y*2+1];
    if(offset>output.runs.length/wordsPerRun)throw Error('Invalid ownership row bounds');
  }
  if(offset!==output.runs.length/wordsPerRun)throw Error('Unreferenced ownership runs');
  return output;
}

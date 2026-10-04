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
    const verify=async(bytes,expected)=>{if(!expected)return;const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');if(digest!==expected)throw Error('Ownership asset checksum mismatch');};
    const isCompressed=compressed[0]===31&&compressed[1]===139;
    // A host may already decode Content-Encoding:gzip. In that case the
    // reconstructed-word digest validates the exact same ownership values.
    if(isCompressed||!part.decoded_sha256)await verify(compressed,part.sha256);
    const raw=isCompressed?await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():compressed.buffer;
    let words;
    if(part.encoding==='byte-shuffle')words=unshuffleOwnershipBytes(new Uint8Array(raw),part.words);
    else if(part.encoding==='row-varint'){
      if(part.kind!=='runs'||manifest.version!==2)throw Error('Varint transport requires compact ownership runs');
      words=decodeOwnershipVarints(new Uint8Array(raw),{rows:output.rows,offset:part.offset,words:part.words,coordinateBits,size:output.size});
    }else{
      if(part.encoding&&part.encoding!=='uint32-le')throw Error('Unsupported ownership transport encoding');
      if(raw.byteLength!==part.words*4)throw new Error('Incomplete ownership asset');words=new Uint32Array(raw);
    }
    await verify(new Uint8Array(words.buffer,words.byteOffset,words.byteLength),part.decoded_sha256);
    output[part.kind].set(words,part.offset);
  };
  const loadParts=async parts=>{let next=0;await Promise.all(Array.from({length:Math.min(8,parts.length)},async()=>{while(next<parts.length)await loadPart(parts[next++]);}));};
  // Row-local delta streams depend on the complete immutable row table.
  await loadParts(manifest.parts.filter(part=>part.kind==='rows'));
  await loadParts(manifest.parts.filter(part=>part.kind==='runs'));
  let offset=0;
  for(let y=0;y<output.size;y++){
    if(output.rows[y*2]!==offset)throw Error('Invalid ownership row offset');
    offset+=output.rows[y*2+1];
    if(offset>output.runs.length/wordsPerRun)throw Error('Invalid ownership row bounds');
  }
  if(offset!==output.runs.length/wordsPerRun)throw Error('Unreferenced ownership runs');
  return output;
}

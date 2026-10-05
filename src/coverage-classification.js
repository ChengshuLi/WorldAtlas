import {unshuffleOwnershipBytes} from './ownership-codec.js';
import {ownershipRun,pickOwnership} from './pixel-ownership.js';

const hashPattern=/^[a-f0-9]{64}$/;
const MAX_WORDS=16000000,MAX_PART_BYTES=8*1024*1024;
const assert=(condition,message)=>{if(!condition)throw Error(message);};

// A physical reference is separate from location ownership. Reject stale pins
// before allocation; missing/corrupt products are handled as unknown by callers.
export function validateCoverageManifest(manifest,expected){
  assert(manifest?.kind==='physical-reference-classification'&&manifest.classification_version===1&&manifest.version===2,'Unsupported coverage classification');
  assert(Number.isInteger(manifest.size)&&manifest.size>=2&&manifest.size<=300000&&manifest.coordinateBits===Math.ceil(Math.log2(manifest.size)),'Invalid coverage grid');
  assert(Number.isSafeInteger(manifest.runWords)&&manifest.runWords>=0&&manifest.runWords<=MAX_WORDS&&manifest.runWords%2===0,'Coverage run budget exceeded');
  for(const key of ['footprints_sha256','hierarchy_sha256','canonical_grid_sha256']){
    assert(hashPattern.test(manifest[key])&&manifest[key]===expected?.[key],'Stale coverage classification: '+key);
  }
  assert(typeof manifest.release_id==='string'&&manifest.release_id===expected.release_id,'Coverage release mismatch');
  assert(manifest.size===expected.size&&manifest.coordinateBits===expected.coordinateBits,'Coverage grid mismatch');
  assert(Array.isArray(manifest.sources)&&manifest.sources.length===2&&manifest.sources.every(source=>hashPattern.test(source.original_sha256)&&typeof source.name==='string'&&/^https:\/\//.test(source.url)),'Missing physical source provenance');
  assert(Array.isArray(manifest.parts)&&manifest.parts.length<=32,'Coverage part budget exceeded');
  const paths=new Set();
  for(const kind of ['rows','runs']){
    let offset=0;
    for(const part of manifest.parts.filter(p=>p.kind===kind).sort((a,b)=>a.offset-b.offset)){
      assert(part.offset===offset&&Number.isInteger(part.words)&&part.words>0&&part.words<=1048576&&part.encoding==='byte-shuffle','Invalid coverage part layout');
      assert(new RegExp('^coverage-classification/'+kind+'-\\d+\\.bin\\.gz$').test(part.path)&&!paths.has(part.path),'Unsafe or duplicate coverage path');
      paths.add(part.path);
      assert(hashPattern.test(part.sha256)&&hashPattern.test(part.decoded_sha256)&&Number.isInteger(part.compressed_bytes)&&part.compressed_bytes>0&&part.compressed_bytes<=MAX_PART_BYTES,'Missing coverage byte proof');
      offset+=part.words;
    }
    assert(offset===(kind==='rows'?manifest.size*2:manifest.runWords),'Incomplete coverage parts');
  }
  assert(paths.size===manifest.parts.length,'Unknown coverage part kind');
  return manifest;
}

async function boundedStream(stream,limit){
  const reader=stream.getReader(),chunks=[];let length=0;
  try{
    while(true){
      const {done,value}=await reader.read();if(done)break;
      length+=value.byteLength;assert(length<=limit,'Coverage stream exceeds byte budget');chunks.push(value);
    }
  }catch(error){await reader.cancel().catch(()=>{});throw error;}
  finally{reader.releaseLock();}
  const bytes=new Uint8Array(length);let offset=0;
  for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
  return bytes;
}

async function verify(bytes,expected){
  const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  assert(actual===expected,'Coverage checksum mismatch');
}

export async function loadCoverageClassification(manifest,expected,fetcher=fetch){
  validateCoverageManifest(manifest,expected);
  const grid={version:2,size:manifest.size,coordinateBits:manifest.coordinateBits,rows:new Uint32Array(manifest.size*2),runs:new Uint32Array(manifest.runWords)};
  // Limit concurrent compressed/decoded parts; no dense world bitmap.
  let next=0;
  await Promise.all(Array.from({length:Math.min(2,manifest.parts.length)},async()=>{
    while(next<manifest.parts.length){
      const part=manifest.parts[next++],response=await fetcher('./'+part.path);
      assert(response.ok&&response.body,'Coverage assets could not load');
      const bytes=await boundedStream(response.body,Math.max(part.compressed_bytes,part.words*4));
      const compressed=bytes[0]===31&&bytes[1]===139;
      if(compressed){assert(bytes.length===part.compressed_bytes,'Coverage compressed size mismatch');await verify(bytes,part.sha256);}
      // Hosts may decode Content-Encoding. Exact decoded hashes still apply.
      const raw=compressed?await boundedStream(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')),part.words*4):bytes;
      assert(raw.length===part.words*4,'Coverage decoded size mismatch');
      const words=unshuffleOwnershipBytes(raw,part.words);
      await verify(new Uint8Array(words.buffer,words.byteOffset,words.byteLength),part.decoded_sha256);
      grid[part.kind].set(words,part.offset);
    }
  }));
  let offset=0;
  for(let y=0;y<grid.size;y++){
    assert(grid.rows[y*2]===offset,'Invalid coverage row offset');
    const end=offset+grid.rows[y*2+1];assert(end<=grid.runs.length/2,'Invalid coverage row bounds');
    let previous=0;
    for(;offset<end;offset++){
      const run=ownershipRun(grid,offset);
      assert(run.start>=previous&&run.end>run.start&&run.end<=grid.size&&(run.id===1||run.id===2),'Invalid coverage class or overlapping run');
      previous=run.end;
    }
  }
  assert(offset===grid.runs.length/2,'Unreferenced coverage runs');
  return {grid,manifest};
}

export function coverageExplanation(coverage,point,latlng){
  const kind=pickOwnership(coverage?.grid,point.x,point.y);
  const title=kind===1?'Possible geographic coverage gap':kind===2?'Reference water':'Unverified geographic coverage';
  const explanation=kind===1?'No mapped location. A coarse physical reference shows land here; smaller waterways and boundary differences remain uncertain.':kind===2?'No mapped location. The physical reference shows a major lake or reservoir here.':'No mapped location; water or geographic coverage is not verified.';
  return {kind,title,explanation,coordinates:`${latlng.lat.toFixed(5)}°, ${latlng.lng.toFixed(5)}°`,sources:coverage?.manifest.sources??[]};
}

export function coverageText(info){
  return `${info.title} · ${info.coordinates}. ${info.explanation}${info.sources.length?' Sources: '+info.sources.map(source=>source.name).join('; ')+'. Modern reference, independent of selected historical year.':''}`;
}

// DOM construction keeps source labels and coordinates out of HTML parsing.
export function coverageContent(info){
  const content=document.createElement('div'),text=document.createElement('p');
  text.textContent=`${info.title} · ${info.coordinates}. ${info.explanation}`;
  content.append(text);
  for(const source of info.sources){
    const link=document.createElement('a');link.textContent=source.name;link.href=source.url;link.target='_blank';link.rel='noreferrer';
    const paragraph=document.createElement('p');paragraph.append(link);content.append(paragraph);
  }
  if(info.sources.length){const note=document.createElement('p');note.textContent='Modern physical reference, independent of the selected historical year. No location or political affiliation is inferred.';content.append(note);}
  return content;
}

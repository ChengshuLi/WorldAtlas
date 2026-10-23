import {inflateRawSync} from 'node:zlib';

// Historical baseline identities consumed by the retained forward verifier.
// The completed original storage-copy executor and workflow are retired.
export const migrationWorkflowPath='.github/workflows/neon-storage-migration.yml';
export const migrationRepository='ChengshuLi/WorldAtlas';
class MigrationError extends Error{constructor(code){super(code);this.code=code;}}
const fail=code=>{throw new MigrationError(code);};

/** The authenticated artifact archive is small and hash-pinned. Read one exact
 * central-directory entry without extracting any archive path to disk. */
export function rehearsalReceiptFromZIP(bytes){
 if(!Buffer.isBuffer(bytes)||bytes.length<22||bytes.length>2*1024*1024)fail('invalid-rehearsal-artifact-size');
 let end=-1;for(let i=bytes.length-22;i>=Math.max(0,bytes.length-65557);i--)if(bytes.readUInt32LE(i)===0x06054b50){end=i;break;}
 if(end<0||end+22+bytes.readUInt16LE(end+20)!==bytes.length||bytes.readUInt16LE(end+4)||bytes.readUInt16LE(end+6))fail('unsupported-rehearsal-zip');
 const count=bytes.readUInt16LE(end+10),centralSize=bytes.readUInt32LE(end+12),centralOffset=bytes.readUInt32LE(end+16);
 if(count<1||count>10||count!==bytes.readUInt16LE(end+8)||centralOffset+centralSize!==end)fail('invalid-rehearsal-zip-directory');
 let at=centralOffset,result=null;
 for(let entry=0;entry<count;entry++){
  if(at+46>end||bytes.readUInt32LE(at)!==0x02014b50)fail('invalid-rehearsal-zip-entry');
  const flags=bytes.readUInt16LE(at+8),method=bytes.readUInt16LE(at+10),compressed=bytes.readUInt32LE(at+20),raw=bytes.readUInt32LE(at+24),nameLength=bytes.readUInt16LE(at+28),extra=bytes.readUInt16LE(at+30),comment=bytes.readUInt16LE(at+32),local=bytes.readUInt32LE(at+42);
  const next=at+46+nameLength+extra+comment;if(next>end)fail('invalid-rehearsal-zip-entry-size');
  const name=bytes.subarray(at+46,at+46+nameLength).toString('utf8');
  if(!['receipt.json','credential-envelope.json'].includes(name)||flags&1||![0,8].includes(method)||compressed>2*1024*1024||raw>128*1024)fail('unsafe-rehearsal-zip-entry');
  if(name==='receipt.json'){
   if(result||local+30>centralOffset||bytes.readUInt32LE(local)!==0x04034b50||bytes.readUInt16LE(local+8)!==method)fail('invalid-rehearsal-zip-local-header');
   const localName=bytes.readUInt16LE(local+26),localExtra=bytes.readUInt16LE(local+28),start=local+30+localName+localExtra;
   if(bytes.subarray(local+30,local+30+localName).toString('utf8')!==name||start+compressed>centralOffset)fail('invalid-rehearsal-zip-local-name');
   result=method===0?Buffer.from(bytes.subarray(start,start+compressed)):inflateRawSync(bytes.subarray(start,start+compressed),{maxOutputLength:128*1024});
   if(result.length!==raw)fail('invalid-rehearsal-zip-raw-size');
  }
  at=next;
 }
 if(at!==end||!result)fail('missing-rehearsal-receipt');return result;
}

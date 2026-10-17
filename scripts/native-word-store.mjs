// Private scratch for authenticated shuffled native words. The wire format is
// unchanged; only a fixed window is materialized, regardless of container size.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createGunzip} from 'node:zlib';
import {Readable,Transform} from 'node:stream';
import {pipeline} from 'node:stream/promises';
const need=(value,message)=>{if(!value)throw Error(message);};
export const NATIVE_WORD_WINDOW=16384;

export async function openNativeWordStore(chunks,pin,{directory=process.cwd()}={}) {
  need(Number.isSafeInteger(pin.words)&&pin.words>0&&pin.decoded_bytes===pin.words*4,
    'Incomplete shuffled native word count');
  const root=fs.mkdtempSync(path.join(directory,'worldatlas-native-'));
  const file=path.join(root,'shuffled');let fd,closed=false,windowStart=-1,window,planes=Buffer.allocUnsafe(NATIVE_WORD_WINDOW*4),words=Buffer.allocUnsafe(NATIVE_WORD_WINDOW*4);
  const close=()=>{if(closed)return;closed=true;window=null;planes=null;words=null;windowStart=-1;if(fd!==undefined)fs.closeSync(fd);fs.rmSync(root,{recursive:true});};
  try {
    const encodedHash=createHash('sha256');let encodedBytes=0,decodedBytes=0;
    const encoded=new Transform({transform(chunk,encoding,done){
      encodedBytes+=chunk.length;
      if(encodedBytes>pin.bytes)return done(Error('Native encoded size exceeds pin'));
      encodedHash.update(chunk);done(null,chunk);
    }});
    const decoded=new Transform({transform(chunk,encoding,done){
      decodedBytes+=chunk.length;
      if(decodedBytes>pin.decoded_bytes)return done(Error('Native decoded size exceeds pin'));
      done(null,chunk);
    }});
    await pipeline(Readable.from(chunks),encoded,createGunzip(),decoded,
      fs.createWriteStream(file,{flags:'wx',mode:0o600}));
    need(encodedBytes===pin.bytes&&encodedHash.digest('hex')===pin.sha256,'Whole native encoded body differs');
    need(decodedBytes===pin.decoded_bytes,'Whole native decoded length differs');
    fd=fs.openSync(file,'r');
    function load(start) {
      const count=Math.min(NATIVE_WORD_WINDOW,pin.words-start);
      for(let plane=0;plane<4;plane++){
        let read=0;while(read<count){const n=fs.readSync(fd,planes,plane*count+read,count-read,plane*pin.words+start+read);need(n>0,'Truncated native word spool');read+=n;}
      }
      for(let i=0;i<count;i++)words.writeUInt32LE(planes[i]+planes[count+i]*256+planes[count*2+i]*65536+planes[count*3+i]*16777216,i*4);
      return words.subarray(0,count*4);
    }
    const canonical=createHash('sha256');
    for(let at=0;at<pin.words;at+=NATIVE_WORD_WINDOW)canonical.update(load(at));
    need(canonical.digest('hex')===pin.decoded_sha256,'Whole native canonical words differ');
    return Object.freeze({length:pin.words,close,
      get(index){
        need(!closed&&Number.isSafeInteger(index)&&index>=0&&index<pin.words,'Foreign or closed native word index');
        const start=Math.floor(index/NATIVE_WORD_WINDOW)*NATIVE_WORD_WINDOW;
        if(start!==windowStart){window=load(start);windowStart=start;}
        return window.readUInt32LE((index-start)*4);
      }
    });
  }catch(error){close();throw error;}
}

// Reversible transport codecs; decoded words retain the canonical GPU layout.
export function shuffleOwnershipBytes(words){
 const out=new Uint8Array(words.length*4);
 for(let i=0;i<words.length;i++)for(let b=0;b<4;b++)out[b*words.length+i]=words[i]>>>(b*8)&255;
 return out;
}
export function unshuffleOwnershipBytes(bytes,wordCount){
 if(bytes.length!==wordCount*4)throw Error('Incomplete shuffled ownership asset');
 const out=new Uint32Array(wordCount);
 for(let i=0;i<wordCount;i++)out[i]=bytes[i]+bytes[wordCount+i]*256+bytes[wordCount*2+i]*65536+bytes[wordCount*3+i]*16777216;
 return out;
}
function rowTracker(rows,firstRun){
 let lo=0,hi=rows.length/2;
 while(lo<hi){const mid=Math.floor((lo+hi)/2);if(rows[mid*2]+rows[mid*2+1]<=firstRun)lo=mid+1;else hi=mid;}
 let row=lo,end=rows[row*2]+rows[row*2+1];
 return index=>{let changed=false;while(index>=end&&row<rows.length/2){row++;end=rows[row*2]+rows[row*2+1];changed=true;}if(row>=rows.length/2)throw Error('Ownership transport exceeds row table');return changed;};
}
export function encodeOwnershipVarints(words,{rows,offset=0,coordinateBits}){
 if(offset%2||words.length%2)throw Error('Incomplete compact ownership words');
 const bytes=new Uint8Array(words.length*8),mask=2**coordinateBits-1,base=2**(32-coordinateBits),nextRow=rowTracker(rows,offset/2);let at=0,previousEnd=0,previousId=0;
 const put=value=>{while(value>=128){bytes[at++]=value%128+128;value=Math.floor(value/128);}bytes[at++]=value;};
 for(let k=0;k<words.length;k+=2){
  if(nextRow((offset+k)/2)){previousEnd=0;previousId=0;}
  const a=words[k],b=words[k+1],start=a&mask,end=(b&mask)+1,id=(a>>>coordinateBits)+(b>>>coordinateBits)*base,delta=id-previousId;
  put(start-previousEnd);put(end-start);put(delta<0?-delta*2-1:delta*2);previousEnd=end;previousId=id;
 }
 return bytes.slice(0,at);
}
export function decodeOwnershipVarints(bytes,{rows,offset=0,words,coordinateBits,size}){
 if(offset%2||words%2)throw Error('Incomplete compact ownership words');
 const out=new Uint32Array(words),factor=2**coordinateBits,base=2**(32-coordinateBits),max=Math.min(2**32-1,base*base-1),nextRow=rowTracker(rows,offset/2);let at=0,previousEnd=0,previousId=0;
 const get=()=>{let value=0,multiplier=1;for(let k=0;k<6;k++){if(at>=bytes.length)throw Error('Incomplete ownership varints');const byte=bytes[at++];value+=(byte&127)*multiplier;if(byte<128)return value;multiplier*=128;}throw Error('Ownership varint exceeds capacity');};
 for(let k=0;k<words;k+=2){
  if(nextRow((offset+k)/2)){previousEnd=0;previousId=0;}
  const start=previousEnd+get(),end=start+get(),zigzag=get(),id=previousId+(zigzag%2?-(zigzag+1)/2:zigzag/2);
  if(start<previousEnd||end<=start||end>size||id<1||id>max)throw Error('Invalid ownership varint run');
  out[k]=id%base*factor+start;out[k+1]=Math.floor(id/base)*factor+end-1;previousEnd=end;previousId=id;
 }
 if(at!==bytes.length)throw Error('Unreferenced ownership varint bytes');
 return out;
}

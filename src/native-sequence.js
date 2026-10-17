// Browser-safe, explicitly branded repeatable sequence of native rows/intervals.
// A sequence is storage, never scientific authority; consumers validate domains.
const sources=new WeakMap();
const require=(ok,message)=>{if(!ok)throw Error(message);};
export function nativeSequence(length,entries,{rowAt}={}) {
  require(Number.isSafeInteger(length)&&length>=0&&typeof entries==='function','Invalid native sequence');
  const sequence={length,
    *[Symbol.iterator](){
      let count=0;
      for(const item of entries()){
        require(count++<length,'Native sequence exceeds declared count');yield item;
      }
      require(count===length,'Native sequence omitted declared entries');
    },
    at(index){
      require(Number.isSafeInteger(index),'Invalid native sequence index');
      if(index<0)index+=length;
      if(index<0||index>=length)return undefined;
      let i=0;for(const item of sequence)if(i++===index)return item;
    }};
  Object.defineProperty(sequence,'at',{enumerable:false});Object.freeze(sequence);
  sources.set(sequence,{rowAt});return sequence;
}
export const isNativeSequence=value=>Array.isArray(value)||sources.has(value);
export function nativeRowAt(rows,y) {
  require(isNativeSequence(rows),'Missing native row sequence');
  const direct=sources.get(rows)?.rowAt;
  if(direct){const row=direct(y);require(row===undefined||row.y===y,'Native sequence lookup changed row identity');return row;}
  if(Array.isArray(rows)){
    let lo=0,hi=rows.length;while(lo<hi){const mid=Math.floor((lo+hi)/2);if(rows[mid].y<y)lo=mid+1;else hi=mid;}
    return rows[lo]?.y===y?rows[lo]:undefined;
  }
  for(const row of rows){if(row.y===y)return row;if(row.y>y)break;}
}

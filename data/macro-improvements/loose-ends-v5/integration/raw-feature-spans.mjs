// Preserve untouched feature bytes, including JSON number spellings (30.0 vs 30).
// Geometry fingerprints in other runtimes can retain that distinction.
export function replaceFeatureSpans(raw,replacements){
 let cursor=0;
 const space=()=>{while(/\s/.test(raw[cursor]??'')&&cursor<raw.length)cursor++;};
 const stringEnd=start=>{
  if(raw[start]!== '"')throw Error('Expected JSON string');
  let escaped=false;
  for(let i=start+1;i<raw.length;i++){
   if(escaped){escaped=false;continue;}
   if(raw[i]==='\\'){escaped=true;continue;}
   if(raw[i]==='"')return i+1;
  }
  throw Error('Unterminated JSON string');
 };
 const valueEnd=start=>{
  if(raw[start]==='"')return stringEnd(start);
  if(raw[start]!=='{'&&raw[start]!=='['){let i=start;while(i<raw.length&&!/[\s,}\]]/.test(raw[i]))i++;return i;}
  const stack=[];
  for(let i=start;i<raw.length;i++){
   const char=raw[i];if(char==='"'){i=stringEnd(i)-1;continue;}
   if(char==='{'||char==='[')stack.push(char);
   else if(char==='}'||char===']'){
    if(stack.pop()!==(char==='}'?'{':'['))throw Error('Mismatched JSON nesting');
    if(!stack.length)return i+1;
   }
  }
  throw Error('Unterminated JSON value');
 };
 space();if(raw[cursor++]!=='{')throw Error('Expected FeatureCollection object');
 let arrayStart=-1;
 while(cursor<raw.length){
  space();if(raw[cursor]==='}')break;
  const end=stringEnd(cursor),key=JSON.parse(raw.slice(cursor,end));cursor=end;space();
  if(raw[cursor++]!==':')throw Error('Expected member separator');space();
  const start=cursor;cursor=valueEnd(cursor);
  if(key==='features'){if(arrayStart!==-1||raw[start]!=='[')throw Error('Invalid features array');arrayStart=start;}
  space();if(raw[cursor]===','){cursor++;continue;}if(raw[cursor]!=='}')throw Error('Invalid object delimiter');break;
 }
 if(arrayStart===-1)throw Error('Missing top-level features');
 cursor=arrayStart+1;let preservedEnd=0;const chunks=[],seen=new Set(),changed=new Set();
 while(cursor<raw.length){
  space();if(raw[cursor]===']')break;
  const start=cursor,end=valueEnd(start),feature=JSON.parse(raw.slice(start,end)),id=feature.id;
  if(!id||id!==feature.properties?.id||seen.has(id))throw Error('Invalid or duplicate feature identity');seen.add(id);
  if(replacements.has(id)){
   const next=replacements.get(id);if(next.id!==id||next.properties?.id!==id)throw Error('Replacement identity changed');
   chunks.push(raw.slice(preservedEnd,start),JSON.stringify(next));preservedEnd=end;changed.add(id);
  }
  cursor=end;space();if(raw[cursor]===','){cursor++;continue;}if(raw[cursor]!==']')throw Error('Invalid array delimiter');break;
 }
 chunks.push(raw.slice(preservedEnd));return {raw:chunks.join(''),changed_ids:[...changed]};
}

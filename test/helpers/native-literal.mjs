// Test-only materialization for comparing private cursor views from isolated
// copied modules with their independent literal JSON operands.
export function nativeLiteral(value) {
  if(value&&typeof value==='object'){
    if(Array.isArray(value)||typeof value[Symbol.iterator]==='function')return Array.from(value,nativeLiteral);
    return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,nativeLiteral(item)]));
  }
  return value;
}

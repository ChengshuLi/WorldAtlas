// Test-only materialization for comparing private cursor views from isolated
// copied modules with their independent literal JSON operands.
export function nativeLiteral(value) {
  if(value&&typeof value==='object'){
    if(Array.isArray(value)||typeof value[Symbol.iterator]==='function')return Array.from(value,nativeLiteral);
    return Object.fromEntries(Object.entries(value).map(([key,item])=>[key,nativeLiteral(item)]));
  }
  return value;
}

// A live disk-backed state requires explicit release, including in a test that
// fails before reaching its normal release assertion. Keep production authority
// checks intact and tolerate only a session already released by the test.
export function checkpointTestAPI(t,api) {
  const track=fn=>async (...args)=>{
    const result=await fn(...args);
    if(result.available)t.after(()=>{
      try{api.releaseCheckpoint(result.state);}catch(error){
        if(!/Checkpoint already released or foreign/.test(error.message))throw error;
      }
    });
    return result;
  };
  return {...api,qualifyCheckpoint:track(api.qualifyCheckpoint),qualifyAcceptedCheckpoint:track(api.qualifyAcceptedCheckpoint)};
}

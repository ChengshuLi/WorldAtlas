// Immutable numerical preimage from 07d177c76bc5172fd5cce78621ed4cd8d992c4c3.
const demand=(v,m)=>{if(!v)throw Error(m);};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);

// Numerical consumers of complete row projections. These helpers do not issue
// selection/checkpoint authority: the trusted shared reader must authenticate
// each vintage, scope, owner/parent binding and complete native input custody.
function effectiveNativeRows(rows,size,owners) {
  demand(Number.isSafeInteger(size)&&size>0&&Number.isSafeInteger(size*size),'Invalid effective native domain');
  demand(Array.isArray(rows)&&Array.isArray(owners)&&owners.length>0,'Missing complete effective native projections');
  const indexed=new Map();let previous=-1;
  for(const row of rows){
    demand(row&&Number.isSafeInteger(row.y)&&row.y>previous&&row.y<size&&Array.isArray(row.runs),'Duplicate/foreign/unordered effective native row');
    previous=row.y;let end=0;
    for(const run of row.runs){
      demand(Array.isArray(run)&&run.length===3&&run.every(Number.isSafeInteger)&&run[0]>=end&&run[1]>run[0]&&run[1]<=size&&run[2]>0
        &&typeof owners[run[2]-1]?.id==='string'&&owners[run[2]-1].id.length>0,'Invalid complete effective native interval/owner');
      end=run[1];
    }
    indexed.set(row.y,row);
  }
  return indexed;
}

// Shared projectNativeRows returns ORIGINAL base intervals. Its privately
// qualified state's cumulative patch must be applied once, never cached twice.
export function applyNativeAdditiveRows(baseRows,patch,{size,owners}) {
  const base=effectiveNativeRows(baseRows,size,owners);
  const additions=effectiveNativeRows(patch==null?[]:patch.rows,size,owners);
  const rows=[];
  for(const [y,row]of base){
    const runs=[...row.runs.map(run=>[...run]),...(additions.get(y)?.runs??[]).map(run=>[...run])].sort((a,b)=>a[0]-b[0]);
    let end=0;
    for(const run of runs){demand(run[0]>=end,'Selected additive delta overlaps preexisting assigned native cells');end=run[1];}
    rows.push({y,runs});
  }
  return rows;
}

export function deriveEffectiveNativeRowDelta(beforeRows,afterRows,{size,ownersBefore,ownersAfter}) {
  const before=effectiveNativeRows(beforeRows,size,ownersBefore),after=effectiveNativeRows(afterRows,size,ownersAfter);
  const rows=[...new Set([...before.keys(),...after.keys()])].sort((a,b)=>a-b);
  return rows.filter(y=>{
    const old=before.get(y),next=after.get(y);
    if(!old||!next||!same(old.runs,next.runs))return true;
    // Stable indices are independently checked by the acquisition boundary;
    // do not let this pure helper hide an ID change behind an equal run count.
    return old.runs.some(run=>ownersBefore[run[2]-1].id!==ownersAfter[run[2]-1].id);
  });
}


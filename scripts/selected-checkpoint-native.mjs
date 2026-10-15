// Joint-only native checkpoint consumer. Keep the cold/package import closure literal.
import {compareIntervals,newVisibleRepairCandidates,repairVisibilityWitnesses} from './check-effective-geographic-regression.mjs';
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

export function compareEffectiveNativeRows(beforeRows,afterRows,{size,ownersBefore,ownersAfter,rows}) {
  const before=effectiveNativeRows(beforeRows,size,ownersBefore),after=effectiveNativeRows(afterRows,size,ownersAfter);
  demand(Array.isArray(rows)&&rows.every((y,i)=>Number.isSafeInteger(y)&&y>=0&&y<size&&(!i||y>rows[i-1])),'Duplicate/foreign/unordered requested native row');
  demand(same([...before.keys()],rows)&&same([...after.keys()],rows),'Incomplete complete native projection scope');
  const intervals=[];let lostCells=0;
  for(const y of rows)for(const loss of compareIntervals(before.get(y).runs,after.get(y).runs,{row:y,ownersBefore,ownersAfter})){
    lostCells+=loss.end-loss.start;demand(Number.isSafeInteger(lostCells),'Native loss count exceeds exact integer domain');intervals.push(loss);
  }
  return {checked_rows:rows.length,lost_or_reassigned_cells:lostCells,intervals};
}

// The joint launcher qualifies both states in one invocation and owns release.
// Authentication stays in the shared projector, including the zero-row path.
export async function compareSelectedCheckpointNative({transition}) {
  const {authenticateTransition,projectNativeRows,projectVisibilityLatitudes}=await import('../coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs');
  const {baseline,candidate,changedNativeRows}=authenticateTransition({transition});
  const visibilityCandidates=newVisibleRepairCandidates(baseline.additions,candidate.additions);
  const size=baseline.manifest.size,oldEntries=baseline.certificate.entries,newEntries=candidate.certificate.entries;
  demand(size===candidate.manifest.size&&oldEntries.length===newEntries.length,'Checkpoint native domain or complete owner roster differs');
  for(let i=0;i<oldEntries.length;i++)for(let k=0;k<4;k++)
    demand(oldEntries[i][k]===newEntries[i][k],'Checkpoint original stable owner/index/parent rebound');
  // The private transition already derives the complete symmetric patch delta
  // from actual authenticated bodies. Caller-created wrappers cannot select it.
  const expected=changedNativeRows;

  // qualifyTransition proves identical base selection and all native routes;
  // its candidate cache already contains newly qualified original base rows.
  // Project once, then apply the two cumulative patches to that SAME base.
  demand(same(baseline.baseSelection,candidate.baseSelection)&&baseline.selection.sha256===candidate.selection.sha256,
    'Checkpoint original native base/manifest binding differs');
  const projection=projectNativeRows({state:candidate,rows:expected});
  let result={checked_rows:0,lost_or_reassigned_cells:0,intervals:[]},visibilityWitnesses=[];
  if(expected.length){

    const owners=oldEntries.map(row=>({id:row[0],index:row[1],province_id:row[2],province_index:row[3]}));
    const oldRows=applyNativeAdditiveRows(projection.rows,baseline.patch,{size,owners});
    const newRows=applyNativeAdditiveRows(projection.rows,candidate.patch,{size,owners});
    result=compareEffectiveNativeRows(oldRows,newRows,{size,ownersBefore:owners,ownersAfter:owners,rows:expected});
    if(visibilityCandidates.length){

      const latitudes=projectVisibilityLatitudes({state:candidate});
      visibilityWitnesses=repairVisibilityWitnesses({candidates:visibilityCandidates,size,latitudes,beforeRows:oldRows,afterRows:newRows});
    }
  }
  demand(visibilityWitnesses.length===visibilityCandidates.length&&visibilityWitnesses.every(Boolean),'New gap repair has no actual changed map-cell witness');
  const report={version:1,repair_visibility:{new_components:visibilityCandidates.length,witnesses:visibilityWitnesses},method:'selected-native-owner-conservation-v1',
    status:result.intervals.length?'native-regressions-found':'no-new-native-loss',
    baseline_selection:baseline.selection,candidate_selection:candidate.selection,
    affected_rows:result.checked_rows,lost_or_reassigned_cells:result.lost_or_reassigned_cells,intervals:result.intervals,
    native_row_scope:{proof:'shared-qualified-complete-base-and-cumulative-patch',changed_rows:expected,
      shared_base_reused_rows:projection.reused_rows,shared_base_acquired_rows:projection.acquired_rows},
    checkpoint_custody:{baseline_checkpoint:baseline.accepted_execution,shared_base:projection.custody},
    candidate_code_executed:false,
    limits:['Shared qualification and transition authenticate complete selection, registry, ledger, source and native custody before this consumer.',
      'Native interval conservation is not sub-cell polygon coverage or source authority approval; continuous coverage, when in scope, is reported separately.']};
  return report;
}


import {colorLab,labDistance,visionModels} from '../src/color-perception.js';

const hash = value => { let n=2166136261; for (const c of value) n=Math.imul(n^c.charCodeAt(0),16777619); return n>>>0; };
const hex = rgb => '#' + rgb.map(v => v.toString(16).padStart(2,'0')).join('');
const levels = [48,76,104,132,160,188,216,244];
const candidates = levels.flatMap(r => levels.flatMap(g => levels.map(b => hex([r,g,b]))))
  .filter(color => { const [l,a,b]=colorLab(color); return l>=0.43 && l<=0.88 && Math.hypot(a,b)>=0.04; });
const labs = candidates.map(color => visionModels.map(model => colorLab(color,model)));
const unknown = visionModels.map(model => colorLab('#53615c',model));
export const contrastBudget = Object.freeze({normal:8,protanopia:4,deuteranopia:4,tritanopia:4});
const normalized = (a,b) => Math.min(...visionModels.map((model,i) => labDistance(a[i],b[i])/contrastBudget[model]));

// Fixed input graph, deterministic ID order/ties and bounded optimization. Nothing
// depends on the active year, viewport, request order or a browser session cache.
export function assignCategoryColors(keys, edges, {passes=4}={}) {
  if (!Array.isArray(keys) || keys.some(k => typeof k !== 'string') || new Set(keys).size!==keys.length || !Number.isInteger(passes) || passes<0 || passes>12) throw Error('Invalid category palette input');
  const identities=[...keys].sort(), byKey=new Map(identities.map((k,i)=>[k,i])), neighbors=identities.map(()=>new Set());
  for (const pair of edges) {
    if (!Array.isArray(pair) || pair.length!==2 || !byKey.has(pair[0]) || !byKey.has(pair[1])) throw Error('Unknown palette edge identity');
    const a=byKey.get(pair[0]),b=byKey.get(pair[1]); if (a===b) continue;
    neighbors[a].add(b); neighbors[b].add(a);
  }
  const order=identities.map((_,i)=>i).sort((a,b)=>neighbors[b].size-neighbors[a].size || (identities[a]<identities[b]?-1:1));
  const choices=new Int32Array(identities.length).fill(-1);
  const score = (node,candidate) => {
    let minimum=Math.min(2,normalized(labs[candidate],unknown));
    for (const neighbor of neighbors[node]) if (choices[neighbor]>=0) minimum=Math.min(minimum,normalized(labs[candidate],labs[choices[neighbor]]));
    return minimum;
  };
  const choose = node => {
    let identity=identities[node];
    if (identity.startsWith('[')) { try { const parsed=JSON.parse(identity); if (Array.isArray(parsed) && parsed.length===2 && typeof parsed[0]==='string') identity=parsed[0]; } catch {} }
    const start=hash(identity)%candidates.length;
    let best=choices[node], value=best<0?-1:score(node,best);
    for (let step=0;step<candidates.length;step++) {
      const c=(start+step)%candidates.length,s=score(node,c);
      if (s>value+1e-10) { best=c; value=s; }
    }
    choices[node]=best;
  };
  for (const node of order) choose(node);
  for (let pass=0;pass<passes;pass++) for (const node of order) choose(node);
  return Object.fromEntries(identities.map((key,i)=>[key,candidates[choices[i]]]));
}

export function auditCategoryColors(colors,edges) {
  const summary={edges:0,models:Object.fromEntries(visionModels.map(model=>[model,{budget:contrastBudget[model],minimum:null,below_budget:0}])),failures:[]};
  const cache=new Map(); const points=key=>{if(!Object.hasOwn(colors,key))throw Error('Missing palette identity');if(!cache.has(key))cache.set(key,visionModels.map(m=>colorLab(colors[key],m)));return cache.get(key);};
  for (const [a,b] of edges) {
    if (a===b) continue;
    summary.edges++; const x=points(a),y=points(b),values={}; let failed=false;
    visionModels.forEach((model,i)=>{
      const value=labDistance(x[i],y[i]),row=summary.models[model];values[model]=value;
      row.minimum=row.minimum===null?value:Math.min(row.minimum,value);
      if(value+1e-9<row.budget){row.below_budget++;failed=true;}
    });
    if(failed)summary.failures.push({a,b,differences:values});
  }
  return summary;
}

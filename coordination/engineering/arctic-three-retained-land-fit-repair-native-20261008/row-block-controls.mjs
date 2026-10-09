// Cache-only prototype: genuine scoped calls of existing numerical primitives.
// No full-world computation, product adoption, or scientific qualification.
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const root = process.argv[2];
const {nativePolygonIntervals} = await import(pathToFileURL(root+'/src/native-grid.js'));
const {coverageRow} = await import(pathToFileURL(root+'/scripts/audit-grid-intervals.mjs'));
const {compileNativeOwnership} = await import(pathToFileURL(root+'/scripts/native-ownership/compile-native-ownership.mjs'));

const {compileRowBlock} = await import(pathToFileURL(root+'/coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008/compile-row-block.mjs'));
function block(index,{size,latitudes,first,end}) {
 const r=compileRowBlock(index,{size,latitudes,rowStart:first,rowEnd:end});
 return {rows:r.rows,words:r.runs,ownedCells:r.owned_cells,multipleOwnerCells:r.multiple_owner_cells,ties:r.boundary_tie_records,ownerCounts:r.per_owner_cells};
}

const ring=(x1,y1,x2,y2)=>new Float64Array([x1,y1,x2,y1,x2,y2,x1,y2,x1,y1]);
const fixtures=[[],[{index:1,polygons:[[ring(-80,-70,80,70)]]}],
  [{index:1,polygons:[[ring(-100,-70,40,70)]]},{index:2,polygons:[[ring(-20,-50,120,50)]]}],
  [{index:1,polygons:[[ring(-160,-70,160,70),ring(-40,-30,40,30)]]}]];
const size=16,latitudes=Float64Array.from({length:size},(_,i)=>80-i*10);
let passes=0;
for(const index of fixtures){
  const fullParts=[];
  const full=await compileNativeOwnership(index,{size,latitudes,rowBlock:4,partWords:8,
    writePart:async(p,words)=>{fullParts.push({...p,body:words});return p;}});
  const actualRows=new Uint32Array(size*2),actualWords=[];
  let prefix=0,owned=0,multiple=0,ties=0;
  const counts=new Map(index.map(row=>[row.index,0]));
  for(let first=0;first<size;first+=4){
    const piece=block(index,{size,latitudes,first,end:first+4});
    for(let i=0;i<piece.rows.length;i+=2){actualRows[first*2+i]=piece.rows[i]+prefix;actualRows[first*2+i+1]=piece.rows[i+1];}
    actualWords.push(...piece.words);prefix+=piece.words.length/2;
    owned+=piece.ownedCells;multiple+=piece.multipleOwnerCells;ties+=piece.ties;
    for(const [id,value] of piece.ownerCounts)counts.set(id,counts.get(id)+value);
  }
  const expectedRuns=fullParts.filter(p=>p.kind==='runs').flatMap(p=>[...p.body]);
  const expectedRows=fullParts.filter(p=>p.kind==='rows').flatMap(p=>[...p.body]);
  assert.deepEqual(actualWords,expectedRuns);assert.deepEqual([...actualRows],expectedRows);
  assert.equal(owned,full.owned_cells);assert.equal(multiple,full.multiple_owner_cells);
  assert.equal(ties,full.boundary_tie_records);assert.deepEqual([...counts],full.per_owner_cells);
  passes++;
}
assert.throws(()=>block([{index:2,polygons:[]},{index:1,polygons:[]}],{size,latitudes,first:0,end:4}));
assert.throws(()=>block([{index:1,polygons:[[new Float64Array([0,0,1,0,1,1,2,2])]]}],{size,latitudes,first:0,end:4}));
assert.throws(()=>block([],{size,latitudes,first:-1,end:4}));
console.log(JSON.stringify({scope:'actual owned row-block adapter vs immutable stock compiler on tiny complete fixtures',positive:passes,negative:3,
  full_world_executed:false,operand_generation:false,qualified_science:false,root,node:process.version}));

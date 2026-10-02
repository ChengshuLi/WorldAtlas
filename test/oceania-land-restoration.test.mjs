import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {representation,prepareOceaniaLand} from '../scripts/prepare-oceania-land-restoration.mjs';
const polygon=(id,x,y,size)=>({type:'Feature',id,properties:{id,name:id},geometry:{type:'Polygon',coordinates:[[[x,y],[x+size,y],[x+size,y+size],[x,y+size],[x,y]]]}});
const archiveChecker=new URL('../scripts/validate-oceania-land-restoration.py',import.meta.url);
function archiveFixture(t,old){const root=fs.mkdtempSync(path.join(os.tmpdir(),'oceania-archive-'));t.after(()=>fs.rmSync(root,{recursive:true,force:true}));const bytes=gzipSync(JSON.stringify({locations:[{feature:old}]}));fs.writeFileSync(path.join(root,'archive.gz'),bytes);return {root,archives:[{path:'archive.gz',sha256:createHash('sha256').update(bytes).digest('hex')}]};}
function checkArchive(payload){return JSON.parse(execFileSync('python3',[archiveChecker.pathname],{input:JSON.stringify(payload),stdio:['pipe','pipe','pipe']}));}
test('canonical screen reports actual source-land cells for a compact territorial polygon',()=>{const result=representation(polygon('island',150,-10,.02));assert.ok(result.cell_center_count>0);assert.equal(result.canonical_size,262144);assert.equal(result.canonical_grid_zoom,10);assert.ok(result.example_cells.length>0);});
test('a genuine polygon smaller than a cell remains unrepresented without assigning water',()=>{const result=representation(polygon('tiny',150,-10,.000001));assert.equal(result.cell_center_count,0);assert.deepEqual(result.example_cells,[]);});
test('archived original dry land blocks a purported new identity on that land',t=>{const fixture=archiveFixture(t,polygon('original',150,-10,.02));assert.throws(()=>checkArchive({...fixture,candidates:[polygon('new-id',150,-10,.02)]}),error=>String(error.stderr).includes('Existing archived land cannot be created again'));});
test('an exact-name homonym on different land does not transfer or reuse archived identity',t=>{const fixture=archiveFixture(t,polygon('McKean',-78,41,.02));const result=checkArchive({...fixture,candidates:[polygon('McKean island',-174,-3,.02)]});assert.equal(result.verified,true);assert.equal(result.archived_predecessors_checked,1);assert.equal(result.history_transfer,false);});
test('changed archive bytes fail before considering identity absence',t=>{const fixture=archiveFixture(t,polygon('old',1,1,.02));fs.appendFileSync(path.join(fixture.root,'archive.gz'),'changed');assert.throws(()=>checkArchive({...fixture,candidates:[polygon('new',10,10,.02)]}),error=>String(error.stderr).includes('Archived geography bytes changed'));});
test('candidate preparation refuses an existing output instead of overwriting evidence',t=>{const output=fs.mkdtempSync(path.join(os.tmpdir(),'oceania-existing-'));t.after(()=>fs.rmSync(output,{recursive:true,force:true}));fs.writeFileSync(path.join(output,'prior-evidence'),'retained');assert.throws(()=>prepareOceaniaLand({root:path.join(output,'source'),output}),/fresh and separate/);assert.equal(fs.readFileSync(path.join(output,'prior-evidence'),'utf8'),'retained');});

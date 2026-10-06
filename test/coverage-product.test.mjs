import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {loadCoverageClassification} from '../src/coverage-classification.js';
import {projectCell} from '../src/pixel-grid.js';
import {pickOwnership} from '../src/pixel-ownership.js';
import {readGeographicReleaseManifest} from '../scripts/read-geographic-release-manifest.mjs';
test('prepared physical reference is pinned and preserves reported gaps, lake, ocean and blocked uncertainty',async()=>{
 const manifest=JSON.parse(await fs.readFile('data/coverage-classification/manifest.json'));
 const canonical=await fs.readFile('data/canonical-grid/manifest.json'),grid=JSON.parse(canonical);
 // This is the retained original physical product. New releases have a separate
 // reviewed binding; do not reinterpret the old grid as the latest geography.
 const release=readGeographicReleaseManifest().releases.find(row=>row.id===manifest.release_id);
 assert.ok(release,'Original physical release remains in the complete registry');
 assert.equal(release.footprints_sha256,grid.footprints_sha256);
 assert.equal(release.hierarchy_sha256,grid.hierarchy_sha256);
 const coverage=await loadCoverageClassification(manifest,{...grid,release_id:release.id,canonical_grid_sha256:createHash('sha256').update(canonical).digest('hex')},async path=>new Response(await fs.readFile('data/'+path.replace(/^\.\//,''))));
 for(const [name,lon,lat,expected] of [['Iran/Pakistan',63.207727681,26.8032,1],['Portugal/Spain',-6.936928247,39.864122024,1],['Lake Superior',-87.9780717857,47.727,2],['Atlantic',-30,0,0],['Blocked reference',102,55,0],['Antarctica',0,-70,0]]){
  const [x,y]=projectCell(lon,lat);assert.equal(pickOwnership(coverage.grid,x,y),expected,name);
 }
 assert.ok(manifest.parts.reduce((n,part)=>n+part.compressed_bytes,0)<12*1024*1024);
});

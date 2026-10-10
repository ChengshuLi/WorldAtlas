import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {ImmutableReader,SelectedGeometrySources,loadSelection} from '../../../scripts/check-effective-geographic-regression.mjs';
import {currentRebindSourceView} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
const head=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
// Actual immutable selected operands; these controls test reuse, not operating RSS.
const reader=new ImmutableReader(process.cwd(),head,{runtimeBytes:0,outputBytes:0});
const snapshot=loadSelection(reader),view=snapshot.geometrySources;
assert.ok(snapshot.selection.selected_geography&&view instanceof SelectedGeometrySources);
assert.ok(Object.isFrozen(snapshot)&&Object.isFrozen(view));
const used=reader.used,metadata=reader.metadataBytes,read=reader.read;
let reopened=0;reader.read=function(){reopened++;throw Error('Unexpected second source-body read');};
try{
 assert.equal(currentRebindSourceView(snapshot),view);
 assert.equal(currentRebindSourceView(snapshot),view);
 assert.equal(reader.used,used);assert.equal(reader.metadataBytes,metadata);
 assert.throws(()=>currentRebindSourceView({...snapshot}),/privately authenticated/);
 assert.throws(()=>{snapshot.geometrySources=Object.create(SelectedGeometrySources.prototype);},TypeError);
 assert.throws(()=>{snapshot.reader={};},TypeError);
 assert.throws(()=>{snapshot.selection.release_id='foreign';},TypeError);
 assert.throws(()=>{snapshot.manifest.size++;},TypeError);
 const savedVersion=reader.version;reader.version=head==='0'.repeat(40)?'1'.repeat(40):'0'.repeat(40);
 try{assert.throws(()=>currentRebindSourceView(snapshot));}finally{reader.version=savedVersion;}
 const override=view.bank.overrides[0];assert.ok(override);
 view.replacements.delete(override.logical_path);
 try{assert.throws(()=>currentRebindSourceView(snapshot),/replacement roster drift/);}finally{view.replacements.set(override.logical_path,override);}
 view.replacements.set(override.logical_path,{...override});
 try{assert.throws(()=>currentRebindSourceView(snapshot),/replacement roster drift/);}finally{view.replacements.set(override.logical_path,override);}
 assert.equal(currentRebindSourceView(snapshot),view);assert.equal(reopened,0);
 console.log('PASS: actual frozen selected source view reused; private clone/forged replacement/reader/selection/manifest/Map drift refused; zero reopened bodies; complete metadata charge unchanged. Not RSS or scientific qualification.');
}finally{reader.read=read;}

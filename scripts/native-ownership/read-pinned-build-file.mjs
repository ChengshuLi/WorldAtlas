// Read immutable byte pins from Git during preparation, or from an explicitly
// declared ordinary snapshot inside the package source image. Never expose Git
// or the caller's repository through the physical package-input boundary.
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {sha256,safeEvidencePath,repositoryReader} from '../evidence-quality.mjs';
export function inPackageImage(root=process.cwd(),marker=process.env.WORLDATLAS_PACKAGE_STAGE){
 if(!marker)return false;
 if(fs.realpathSync(root)!==fs.realpathSync(marker))throw Error('Native package image differs from declared stage');
 return true;
}
export function readPinnedBuildFile({root=process.cwd(),commit,path:original,sha256:expected,bytes,snapshotPath=original}){
 safeEvidencePath(original);safeEvidencePath(snapshotPath);
 if(!/^[a-f0-9]{40}$/.test(commit??'')||!/^[a-f0-9]{64}$/.test(expected??''))throw Error('Immutable build file needs exact commit and whole-file pin');
 let raw;
 if(inPackageImage(root))raw=repositoryReader(root)(snapshotPath,'candidate');
 else{
  const mode=execFileSync('git',['-C',root,'ls-tree',commit,'--',original],{encoding:'utf8'});
  if(!mode.startsWith('100644 ')&&!mode.startsWith('100755 '))throw Error('Pinned original must be ordinary');
  const exactBytes=Number(execFileSync('git',['-C',root,'cat-file','-s',commit+':'+original],{encoding:'utf8'}));
  if(!Number.isSafeInteger(exactBytes)||exactBytes<0)throw Error('Invalid pinned original byte length');
  raw=execFileSync('git',['-C',root,'show',commit+':'+original],{maxBuffer:exactBytes+1});
 }
 if((bytes!==undefined&&raw.length!==bytes)||sha256(raw)!==expected)
  throw Error('Pinned build snapshot bytes differ');
 return raw;
}

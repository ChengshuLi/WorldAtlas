import {execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [repo, commit, manifestPath] = process.argv.slice(2);
if (!repo || !/^[a-f0-9]{40}$/.test(commit ?? '') || !manifestPath) throw Error('Require repository, exact candidate commit and manifest path');
const {repositoryReader, validateEvidence} = await import(pathToFileURL(path.join(repo,'scripts/evidence-quality.mjs')));
const base = repositoryReader(repo);
const manifestPin = base.descriptor(manifestPath, commit);
const manifest = JSON.parse(base(manifestPath, commit, manifestPin));
const readFile = (name, vintage, descriptor) => base(name, vintage === 'candidate' ? commit : vintage, descriptor);
readFile.descriptor = (name, vintage) => base.descriptor(name, vintage === 'candidate' ? commit : vintage);
readFile.assertAncestor = historical => {
  execFileSync('git',['-C',repo,'merge-base','--is-ancestor',historical,commit],{stdio:'pipe'});
};
console.log(JSON.stringify(validateEvidence(manifest,{readFile}),null,2));

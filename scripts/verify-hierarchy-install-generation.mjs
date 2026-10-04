// Byte reproducibility and preservation check for the complete offline generation.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
 if(!['--one','--two','--data','--receipt'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --one STAGE --two STAGE --data BASELINE-DATA --receipt NEW-FILE');
 options[args[i]]=path.resolve(args[i+1]);
}
if(Object.keys(options).length!==4||fs.existsSync(options['--receipt']))throw Error('Four arguments and new receipt required');
const one=JSON.parse(fs.readFileSync(path.join(options['--one'],'report.json'))),two=JSON.parse(fs.readFileSync(path.join(options['--two'],'report.json')));
if(!isDeepStrictEqual(one,two))throw Error('Complete generation reports differ');
function bytes(base,name){
 const file=path.resolve(base,name);
 if(!file.startsWith(base+path.sep)||fs.realpathSync(file)!==file||!fs.lstatSync(file).isFile())throw Error('Unsafe generation asset');
 return fs.readFileSync(file);
}
for(const [name,pin] of Object.entries(one.writes)){
 const a=bytes(path.join(options['--one'],'after'),name),b=bytes(path.join(options['--two'],'after'),name);
 if(hash(a)!==pin||!a.equals(b))throw Error('Generation bytes differ: '+name);
}
for(const [name,pin] of Object.entries(one.preserved))if(hash(bytes(options['--data'],name))!==pin)throw Error('Original payload changed: '+name);
for(const file of one.immutable_grid_parts)if(hash(bytes(options['--data'],file.path))!==file.sha256)throw Error('Ownership buffer changed');
const result={version:1,verified:true,method_id:'hierarchy-install-generator',kind:'reproducibility',outcome:'passed',run_one_sha256:one.validation_sha256,run_two_sha256:two.validation_sha256,written_files:Object.keys(one.writes).length,preserved_files:Object.keys(one.preserved).length,ownership_buffers:one.immutable_grid_parts.length,counts:one.counts,published:false,historical_claims_transferred:false};
fs.writeFileSync(options['--receipt'],encodeEvidenceJSON(result),{flag:'wx'});
console.log(JSON.stringify(result));

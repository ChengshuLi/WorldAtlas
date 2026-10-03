// JavaScript adapter to the versioned Python preparation byte contract.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const scripts=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');

export function encodeEvidenceJSON(value,{gzip=false}={}){
 return execFileSync(process.env.ATLAS_PYTHON??'python3',['-c',
  'import json,sys; sys.path.insert(0,sys.argv[1]); from evidence.immutable import canonical_json,deterministic_gzip; raw=canonical_json(json.load(sys.stdin)); sys.stdout.buffer.write(deterministic_gzip(raw) if sys.argv[2]=="gzip" else raw)',
  scripts,gzip?'gzip':'json'],{input:JSON.stringify(value),maxBuffer:32*1024*1024});
}

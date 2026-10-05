import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {inspect} from '../../coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11/compile.mjs';
const commit='06bf4087bf5aec0e7071830ba61e99105f2c3697';
const packet='coordination/engineering/iran-pakistan-grid-proof-971-20261005-local11';
const read=p=>execFileSync('git',['show',commit+':'+p],{maxBuffer:32*1024*1024});
const hash=raw=>createHash('sha256').update(raw).digest('hex');
const staged=JSON.parse(read(packet+'/results-v1/staged-neighbors.json'));
const raw=fs.readFileSync('.cache/shared-edge-991/rounded-walk-diagnostic-v1.json');
const candidates=JSON.parse(raw).candidates;
staged.candidate=staged.baseline.map(f=>candidates[f.id]?{...f,geometry:candidates[f.id]}:f);
const result=inspect(staged);
const prior=JSON.parse(read(packet+'/results-v2/compiled.json'));
const out={experimental:true,evaluation_commit:commit,candidate_sha256:hash(raw),
  comparison:result,complete_changed_runs_equal_prior:JSON.stringify(result.changes)===JSON.stringify(prior.changes),
  limits:['Exhaustive eleven-neighbor rectangle only; no worldwide raster audit.',
    'Prior encoded-original parity is inherited from merged PR993; this check does not decode all native world partitions again.',
    'All coordinate-rounding/source/regression unknowns remain; no installation or deployment.']};
const target='.cache/shared-edge-991/rounded-grid-check-v1.json';
if(fs.existsSync(target))throw Error('Refuse output overwrite');
const payload=Buffer.from(JSON.stringify(out)+'\n');
fs.writeFileSync(target,payload);
console.log(JSON.stringify({sha256:hash(payload),change_counts:result.change_counts,
  complete_changed_runs_equal_prior:out.complete_changed_runs_equal_prior}));

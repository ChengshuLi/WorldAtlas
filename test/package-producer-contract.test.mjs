import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {packageProducerContract,compatiblePackageProducers,requireProducerInstallation} from '../scripts/package-producer-contract.mjs';

const fixture=new URL('./fixtures/package-producer-contract/',import.meta.url);
const read=name=>fs.readFileSync(new URL(name,fixture),'utf8');
const original=read('original-workflow.yml'),current=read('current-workflow.yml');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const oid=raw=>createHash('sha1').update(`blob ${Buffer.byteLength(raw)}\0`).update(raw).digest('hex');
const producer=raw=>({kind:'immediate-cloudflare-build-v1',workflows:[{path:'.github/workflows/worker-merge.yml',mode:'100644',oid:oid(raw)}]});
const compatible=(a,b)=>compatiblePackageProducers(producer(a),producer(b),{original:a,current:b});
const replace=(raw,before,after)=>{assert(raw.includes(before),'Real mutation operand must exist');return raw.replace(before,after);};

test('retained producer evidence keeps exact historical workflow and successful job identities',()=>{
  const provenance=JSON.parse(read('provenance.json'));
  for(const [name,pin]of Object.entries(provenance.files)){
    const raw=read(name);assert.equal(Buffer.byteLength(raw),pin.bytes,name);assert.equal(sha(raw),pin.sha256,name);
    if(pin.git_blob_oid)assert.equal(oid(raw),pin.git_blob_oid,name);
  }
  for(const name of ['original-job.json','current-job.json'])requireProducerInstallation(JSON.parse(read(name)));
  assert.equal(JSON.parse(read('original-job.json')).id,117617788157);
  assert.equal(JSON.parse(read('current-job.json')).id,117641280183);
  assert.equal(provenance.original_log_receipt.original_head,'a6130bbe509da73e934e2344db897c1d5b074b1c');
});

test('actual pip deferral preserves the authenticated full-build contract despite distinct whole workflow OIDs',()=>{
  assert.notEqual(oid(original),oid(current));
  assert.deepEqual(packageProducerContract(original),packageProducerContract(current));
  assert.deepEqual(compatible(original,current),packageProducerContract(original));
  assert.deepEqual(compatible(current,original),packageProducerContract(original));
});

test('unchanged producer identity retains legacy behavior without a claimed contract or workflow body',()=>{
  const legacy={kind:'immediate-cloudflare-build-v1',workflows:[{path:'.github/workflows/merge-integration-checks.yml',mode:'100644',oid:'a'.repeat(40)}]};
  assert.equal(compatiblePackageProducers(legacy,structuredClone(legacy)),null);
  assert.throws(()=>compatiblePackageProducers({...legacy,kind:'claimed-build'},legacy),/Immediate original/);
});

test('cross-workflow compatibility requires both exact immutable bodies and queue-only producer scope',()=>{
  const a=producer(original),b=producer(current),bodies={original,current};
  for(const proof of [undefined,true,{sha256:packageProducerContract(original).sha256},{original:current,current},{original,current:current+'\n'}])
    assert.throws(()=>compatiblePackageProducers(a,b,proof),/workflow bod|immutable identity/);
  for(const mutate of [p=>p.workflows.push({...p.workflows[0],path:'.github/workflows/merge-integration-checks.yml'}),
    p=>p.workflows[0].path='.github/workflows/unknown.yml',p=>p.workflows[0].mode='100755',p=>p.workflows[0].oid='main']){
    const changed=structuredClone(b);mutate(changed);assert.throws(()=>compatiblePackageProducers(a,changed,bodies),/workflow bodies/);
  }
});

const hostile=[
  ['build command',"run: npm run build:cloudflare","run: npm run build:cloudflare -- --alter"],
  ['snapshot command','run: node scripts/package-output-artifact.mjs --snapshot','run: node scripts/package-output-artifact.mjs --snapshot --alter'],
  ['capture command','run: node scripts/package-output-artifact.mjs\n','run: node scripts/package-output-artifact.mjs --alter\n'],
  ['installation command','run: python -m pip install -r requirements.txt','run: python -m pip install -r requirements-other.txt'],
  ['installation environment','- run: python -m pip install -r requirements.txt','- run: python -m pip install -r requirements.txt\n        env:\n          PYTHONPATH: altered'],
  ['installation refusal condition',"if: (needs.prepare.outputs.profile == 'full' || needs.prepare.outputs.profile == 'evidence') && steps.assembly.outputs.assembled != 'true'","if: false"],
  ['checkout revision','ref: ${{ needs.prepare.outputs.candidate }}','ref: main'],
  ['checkout action','actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803','actions/checkout@'+'f'.repeat(40)],
  ['Node version',"node-version: '24'","node-version: '22'"],
  ['Python version',"python-version: '3.12'","python-version: '3.11'"],
  ['npm installer','run: npm ci --no-audit --no-fund','run: npm install --no-audit --no-fund'],
  ['inherited environment','    steps:\n','    env:\n      NODE_OPTIONS: --require=altered\n    steps:\n'],
  ['inherited shell','    steps:\n','    defaults:\n      run:\n        shell: sh\n    steps:\n'],
  ['job container','    steps:\n','    container: node:24\n    steps:\n'],
  ['runner','    runs-on: ubuntu-latest','    runs-on: self-hosted'],
  ['extra prefix command','      - name: Snapshot original final-worker package inputs','      - run: echo altered\n      - name: Snapshot original final-worker package inputs'],
  ['capture continue-on-error','        run: node scripts/package-output-artifact.mjs\n','        run: node scripts/package-output-artifact.mjs\n        continue-on-error: true\n'],
  ['upload paths','            dist/client/','            altered/client/'],
  ['upload action','actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02','actions/upload-artifact@'+'e'.repeat(40)],
  ['unknown step effect','        run: npm run build:cloudflare','        run: npm run build:cloudflare\n        unknown-effect: true'],
  ['duplicate command','        run: npm run build:cloudflare','        run: npm run build:cloudflare\n        run: echo overwritten'],
  ['duplicate nested setup input',"          node-version: '24'","          node-version: '24'\n          node-version: '22'"],
  ['YAML alias','    runs-on: ubuntu-latest','    runs-on: *runner'],
  ['YAML anchor','    runs-on: ubuntu-latest','    runs-on: &runner ubuntu-latest'],
  ['folded command','        run: npm run build:cloudflare','        run: >\n          npm run build:cloudflare'],
  ['job fields after steps','      - name: Snapshot original final-worker package inputs','    env:\n      ALTER: true\n      - name: Snapshot original final-worker package inputs'],
];
// Mutate the integration subtree only: the same action also occurs in other
// jobs, whose steps cannot change this isolated runner's captured archive.
for(const [name,before,after]of hostile)test('producer contract refuses changed '+name,()=>{
  const start=current.indexOf('  integration:\n');assert(start>0);
  const changed=current.slice(0,start)+replace(current.slice(start),before,after);
  assert.throws(()=>compatible(original,changed),/producer|Producer|Unsupported|Supported|installation|Scientific|Duplicate|Isolated|Ordinary/);
});

test('unknown global defaults and literal script changes remain effective contract changes',()=>{
  assert.throws(()=>compatible(original,replace(current,'permissions: {}','permissions: {}\nenv:\n  ALTER: true')),/producer changed/);
  assert.throws(()=>compatible(original,replace(current,"          PACKAGE_BOOTSTRAP\n      # Retained assembly","          # literal command comment\n          PACKAGE_BOOTSTRAP\n      # Retained assembly")),/producer changed/);
  assert.throws(()=>packageProducerContract(current+'env:\n  ALTER: true\n'),/precede jobs/);
});

test('only nonexecuting YAML comments and isolated later observations are outside producer compatibility',()=>{
  const comments=replace(current,'      - name: Snapshot original final-worker package inputs','      # queue annotation\n      - name: Snapshot original final-worker package inputs');
  assert.deepEqual(compatible(original,comments),packageProducerContract(original));
  const later=replace(current,'      - name: Install browser dependencies only for tests that use Playwright','      - run: echo later-observation\n      - name: Install browser dependencies only for tests that use Playwright');
  assert.deepEqual(compatible(original,later),packageProducerContract(original));
});

test('changed-workflow admission requires successful actual installation before snapshot in the complete job',()=>{
  const baseline=JSON.parse(read('original-job.json'));
  const pip=job=>job.steps.find(row=>row.name==='Run python -m pip install -r requirements.txt');
  const snapshot=job=>job.steps.find(row=>row.name==='Snapshot original final-worker package inputs');
  for(const mutate of [job=>job.conclusion='failure',job=>job.status='in_progress',job=>pip(job).conclusion='skipped',
    job=>pip(job).status='in_progress',job=>job.steps.push({...pip(job)}),job=>job.steps=job.steps.filter(row=>row!==pip(job)),
    job=>pip(job).number=snapshot(job).number,job=>pip(job).number=snapshot(job).number+1,job=>pip(job).number='9',
    job=>snapshot(job).conclusion='skipped']){
    const job=structuredClone(baseline);mutate(job);assert.throws(()=>requireProducerInstallation(job),/producer|installation/);
  }
});

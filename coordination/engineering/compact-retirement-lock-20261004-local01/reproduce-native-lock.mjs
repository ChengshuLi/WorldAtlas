import fs from 'node:fs';import assert from 'node:assert/strict';import os from 'node:os';import path from 'node:path';import {execFileSync,spawn} from 'node:child_process';
const bin=process.env.PG_BIN;if(!bin)throw Error('Set PG_BIN to PostgreSQL18 bin directory with trailing slash');const dir=fs.mkdtempSync(path.join(os.tmpdir(),'worldatlas-retirement-lock-'));fs.chmodSync(dir,0o700);
execFileSync(bin+'initdb',['-D',dir+'/data','-A','trust','--no-locale'],{stdio:'ignore'});
execFileSync(bin+'pg_ctl',['-D',dir+'/data','-l',dir+'/server.log','-o',`-k ${dir} -p 55497 -c listen_addresses=''`,'-w','start'],{stdio:'ignore'});
const args=['-X','-Atq','-h',dir,'-p','55497','-U',os.userInfo().username,'-d','postgres','-v','ON_ERROR_STOP=1','-v','VERBOSITY=sqlstate'];
const query=sql=>execFileSync(bin+'psql',args,{input:sql,encoding:'utf8'});
let owner;
try{query('CREATE TABLE parent(id integer PRIMARY KEY); CREATE TABLE legacy(id integer REFERENCES parent(id)); INSERT INTO parent VALUES(1); INSERT INTO legacy VALUES(1); CREATE ROLE worldatlas_app LOGIN; GRANT SELECT ON parent TO worldatlas_app;');
 owner=spawn(bin+'psql',args,{stdio:['pipe','pipe','pipe']});owner.stderr.on('data',()=>{});
 const ready=new Promise(resolve=>owner.stdout.on('data',b=>{if(b.toString().includes('dropped'))resolve();}));owner.stdin.write('BEGIN; DROP TABLE legacy;\n\\echo dropped\n');await ready;
 const locks=query("SELECT c.relname,l.mode,l.granted FROM pg_locks l JOIN pg_class c ON c.oid=l.relation WHERE c.relname='parent' ORDER BY l.mode;").trim();let blocked;
 try{execFileSync(bin+'psql',args.map((v,i)=>args[i-1]==='-U'?'worldatlas_app':v),{input:"SET lock_timeout='500ms'; SELECT * FROM parent;",encoding:'utf8',stdio:['pipe','pipe','pipe']});blocked=false;}catch(error){blocked=error.stderr.includes('55P03');}
 owner.stdin.end('COMMIT;\n');await new Promise(resolve=>owner.on('close',resolve));owner=null;
 const after=query('SET ROLE worldatlas_app; SELECT * FROM parent;').trim();assert.match(locks,/parent\|AccessExclusiveLock\|t/);assert.equal(blocked,true);assert.equal(after,'1');console.log(JSON.stringify({method_id:'retirement-commit-order',kind:'code',outcome:'passed',postgres:'18.6',positive_control:'Separate application SELECT succeeds after owner COMMIT with unchanged row',negative_control:'Separate application SELECT before owner COMMIT fails with55P03',owner_drop_transaction_parent_locks:locks,application_select_before_commit_lock_timeout:blocked,application_select_after_commit:after}));
}finally{if(owner)owner.kill();execFileSync(bin+'pg_ctl',['-D',dir+'/data','-m','immediate','-w','stop'],{stdio:'ignore'});fs.rmSync(dir,{recursive:true});}

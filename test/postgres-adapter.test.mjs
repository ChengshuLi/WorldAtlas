import test from 'node:test';
import assert from 'node:assert/strict';
import {PGlite} from '@electric-sql/pglite';
import {createPostgresDatabase,createNeonDatabase,translatePostgresSql,PostgresAdapterError} from '../hosted/postgres-adapter.js';

test('placeholder translation preserves quoted values, dollar bodies and nested comments exactly',()=>{
 const sql=`SELECT ?, 'It''s ? and $1', "?", $body$? $1$body$, $$?$$, E'escaped\\\'? text', ? /* ? /* nested ? */ ? */ -- ?\n`;
 const translated=translatePostgresSql(sql,['first','second']);assert.equal(translated.query,sql.replace('SELECT ?','SELECT $1').replace(", ? /*",", $2 /*"));assert.deepEqual(translated.params,['first','second']);
 assert.deepEqual(translatePostgresSql('SELECT $1, $1, $2',[1,2]),{query:'SELECT $1, $1, $2',params:[1,2]});
 for(const [bad,values] of [['SELECT ?, $1',[1]],['SELECT $2',[1,2]],['SELECT ?',[]],["SELECT 'unterminated",[]],['SELECT /* unfinished',[]],['SELECT 1; SELECT 2',[]]])assert.throws(()=>translatePostgresSql(bad,values),PostgresAdapterError);
});

test('only reviewed inserts and index hints are adapted; SQLite metadata needs an explicit query',()=>{
 assert.match(translatePostgresSql('INSERT OR IGNORE INTO facts (id,value) VALUES (?,?)',['one','42']).query,/INSERT\s+INTO facts .* ON CONFLICT DO NOTHING/);
 const returning=translatePostgresSql('INSERT OR IGNORE INTO facts(id) VALUES (?) RETURNING id;',['one']).query;assert.match(returning,/ON CONFLICT DO NOTHING\s+RETURNING id;/);
 const commented=translatePostgresSql('INSERT OR IGNORE INTO facts(id) VALUES (?) -- retain ? comment',['one']).query;assert.match(commented,/ON CONFLICT DO NOTHING\s+-- retain \? comment$/);
 const indexed=translatePostgresSql("SELECT 'INDEXED BY fake' FROM atlas_entities INDEXED BY entities_kind_id WHERE id=?",['one']).query;assert.match(indexed,/SELECT 'INDEXED BY fake'/);assert.doesNotMatch(indexed,/atlas_entities INDEXED BY/);
 for(const sql of ['SELECT 1 FROM facts INDEXED BY unreviewed','SELECT json_object(\'a\',1)','SELECT typeof(1)','SELECT CAST(metadata AS BLOB) FROM facts','PRAGMA page_size','INSERT OR IGNORE INTO facts(id) VALUES (1) ON CONFLICT DO NOTHING'])assert.throws(()=>translatePostgresSql(sql),PostgresAdapterError);
 assert.equal(translatePostgresSql("SELECT json_type(metadata,'$.rounded'),json_extract(metadata,'$.precision'),instr(name,'a') FROM facts").query,"SELECT json_type(metadata,'$.rounded'),json_extract(metadata,'$.precision'),instr(name,'a') FROM facts",'reviewed schema functions pass unchanged; no blind JSON conversion');
});

test('injected driver returns D1 results with safe numeric dates and unchanged text evidence',async()=>{
 const calls=[],driver={async query(query,params,options){calls.push({query,params,options});return {command:'SELECT',rowCount:1,fields:[{name:'revision',dataTypeID:20},{name:'value',dataTypeID:25}],rows:[{revision:'42',valid_from:'-3000.000',valid_to:'2027',value:'"42"',metadata:'{ "precision" : "original" }',id:'007'}]};},async transaction(){return [];}};
 const db=createPostgresDatabase(driver);assert.equal(db.dialect,'postgres');
 const statement=db.prepare('SELECT * FROM facts WHERE id=?').bind('one'),all=await statement.all();assert.equal(all.success,true);assert.equal(all.meta.changes,0);assert.deepEqual(all.results[0],{revision:42,valid_from:-3000,valid_to:2027,value:'"42"',metadata:'{ "precision" : "original" }',id:'007'});assert.equal(calls[0].query,'SELECT * FROM facts WHERE id=$1');assert.deepEqual(calls[0].params,['one']);assert.equal(calls[0].options.fullResults,true);assert.equal(calls[0].options.arrayMode,false);assert.ok(calls[0].options.fetchOptions.signal instanceof AbortSignal);
 assert.equal(await statement.first('revision'),42);assert.equal((await statement.run()).meta.changes,0);await assert.rejects(statement.first('absent'),/column/);assert.throws(()=>statement.bind(),/binding/);
 for(const invalid of ['9007199254740993','12.5','NaN']){driver.query=async()=>({rowCount:1,rows:[{valid_from:invalid}]});await assert.rejects(db.prepare('SELECT 1').first(),/integer contract/);}
 driver.query=async()=>({rowCount:1,fields:[{name:'bytes',dataTypeID:20}],rows:[{bytes:'1234567'}]});assert.equal(await db.databaseBytes(),1234567);
 driver.query=async()=>({command:'SELECT',rowCount:0,rows:[]});assert.equal(await db.prepare('SELECT 1').first(),null);
});

test('batches remain ordered, atomic and ingestion-locked before identity allocation',async()=>{
 let seen;const driver={async query(){return {rows:[],rowCount:0};},async transaction(statements,options){seen={statements,options};return statements.map((statement,index)=>({command:index?'INSERT':'SELECT',rowCount:index?1:0,rows:[]}));}};
 const db=createPostgresDatabase(driver),result=await db.batch([db.prepare('INSERT OR IGNORE INTO atlas_ingestions(id) VALUES (?)').bind('receipt')]);assert.equal(seen.statements.length,2);assert.equal(seen.statements[0].query,'SELECT pg_advisory_xact_lock(807245315,1)');assert.match(seen.statements[1].query,/ON CONFLICT DO NOTHING/);assert.equal(seen.options.isolationLevel,'ReadCommitted');assert.equal(result.length,1);assert.equal(result[0].meta.changes,1);
 const other=createPostgresDatabase(driver);await assert.rejects(db.batch([other.prepare('SELECT 1')]),/different database/);assert.deepEqual(await db.batch([]),[]);
 driver.transaction=async()=>[{rows:[],rowCount:0}];await assert.rejects(db.batch([db.prepare('SELECT 1'),db.prepare('SELECT 2')]),/transaction result/);
});
test('publication and guarded imports share a lock before fresh ReadCommitted guard snapshots',async()=>{
 const calls=[],driver={async query(){return {rows:[],rowCount:0};},async transaction(statements,options){calls.push({statements,options});return statements.map(()=>({rows:[],rowCount:0}));}},db=createPostgresDatabase(driver);
 const guard=db.prepare("SELECT json_extract(CASE WHEN ?=1 THEN 'true' ELSE 'ATLAS_GEOGRAPHY_CONFLICT' END,'$')").bind(1);
 await db.batch([guard,db.prepare('INSERT OR IGNORE INTO atlas_ingestions(id) VALUES (?)').bind('pinned')]);
 await db.batch([db.prepare("UPDATE atlas_geographic_releases SET status='published',published_at=? WHERE id=? AND status='staged'").bind(1,'second')]);
 for(const call of calls){assert.equal(call.statements[0].query,'SELECT pg_advisory_xact_lock(807245315,1)');assert.equal(call.options.isolationLevel,'ReadCommitted');}
 assert.match(calls[0].statements[1].query,/ATLAS_GEOGRAPHY_CONFLICT/);assert.match(calls[1].statements[1].query,/UPDATE atlas_geographic_releases/);
 await db.batch([db.prepare('SELECT 1')]);assert.equal(calls[2].options.isolationLevel,'Serializable');assert.equal(calls[2].statements.length,1);
});

test('driver failures preserve SQLSTATE while removing credentials, payloads and server details',async()=>{
 const raw=Object.assign(new Error('password=DO_NOT_LOG and private claim text'),{code:'23505',detail:'postgresql://operator:DO_NOT_LOG@private.invalid/atlas',query:'private SQL',parameters:['private evidence']});
 const db=createPostgresDatabase({async query(){throw raw;},async transaction(){throw raw;}});
 for(const request of [()=>db.prepare('SELECT 1').all(),()=>db.batch([db.prepare('SELECT 1')])])await assert.rejects(request(),error=>{assert.equal(error.code,'23505');assert.equal(error.sqlstate,'23505');assert.equal(error.message,'PostgreSQL operation rejected (SQLSTATE 23505)');for(const key of ['detail','query','parameters','cause'])assert.equal(Object.hasOwn(error,key),false);assert.doesNotMatch(error.stack,/DO_NOT_LOG|private claim/);return true;});
 const conflict=createPostgresDatabase({async query(){throw Object.assign(new Error('private state'),{code:'40001'});},async transaction(){return [];}});await assert.rejects(conflict.prepare('SELECT 1').first(),error=>error.retryable===true&&error.sqlstate==='40001');
});

test('bounded timeouts cancel network work and preserve uncertain commit status for idempotent retries',async()=>{
 let signal;const db=createPostgresDatabase({query(_query,_params,options){signal=options.fetchOptions.signal;return new Promise(()=>{});},async transaction(){return [];}},{timeoutMs:1});
 const before=Date.now();await assert.rejects(db.prepare('SELECT 1').first(),error=>error.code==='ATLAS_DB_TIMEOUT'&&error.retryable&&error.commit_status==='unknown');assert.ok(Date.now()-before>=80,'operational timeout clamps to 100ms');assert.equal(signal.aborted,true);
 assert.throws(()=>createPostgresDatabase({query(){},transaction(){}},{timeoutMs:NaN}),/timeout/);
});

test('Neon HTTP wrapper submits lazy ordered queries as one transaction without exposing its URL',async()=>{
 let factoryOptions,transactionOptions,payload;const fixtureURL='postgresql://atlas@fixture.invalid/atlas';
 const queryFactory=(url,options)=>{assert.equal(url,fixtureURL);factoryOptions=options;return {query:async()=>({command:'SELECT',rowCount:1,rows:[{value:'unchanged'}]}),async transaction(build,settings){transactionOptions=settings;payload=build({query:(query,params)=>({query,params})});return payload.map(()=>({command:'INSERT',rowCount:1,rows:[]}));}};};
 const db=createNeonDatabase(fixtureURL,{queryFactory});assert.deepEqual(factoryOptions,{fullResults:true,arrayMode:false});assert.equal((await db.prepare('SELECT 1').first()).value,'unchanged');await db.batch([db.prepare('INSERT OR IGNORE INTO facts(id) VALUES (?)').bind('one')]);assert.equal(payload.length,1);assert.deepEqual(payload[0].params,['one']);assert.equal(transactionOptions.isolationLevel,'Serializable');assert.equal(JSON.stringify(db),'{"dialect":"postgres"}');
 assert.throws(()=>createNeonDatabase('https://private.invalid/password'),/configuration/);assert.throws(()=>createNeonDatabase(fixtureURL,{queryFactory(){throw Error('private connection password');}}),error=>!error.message.includes('password'));
});

test('actual PostgreSQL parses translated placeholders, idempotence and rollback without touching immutable evidence text',async()=>{
 const pg=new PGlite();await pg.exec('CREATE TABLE facts(id TEXT PRIMARY KEY,value TEXT,metadata TEXT,valid_from NUMERIC);CREATE TABLE atlas_ingestions(rowid BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,id TEXT UNIQUE);');
 const driver={query:(query,params)=>pg.query(query,params),transaction:(statements)=>pg.transaction(async tx=>{const results=[];for(const item of statements)results.push(await tx.query(item.query,item.params));return results;})};const db=createPostgresDatabase(driver);
 try{
  const insert=db.prepare('INSERT OR IGNORE INTO facts(id,value,metadata,valid_from) VALUES (?,?,?,?)'),evidence='{ "source" : "verbatim bytes ?" }';assert.equal((await insert.bind('one','"42"',evidence,-3000).run()).meta.changes,1);assert.equal((await insert.bind('one','"42"',evidence,-3000).run()).meta.changes,0);assert.equal((await db.prepare('SELECT * FROM facts WHERE id=?').bind('one').first()).metadata,evidence);
  await assert.rejects(db.batch([insert.bind('two','1','{}',1000),db.prepare('INSERT INTO facts(id) VALUES (?)').bind('one')]),error=>error.sqlstate==='23505');assert.equal(await db.prepare('SELECT * FROM facts WHERE id=?').bind('two').first(),null,'earlier write in failed batch rolls back');
  const receipt=await db.batch([db.prepare('INSERT OR IGNORE INTO atlas_ingestions(id) VALUES (?)').bind('receipt')]);assert.equal(receipt[0].meta.changes,1);assert.equal((await db.prepare('SELECT max(rowid) revision FROM atlas_ingestions').first()).revision,1);
 }finally{await pg.close();}
});

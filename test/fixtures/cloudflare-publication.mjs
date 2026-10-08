export function cloudflareFixture({id=100,primary='a'.repeat(40),worker='ec1f8278-3e1b-4532-b84b-79241459e54b',issue=849,comment=99}={}){
 const url=`https://github.com/ChengshuLi/WorldAtlas/issues/${issue}#issuecomment-${comment}`;
 const origin='https://worldatlas-explorer.chengshu-worldatlas.workers.dev';
 const pins={package_inventory_sha256:'e'.repeat(64),worker_sha256:'1'.repeat(64),config_sha256:'2'.repeat(64),assets_sha256:'3'.repeat(64),lookup_sha256:'4'.repeat(64),hierarchy_sha256:'5'.repeat(64),footprint_sha256:'6'.repeat(64),catalog_sha256:'7'.repeat(64),source_fingerprint:'8'.repeat(64)};
 const op={version:1,protocol_version:2,operation_id:'11111111-2222-3333-4444-555555555555',worker_id:'fixture-publisher',kind:'cloudflare',primary_commit:primary,issues:[issue],started_at:'2026-10-04T00:00:00Z',expires_at:'2026-10-04T01:00:00Z',rollback_url:url,rollback_worker_version:worker,discovery_commit:'b'.repeat(40),tool_commit:'c'.repeat(40),authored_head:'d'.repeat(40),review_url:url,runtime_review_url:url,merge_receipt_url:url,origin,backend:'postgres',read_only:true,public_reads:true,database_writes:false,release_id:'fixture-release',...pins};
 const delivery={version:1,provider:'cloudflare',primary_commit:primary,cloudflare:{origin,worker_version:worker,deployment_id:'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',registry_deployment_id:id},release_id:op.release_id,...pins,backend:'postgres',read_only:true,public_reads:true,database_writes:false,evidence_urls:[url]};
 const result={version:1,deployment_id:id,operation_id:op.operation_id,worker_id:op.worker_id,primary_commit:primary,worker_version:worker,state:'verified',cleanup_confirmed:true,public_reads:true,database_writes_enabled:false,database_information_deleted:false,original_site_and_storage_preserved:true,acceptance_url:url,delivery,issue_checks:[{issue,outcome:'verified',evidence_urls:[url]}]};
 const deployment={id,sha:primary,environment:'worldatlas-cloudflare-public',task:'worldatlas-cloudflare-public',payload:{worldatlas_cloudflare:op}};
 const status={id:id+1000,state:'success',log_url:url};
 const receipt=()=>({id:comment,html_url:url,user:{type:'User'},author_association:'OWNER',body:'<!-- worldatlas-cloudflare-result:v1\n'+JSON.stringify(result)+'\n-->'});
 return {op,deployment,status,result,delivery,url,receipt};
}

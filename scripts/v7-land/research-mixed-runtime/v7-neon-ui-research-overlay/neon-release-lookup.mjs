// Construct a bounded read-only lookup over a caller-supplied authenticated
// PostgreSQL query function. This code provisions no credentials or connection.
const SQL=`SELECT release_id,release_kind,manifest_sha256,records_sha256,manifest,records
FROM atlas.review_presentation_releases_neon_only
WHERE release_id=$1 AND octet_length(manifest::text)<=1048576
  AND octet_length(records::text)<=1048576
  AND octet_length(manifest::text)+octet_length(records::text)<=2097152
LIMIT 2`;
export function createNeonReleaseLookup(query){
 if(typeof query!=='function')throw Error('authenticated query function required');
 return async function(releaseId){
  if(typeof releaseId!=='string'||!releaseId||releaseId.length>512)throw Error('invalid release ID');
  const result=await query(SQL,[releaseId]);
  if(!result||!Array.isArray(result.rows)||result.rows.length!==1)throw Error('release not found or exceeds size limits');
  return result.rows[0];
 };
}

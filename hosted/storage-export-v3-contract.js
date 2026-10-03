/** Complete typed storage backup V3. V1/V2 migration bytes/contracts stay pinned. */
import {storageExportV2Contract} from './storage-export-v2-contract.js';
const freeze = value => { if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); } return value; };
export const storageExportV3Contract = freeze({
 ...storageExportV2Contract,
 version: 3,
 definitions: {
  ...storageExportV2Contract.definitions,
  typed_observations: {"table":"atlas_typed_observations","columns":["id","subject_id","subject_kind","field_id","value","contract_version","registry_sha256","valid_from","valid_to","method","status","source_id","is_example","metadata"],"keys":["id"],"guard":"atlas_typed_observations_immutable"},
  typed_feature_links: {"table":"atlas_typed_feature_links","columns":["id","source_entity_id","target_entity_id","relationship_type","contract_version","registry_sha256","valid_from","valid_to","method","status","source_id","is_example","metadata"],"keys":["id"],"guard":"atlas_typed_feature_links_immutable"},
  typed_retirements: {"table":"atlas_typed_retirements","columns":["id","collection","target_id","source_id","reason","replacement_id","metadata"],"keys":["id"],"guard":"atlas_typed_retirements_immutable"},
 },
 d1_migrations: [...storageExportV2Contract.d1_migrations, {"path": "drizzle/0010_typed_observations.sql", "sha256": "ed2a36e987c5754181d3ca9f03fa1a8ee04551b36f937fe706a138994e214d80"}],
 postgres_migrations: [...storageExportV2Contract.postgres_migrations, {"path": "postgres/migrations/0003_typed_observations.sql", "sha256": "f1f4c05f4f732b0398280cd2e847ac7ac63f542393d43d714097531979313f9d"}],
 d1_catalog_sha256: "6cf13cff19ae2d3cf99cc4c65d8ed704f10488ed7cf62b62391af7352c3787b8",
 postgres_catalog_sha256: "f4bd89d501a8efe65d899a4507786c7c6a5e8febc9d2b08de5a2833094bc7be3",
});
export const storageExportV3Definitions = storageExportV3Contract.definitions;
export const storageExportV3Collections = Object.freeze(Object.keys(storageExportV3Definitions));
export const storageExportV3Columns = Object.freeze(Object.fromEntries(storageExportV3Collections.map(key => [key, storageExportV3Definitions[key].columns])));
export const v3MarkerIdentity=marker=>({version:3,revision:marker.revision,counts:Object.fromEntries(storageExportV3Collections.map(key=>[key,marker.counts[key]])),geographic_releases_sha256:marker.geographic_releases_sha256,footprint_versions_sha256:marker.footprint_versions_sha256,catalog_sha256:marker.catalog_sha256,contract:marker.contract});

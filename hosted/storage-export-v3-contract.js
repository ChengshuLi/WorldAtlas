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
 d1_migrations: [...storageExportV2Contract.d1_migrations, {"path": "drizzle/0010_typed_observations.sql", "sha256": "672cb4f723a84ce2958f90f7c5d1fe517d566d6753da520ec3246a00dfe234c1"}],
 postgres_migrations: [...storageExportV2Contract.postgres_migrations, {"path": "postgres/migrations/0003_typed_observations.sql", "sha256": "0c9c1c402c0f1ee707a0083199ea07314233846deb9fddb79723108a0c439041"}],
 d1_catalog_sha256: "e7474b3d88f1d7d4b4c33b8b2581a1d17d59039abc73d8bd076078ab92639616",
 postgres_catalog_sha256: "cd51f2e42fb343cb4994a2c25a08c96d768c5fdeddfe8a56931ad3e7a694b26c",
});
export const storageExportV3Definitions = storageExportV3Contract.definitions;
export const storageExportV3Collections = Object.freeze(Object.keys(storageExportV3Definitions));
export const storageExportV3Columns = Object.freeze(Object.fromEntries(storageExportV3Collections.map(key => [key, storageExportV3Definitions[key].columns])));
export const v3MarkerIdentity=marker=>({version:3,revision:marker.revision,counts:Object.fromEntries(storageExportV3Collections.map(key=>[key,marker.counts[key]])),geographic_releases_sha256:marker.geographic_releases_sha256,footprint_versions_sha256:marker.footprint_versions_sha256,catalog_sha256:marker.catalog_sha256,contract:marker.contract});

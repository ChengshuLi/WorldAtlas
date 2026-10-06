import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const dir = path.dirname(new URL(import.meta.url).pathname);
const root = process.cwd();
const indent = depth => ' '.repeat(depth * 2);
function stableJSON(value, depth = 0) {
  if (Array.isArray(value)) {
    if (!value.length) return '[]';
    if (value.every(item => item === null || ['string', 'number', 'boolean'].includes(typeof item))) return `[${value.map(item => JSON.stringify(item)).join(', ')}]`;
    return `[\n${value.map(item => `${indent(depth + 1)}${JSON.stringify(item)}`).join(',\n')}\n${indent(depth)}]`;
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value);
    if (!entries.length) return '{}';
    return `{\n${entries.map(([key, item]) => `${indent(depth + 1)}${JSON.stringify(key)}: ${stableJSON(item, depth + 1)}`).join(',\n')}\n${indent(depth)}}`;
  }
  return JSON.stringify(value);
}
const repro = JSON.parse(fs.readFileSync(path.join(dir, 'scope-reproduction.json'), 'utf8'));
const hierarchy = JSON.parse(fs.readFileSync(path.resolve(dir, '../../hierarchy.json'), 'utf8'));
const byId = new Map(hierarchy.map((item) => [item.id, item]));
const evidence = {
  AGO: {
    basis: 'The pinned 2018 geoBoundaries layer identifies these source features as municipalities. Angola INE 2024 final census results state that the census was collected on the former 18-province DPA, then adjusted under Law 14/24 (5 September 2024) to 21 provinces, 326 municipalities, and 378 communes. The report describes municipality territory changes, including Cacuaco/Sequele and Cazenga/Hoji-ya-Henda. A same-name join therefore cannot prove current territorial identity or province parentage.',
    roster: 'historical_role_and_name_crosswalk_supported_current_successor_unresolved',
    boundary: 'insufficient_evidence_no_authoritative_current_feature_geometry_compared',
    disposition: 'insufficient-evidence',
    followups: [1046],
  },
  MWI: {
    basis: 'The pinned 2020 geoBoundaries layer has 28 district features. The official NSO 2018 census report Table A3 lists the 28 district names under three regions and separately lists Blantyre City, Lilongwe City, Mzuzu City, and Zomba City as urban statistical rows. OCHA’s COD-AB history documents a genuine 28-versus-32 level-2 model ambiguity; the NSO/OCHA COD-AB version 02 (valid from 2023-04-05) uses 32 features including the four city districts. These facts confirm a historical 28-district scheme, not unambiguous completeness/current administrative semantics or boundary equivalence.',
    roster: 'historical_role_and_region_crosswalk_supported_28_vs_32_current_model_unresolved',
    boundary: 'insufficient_evidence_no_exact_2023_COD_AB_geometry_comparison_yet',
    disposition: 'insufficient-evidence',
    followups: [1045],
  },
  MOZ_GAZA_TETE: {
    basis: 'The pinned 2019 geoBoundaries layer assigns the listed district features to Gaza and Tete. INE’s 2024 Gaza and Tete provincial yearbooks publish province-specific district tables/rosters matching the names and parents of these 29 scoped features (Gaza 14; Tete 15). This supports named role and parent at roster level but does not establish geometry, completeness outside this packet, legal status, or source boundary accuracy.',
    roster: '2024_official_roster_name_and_parent_crosswalk_supported',
    boundary: 'insufficient_evidence_no_official_district_geometry_compared',
    disposition: 'insufficient-evidence',
    followups: [1042],
  },
  MOZ_MAPUTO: {
    basis: 'INE’s 2024 Maputo Province yearbook table lists eight provincial district units including Cidade da Matola and excludes Cidade de Maputo. Its location map distinguishes Cidade de Maputo from Província de Maputo at the national view and labels eight districts inside the province. INE separately publishes a Cidade de Maputo yearbook, and the 2017 census metadata says the city has seven municipal districts. The atlas assigns the whole Cidade De Maputo feature under the distinct Maputo Province parent; this parent relationship needs correction to a separate Maputo City administrative parent after the full roster integration identifies the canonical node. Geometry equivalence is not inferred.',
    roster: '2024_province_roster_and_map_support_eight_province_districts;_maputo_city_separate',
    boundary: 'parent_correction_needed; source_boundary_accuracy_still_unverified',
    disposition: 'correction-needed',
    followups: [1042],
  },
  MOZ_MAPUTO_OTHER: {
    basis: 'INE’s 2024 Maputo Province yearbook table enumerates eight units, exactly including the eight scoped features other than Cidade de Maputo: Cidade da Matola, Boane, Magude, Manhiça, Marracuene, Matutuine, Moamba, and Namaacha. Its location map distinguishes Cidade de Maputo nationally from Province of Maputo, but the inset label “Maputo” does not exactly match the table’s “Cidade da Matola”; the table roster supports these named parent assignments while the map is not a boundary crosswalk. 2019 source geometry and current district boundaries remain unverified. Mozambique’s full roster/source lineage is tracked by #1042.',
    roster: '2024_province_table_roster_supports_eight_names;_map_inset_name_crosswalk_not_resolved',
    boundary: 'insufficient_evidence_no_official_geometry_compared',
    disposition: 'insufficient-evidence',
    followups: [1042],
  },
};

const rows = repro.rows.map((r) => {
  let ev;
  if (r.iso === 'AGO') ev = evidence.AGO;
  else if (r.iso === 'MWI') ev = evidence.MWI;
  else if (r.source_name === 'Cidade De Maputo') ev = evidence.MOZ_MAPUTO;
  else if (r.assigned_parent_id === 'framework:province:maputo:fbf9376e8f46') ev = evidence.MOZ_MAPUTO_OTHER;
  else ev = evidence.MOZ_GAZA_TETE;
  const p = byId.get(r.assigned_parent_id);
  const duplicateCuanzaParent = r.iso === 'AGO' && r.assigned_parent_id === 'framework:province:cuanza-norte:60d130f0de3e';
  return {
    id: r.id,
    country: r.iso,
    location_name: r.atlas_name,
    source_name: r.source_name,
    source_vintage: r.source_year,
    source_role: r.source_role,
    assigned_parent_id: r.assigned_parent_id,
    assigned_parent_name: p?.name ?? null,
    classification: ev.disposition,
    role_and_roster_finding: ev.roster,
    source_geometry_finding: ev.boundary,
    rationale: ev.basis,
    native_source_feature_matched: true,
    source_name_crosswalk_matched: r.normalized_name_match,
    structural_diagnostics: {
      source_geometry_type: r.source_geometry_type,
      polygon_components: r.source_polygon_component_count,
      rings_closed: r.source_rings_closed,
      finite_coordinates: r.source_coordinates_finite,
      source_atlas_geometry_byte_identical: r.atlas_source_geometry_identical,
      interpretation: 'structural diagnostics only; no topology, accuracy, completeness or territorial correctness conclusion',
    },
    source_registry_id: r.source_id,
    source_native_id: r.native_shape_id,
    source_artifact_sha256: r.iso === 'AGO'
      ? '44e58b2a8c2fefb9369294a32e2adde3e3637b9e02e8f1e2c53b400bec04f404'
      : r.iso === 'MOZ'
        ? '5f04bb75bcb08092451f8626f7113830abfe726c1fad5309107309ab6cceab65'
        : '5fe9b6313ee3eaf6d2b8a4579b7a7fa75dc1b16b9324a436f5a359da23527ea6',
    atlas_part_path: r.atlas_part,
    atlas_part_sha256: r.atlas_part_sha256,
    followup_issues: [...ev.followups],
    additional_parent_ambiguity: duplicateCuanzaParent
      ? 'The other framework:province:Cuanza Norte node also appears in this exact scope under a different ID; integration must establish a single canonical parent. No hierarchy mutation is made here.'
      : null,
    evidence_refs: r.iso === 'AGO'
      ? ['GB-AGO-2018', 'AGO-INE-RGPH-2024']
      : r.iso === 'MWI'
        ? ['GB-MWI-2020', 'MWI-NSO-CENSUS-2018', 'MWI-OCHA-CODAB-HISTORY', 'MWI-CODAB-2023']
        : r.assigned_parent_id === 'framework:province:maputo:fbf9376e8f46'
          ? ['GB-MOZ-2019', 'MOZ-INE-CENSUS-2017', 'MOZ-INE-MAPUTO-YEARBOOK-2024', 'MOZ-INE-MAPUTO-YEARBOOK-MAP-2024', 'MOZ-INE-CITY-MAPUTO-YB-2024', 'MOZ-FOLLOWUP-1042']
          : ['GB-MOZ-2019', 'MOZ-INE-GAZA-YEARBOOK-2024', 'MOZ-INE-TETE-YEARBOOK-2024'],
  };
});

const output = {
  version: 1,
  issue: 411,
  scope_reproduction_sha256: crypto.createHash('sha256').update(fs.readFileSync(path.join(dir, 'scope-reproduction.json'))).digest('hex'),
  baseline_commit: repro.baseline_commit,
  classification_policy: 'Each row receives one issue-required overall classification. Overall status remains insufficient when the identity/role/parent roster is supported but a key required dimension (current territorial identity, boundary evidence, completeness or parent attribution) is unresolved. A correction-needed status is reserved for a specific sourced present-parent relationship concern. Counts and structural diagnostics never certify correctness.',
  cross_scope_findings: [
    {
      affected_scope: 'MWI',
      finding: 'The pinned 2020 source has 28 districts and the issue owns those 28. Official NSO 2018 census table separately lists Blantyre City, Lilongwe City, Mzuzu City and Zomba City; NSO/OCHA COD-AB version 02 (valid 2023-04-05) is documented as a 32-feature model including these four city districts. OCHA records the 28/32 distinction as an administrative/operational ambiguity. These four names are not packet subjects, and no additive IDs/geometries are proposed here. Boundary completeness and which tier convention the atlas should represent require a bounded source/decision follow-up.',
      omitted_city_units: ['Blantyre City', 'Lilongwe City', 'Mzuzu City', 'Zomba City'],
      classification: 'insufficient-evidence',
      followup_issue: 1045,
    },
    {
      affected_scope: 'AGO',
      finding: 'The exact pinned 2018 collection has 161 features while 157 belong to this packet. Four Cabinda source IDs fall outside this packet and are absent from all pinned atlas partitions; #896 already owns their current-ten-municipality source restoration/correction work. Do not fold those IDs into this packet or count their absence as approval for the 157 subjects.',
      outside_ids: ['gb:AGO:ADM2:16411231B22766430211667', 'gb:AGO:ADM2:16411231B679187258105', 'gb:AGO:ADM2:16411231B42954517222252', 'gb:AGO:ADM2:16411231B63355352791940'],
      classification: 'out-of-scope-handoff',
      followup_issues: [896, 1046],
    },
    {
      affected_scope: 'MOZ',
      finding: 'The source has 159 features while this exact issue owns 38; the other 121 are reserved by disjoint packet #412. The seven district units in Maputo City are an administrative context for the whole-Cidade de Maputo feature, not seven additional packet IDs. The complete Mozambique 159/161 source and parent question is already tracked by #1042.',
      classification: 'out-of-scope-handoff',
      followup_issues: [412, 1042],
    }
  ],
  structural_and_granularity_screen: {
    multipart_source_features: rows.filter((row) => row.structural_diagnostics.polygon_components > 1).map((row) => ({
      id: row.id,
      name: row.location_name,
      country: row.country,
      source_components: row.structural_diagnostics.polygon_components,
      review_needed: 'Check official source meaning, disconnected districts/islands and neighboring coverage against authoritative data; component count alone does not identify a real island or prove complete coverage.'
    })),
    city_named_source_features: rows.filter((row) => /^cidade\b/i.test(row.source_name)).map((row) => ({id: row.id, name: row.location_name, country: row.country, source_role: row.source_role, classification: row.classification})),
    duplicate_same_name_parent_nodes: [{
      name: 'Cuanza Norte',
      parent_ids: ['framework:province:cuanza-norte:0f18f00b9a8c', 'framework:province:cuanza-norte:60d130f0de3e'],
      affected_member_ids: rows.filter((row) => row.additional_parent_ambiguity).map((row) => row.id),
      disposition: 'insufficient-evidence; resolve in #1046'
    }],
    screening_limits: 'Feature names, source ADM2 labels, multipart counts, and sibling counts are candidate screens only. No source-versus-source topology, boundary accuracy, complete component ownership, oversized-territory measure, or administrative remainder test is claimed.'
  },
  counts: Object.fromEntries(['justified', 'correction-needed', 'insufficient-evidence'].map((k) => [k, rows.filter((r) => r.classification === k).length])),
  rows,
};
const args = process.argv.slice(2);
const outputAt = args.indexOf('--output');
const outputName = outputAt >= 0 ? args[outputAt + 1] : path.join(dir, 'row-assessments.json');
if (!outputName) throw new Error('--output requires a path');
const outputPath = path.isAbsolute(outputName) ? outputName : path.resolve(root, outputName);
fs.writeFileSync(outputPath, `${stableJSON(output)}\n`);
console.log(`Assessments written to ${outputPath}`);

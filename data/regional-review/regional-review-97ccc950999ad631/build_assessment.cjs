#!/usr/bin/env node
"use strict";

// Build per-subject and per-province source assessments from retained inputs.
// This records reproducible identity/representative-point screens; it does not
// compute a polygon overlay or certify complete geography.
const fs = require("node:fs");
const path = require("node:path");
const zlib = require("node:zlib");
const crypto = require("node:crypto");

const ROOT = __dirname;
const REPO = path.resolve(ROOT, "../../..");
const SOURCES = path.join(ROOT, "sources");
const CLAIM = "codex-01a10948-7d38-75d0-bc01-4cc28ea41f49";
const BASELINE_COMMIT = "ee1b368bcaeb1fb114e3a5d0d9d3a2e06d633fa7";
const ISSUE = 473;
const readJson = (p) => JSON.parse(fs.readFileSync(p, "utf8"));
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");
const norm = (s) => String(s || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
const pointInRing = (pt, ring) => {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    const crosses = ((yi > pt[1]) !== (yj > pt[1])) &&
      (pt[0] < ((xj - xi) * (pt[1] - yi)) / (yj - yi || Number.EPSILON) + xi);
    if (crosses) inside = !inside;
  }
  return inside;
};
const pointInPolygon = (pt, polygon) => polygon.length > 0 && pointInRing(pt, polygon[0]) && !polygon.slice(1).some((r) => pointInRing(pt, r));
const covers = (pt, geometry) => {
  if (!geometry || !geometry.coordinates) return false;
  if (geometry.type === "Polygon") return pointInPolygon(pt, geometry.coordinates);
  if (geometry.type === "MultiPolygon") return geometry.coordinates.some((p) => pointInPolygon(pt, p));
  return false;
};
function geometryStats(geometry) {
  if (!geometry || !geometry.coordinates) return { geometry_type: geometry?.type || null, components: 0, rings: 0, vertices: 0, area_km2_spherical_screen: null, bbox: null };
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.type === "MultiPolygon" ? geometry.coordinates : [];
  let rings = 0, vertices = 0, area = 0;
  const xs = [], ys = [];
  const ringArea = (ring) => {
    let total = 0;
    for (let i = 0; i + 1 < ring.length; i++) {
      const [lon1, lat1] = ring[i], [lon2, lat2] = ring[i + 1];
      total += (lon2 - lon1) * Math.PI / 180 * (2 + Math.sin(lat1 * Math.PI / 180) + Math.sin(lat2 * Math.PI / 180));
    }
    return Math.abs(total * (6371008.8 ** 2) / 2);
  };
  for (const polygon of polygons) {
    rings += polygon.length;
    for (let j = 0; j < polygon.length; j++) {
      const ring = polygon[j]; vertices += ring.length;
      for (const [x, y] of ring) { xs.push(x); ys.push(y); }
      const a = ringArea(ring);
      area += j === 0 ? a : -a;
    }
  }
  return { geometry_type: geometry.type, components: polygons.length, rings, vertices,
    area_km2_spherical_screen: Number((Math.abs(area) / 1e6).toFixed(3)),
    bbox: xs.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : null };
}
const dejson = (filename) => JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(SOURCES, filename))));
const write = (filename, value) => fs.writeFileSync(path.join(ROOT, filename), JSON.stringify(value, null, 2) + "\n");

function main() {
  const scope = readJson(path.join(ROOT, "issue-scope-pinned.json"));
  const issueSnapshotPath = "/tmp/worldatlas-issue-473.json";
  if (fs.existsSync(issueSnapshotPath)) {
    const issue = readJson(issueSnapshotPath);
    const bodyScope = JSON.parse(issue.body.match(/```json\n([\s\S]*?)\n```/)[1]);
    if (JSON.stringify(bodyScope) !== JSON.stringify(scope)) throw new Error("Pinned issue scope changed; refresh from GitHub before rebuilding.");
  }
  if (scope.location_count !== 229 || scope.member_location_ids.length !== 229 || new Set(scope.member_location_ids).size !== 229) throw new Error("Issue subject roster is not exactly 229 unique IDs.");
  const git = require("node:child_process");
  const baselineWorldIndex = git.execFileSync("git", ["-C", REPO, "show", BASELINE_COMMIT + ":data/world-index.json"]);
  const currentWorldIndex = fs.readFileSync(path.join(REPO, "data/world-index.json"));
  if (sha(baselineWorldIndex) !== sha(currentWorldIndex)) throw new Error("Current world-index differs from the pinned PR-baseline commit; refresh assessment source before rebuilding.");

  const release = readJson(path.join(REPO, "data/validation/macro-publication-v5.json"));
  for (const key of ["id", "version", "hierarchy_sha256", "footprints_sha256"]) {
    if (release.release[key] !== scope.release[key]) throw new Error("Pinned issue release differs from macro publication receipt: " + key);
  }
  if (release.macro_certificate_sha256 !== scope.macro_certificate_sha256) throw new Error("Pinned issue macro certificate differs from publication proof.");
  const index = readJson(path.join(REPO, "data/world-index.json"));
  const allFeatures = index.parts.flatMap((part) => readJson(path.join(REPO, "data", part)).features);
  const byId = new Map(allFeatures.map((feature) => [feature.properties.id, feature]));
  const sourceDefs = {
    LBR: { name: "Liberia", file: "geoboundaries-lbr-adm2-2021.geojson.gz", adm1: "geoboundaries-lbr-adm1-2021.geojson.gz", vintage: "2021", role: "District", roleApi: "Districts", license: "CC BY 3.0 IGO" },
    MLI: { name: "Mali", file: "geoboundaries-mli-adm2-2017.geojson.gz", adm1: "geoboundaries-mli-adm1-2017.geojson.gz", vintage: "2017", role: "Cercle", roleApi: "Cercle", license: "CC BY 4.0" },
    MRT: { name: "Mauritania", file: "geoboundaries-mrt-adm2-2020.geojson.gz", adm1: "geoboundaries-mrt-adm1-2020.geojson.gz", vintage: "2020", role: "Mauritania (not a unit name)', with official hierarchy unresolved", roleApi: "Mauritania", license: "CC BY 3.0 IGO" }
  };
  const sourceFeatures = {};
  const sourceRoster = {};
  const sourceAdmin1 = {};
  const sourceRegister = readJson(path.join(SOURCES, "register.json"));
  for (const [code, spec] of Object.entries(sourceDefs)) {
    const entry = sourceRegister.sources.find((item) => item.country_code === code);
    const adm2Gzip = fs.readFileSync(path.join(SOURCES, path.basename(entry.retained_gzip_path)));
    const adm2Bytes = zlib.gunzipSync(adm2Gzip);
    if (sha(adm2Gzip) !== entry.retained_gzip_sha256 || sha(adm2Bytes) !== entry.original_sha256 || adm2Bytes.length !== entry.original_bytes) throw new Error("Pinned source bytes changed: " + code + " ADM2");
    const adm1Gzip = fs.readFileSync(path.join(SOURCES, path.basename(entry.adm1_source.retained_gzip_path)));
    const adm1Bytes = zlib.gunzipSync(adm1Gzip);
    if (sha(adm1Gzip) !== entry.adm1_source.retained_gzip_sha256 || sha(adm1Bytes) !== entry.adm1_source.sha256 || adm1Bytes.length !== entry.adm1_source.bytes) throw new Error("Pinned source bytes changed: " + code + " ADM1");
    const metadataPath = path.join(SOURCES, "geoboundaries-current-metadata-" + code.toLowerCase() + ".json");
    const metadataBytes = fs.readFileSync(metadataPath);
    entry.current_metadata_sha256 = sha(metadataBytes);
    entry.current_metadata_bytes = metadataBytes.length;
    entry.current_metadata_path = "sources/" + path.basename(metadataPath);
    const fc = dejson(spec.file);
    const pfc = dejson(spec.adm1);
    sourceFeatures[code] = new Map(fc.features.map((f) => [f.properties.shapeID, f]));
    sourceRoster[code] = fc.features;
    sourceAdmin1[code] = pfc.features;
  }
  const ecoReceipt = readJson(path.join(SOURCES, "resolve-query-receipt.json"));
  const ecoGzip = fs.readFileSync(path.join(SOURCES, path.basename(ecoReceipt.retained_gzip_path)));
  const ecoBytes = zlib.gunzipSync(ecoGzip);
  if (sha(ecoGzip) !== ecoReceipt.retained_gzip_sha256 || sha(ecoBytes) !== ecoReceipt.response_sha256 || ecoBytes.length !== ecoReceipt.response_bytes) throw new Error("Retained RESOLVE query bytes differ from receipt.");
  const ecoCollection = JSON.parse(ecoBytes);
  const ecoById = new Map(ecoCollection.features.map((f) => [String(f.properties.ECO_ID), f]));
  const hierarchy = new Map(allFeatures.map((feature) => [feature.properties.id, feature.properties]));
  for (const record of readJson(path.join(REPO, "data/hierarchy.json"))) hierarchy.set(record.id, record);
  const members = [];
  const rows = [];
  const directRosterIds = new Set();
  const sourceCodeByOwner = { Liberia: "LBR", Mali: "MLI", Mauritania: "MRT" };

  for (const id of scope.member_location_ids) {
    const feature = byId.get(id);
    if (!feature) throw new Error("Subject absent from baseline geography: " + id);
    const p = feature.properties;
    const md = p.metadata || {};
    const parentChain = [];
    let cursor = p.parent_id;
    while (cursor) {
      const ancestor = hierarchy.get(cursor);
      if (!ancestor) { parentChain.push({ id: cursor, missing_from_current_index: true }); break; }
      parentChain.push({ id: cursor, name: ancestor.name, parent_id: ancestor.parent_id || null, source_id: ancestor.metadata?.source_id || null });
      cursor = ancestor.parent_id;
    }
    const code = sourceCodeByOwner[p.reference_owner];
    const spec = sourceDefs[code];
    if (!spec) throw new Error("Unexpected owner for scoped subject " + id + ": " + p.reference_owner);
    const physical = id.startsWith("atlas:physical:");
    let sourceId = md.source_id;
    let sourceMemberId = physical ? (md.source_member_ids || [])[0] : id;
    let nativeId = physical ? md.original_id : id.split(":").slice(-1)[0];
    const nativeFeature = sourceFeatures[code].get(nativeId);
    if (!nativeFeature) throw new Error("Pinned source feature missing for " + id + ": " + nativeId);
    const sourceProps = nativeFeature.properties;
    directRosterIds.add(code + ":" + nativeId);
    const representative = md.representative_point || null;
    const ecoId = physical ? String(sourceId).replace(/^resolve:/, "") : null;
    const ecoFeature = physical ? ecoById.get(ecoId) : null;
    if (physical && !ecoFeature) throw new Error("Referenced ecoregion not in retained query: " + ecoId);
    const ecoProps = ecoFeature?.properties || null;
    const baseContainsPoint = representative ? covers(representative, nativeFeature.geometry) : null;
    const atlasContainsPoint = representative ? covers(representative, feature.geometry) : null;
    const ecoContainsPoint = representative && ecoFeature ? covers(representative, ecoFeature.geometry) : null;
    const adm1Candidates = representative
      ? sourceAdmin1[code].filter((f) => covers(representative, f.geometry)).map((f) => f.properties.shapeName).sort()
      : [];
    const atlasProvinceName = parentChain[0]?.name || null;
    const parentPointMatch = adm1Candidates.length === 1 && norm(adm1Candidates[0]) === norm(atlasProvinceName);
    const sourceGeometry = geometryStats(nativeFeature.geometry);
    const subjectSourceGeometry = geometryStats(physical ? ecoFeature.geometry : nativeFeature.geometry);
    const currentGeometry = geometryStats(feature.geometry);
    const adm1ForArea = sourceAdmin1[code].find((f) => norm(f.properties.shapeName) === norm(atlasProvinceName)) ||
      sourceAdmin1[code].find((f) => adm1Candidates.length === 1 && norm(f.properties.shapeName) === norm(adm1Candidates[0]));
    const adm1Geometry = adm1ForArea ? geometryStats(adm1ForArea.geometry) : null;
    const sourceAreaRatio = !physical && adm1Geometry?.area_km2_spherical_screen
      ? Number((sourceGeometry.area_km2_spherical_screen / adm1Geometry.area_km2_spherical_screen).toFixed(6)) : null;
    const sourceParentFeature = adm1ForArea;
    const sourceParentChildren = sourceParentFeature ? sourceRoster[code].filter((f) => covers(representative, sourceParentFeature.geometry) && covers(representative, f.geometry)).length : null;
    const sourceUnitEqualsParent = !physical && sourceParentFeature && JSON.stringify(nativeFeature.geometry) === JSON.stringify(sourceParentFeature.geometry);

    let status = "insufficient-evidence";
    let finding;
    let recommendation;
    if (physical) {
      status = "correction-needed";
      finding = "The retained record is a named ecoregion portion of a source administrative predecessor. Its current source_role is an administrative label, while RESOLVE ECO_ID and ECO_NAME identify ecological geography. Representative-point checks are a point screen only; the complete intersection geometry was not independently rebuilt.";
      recommendation = "Engineering should correct the source role and selection rationale to describe a RESOLVE ecoregion portion clipped to the named geoBoundaries ADM2 predecessor; preserve stable ID, source-member ID, geometry and parent pending a separately reviewed extent/parent decision.";
    } else if (code === "MLI" && norm(sourceProps.shapeName) === "bamako" && sourceUnitEqualsParent) {
      status = "correction-needed";
      finding = "The pinned ADM2 feature named Bamako is byte-for-byte geometry-equal to the pinned ADM1 feature named Bamako, and the scoped province has one subordinate feature. The geoBoundaries national ADM2 metadata calls the layer Cercle, while Mali's current legal structure separately names the District of Bamako and regional Cercles. This is a repeated-tier/special-unit role ambiguity, not a demonstrated bad footprint.";
      recommendation = "Engineering should verify Bamako's separate district/cercle role against the current official 2023 source, then correct only its role/rationale if supported. Preserve its ID, geometry and parent until current source review; do not merge or delete the feature from area equality alone.";
    } else if (code === "MRT") {
      status = "correction-needed";
      finding = "geoBoundaries current metadata labels this 2020 ADM2 source canonical role 'Mauritania', not an administrative unit. A 2023 UK government factsheet describes 15 wilayas, 54 moughataa/departments and communes below; the source has 57 polygons. Exact current crosswalk and license compatibility are not established.";
      recommendation = "Engineering should not retain 'Mauritania' as an administrative source role; source restoration/review should crosswalk the 2020 polygons to DCIG/UN SALB 2021–2023 or later official moughataa data before changing labels, parent links or footprints.";
    } else {
      finding = code === "MLI"
        ? "The 2017 source explicitly identifies Cercles, but Mali's 2023 Law 2023-006 established 19 regions and 159 circles. This older 50-feature national set cannot establish current regional parents or completeness; do not infer a one-to-one transfer from name alone."
        : "The 2021 source explicitly identifies administrative Districts and contains 136 national features. The assigned subset is only 127 members and LISGIS publishes 2022 district boundaries; an independent current name/code/geometry crosswalk and settlement/physical-land completeness evidence were not reproduced here.";
      recommendation = code === "MLI"
        ? "Obtain the official post-2023 district/region boundary source, crosswalk all assigned source IDs and exact new parents, and coordinate a bounded correction if a changed circle/region affects a shared parent."
        : "Compare the exact 127 assigned 2021 district features with LISGIS 2022 district boundaries and preserve explicit excluded-subset accounting; no transferred IDs or bounds without a sourced crosswalk.";
    }
    rows.push({
      subject_id: id, name: p.name, reference_owner: p.reference_owner,
      subject_kind: physical ? "ecoregion portion" : "administrative source unit",
      individual_status: status, source_id: sourceId, source_member_id: sourceMemberId,
      native_source_id: nativeId, source_name: sourceProps.shapeName,
      source_role_in_issue: md.source_role || null,
      publisher_canonical_role: spec.roleApi,
      source_vintage: physical ? md.reference_year : spec.vintage,
      source_license: physical ? (ecoProps.LICENSE || "CC BY 4.0") + "; administrative predecessor license " + spec.license : spec.license,
      source_geojson_shape_type: sourceProps.shapeType,
      source_geometry_measurement_role: physical ? "administrative predecessor polygon; not the ecological portion or clipped subject geometry" : "administrative source unit polygon",
      source_feature_geometry_screen: subjectSourceGeometry,
      parent_id: p.parent_id, parent_name: parentChain[0]?.name || null,
      parent_chain: parentChain, atlas_location_basis: md.location_basis || md.administrative_level || null,
      adm1_source_representative_point_candidates: adm1Candidates,
      adm1_source_point_agrees_with_atlas_parent_name: parentPointMatch,
      atlas_selection_reason: md.selection_reason || null,
      ecoregion_id: ecoId, ecoregion_name: ecoProps?.ECO_NAME || null,
      eco_feature_license: ecoProps?.LICENSE || null,
      representative_point: representative,
      representative_point_in_baseline_feature: atlasContainsPoint,
      representative_point_in_native_adm2_source: baseContainsPoint,
      representative_point_in_resolve_ecoregion: ecoContainsPoint,
      native_source_component_count: sourceGeometry.components,
      native_source_ring_count: sourceGeometry.rings,
      native_source_vertex_count: sourceGeometry.vertices,
      native_source_bbox_wgs84: sourceGeometry.bbox,
      native_source_area_km2_spherical_screen: sourceGeometry.area_km2_spherical_screen,
      native_source_area_measurement_limit: physical ? "Area describes the full administrative predecessor, not the ecological portion; its actual intersection area was not computed." : "Spherical source-polygon screen; not an equal-area overlay result.",
      source_adm1_area_km2_spherical_screen: adm1Geometry?.area_km2_spherical_screen ?? null,
      native_adm2_to_source_adm1_area_ratio_screen: sourceAreaRatio,
      source_scale_screen_flag: sourceAreaRatio >= 0.8 ? "large: at least 80% of candidate source ADM1 area; inspect tier/parent semantics" : null,
      source_predecessor_equals_source_adm1_geometry: physical ? null : Boolean(sourceUnitEqualsParent),
      source_parent_children_at_representative_point: sourceParentChildren,
      source_parent_repeated_tier_flag: sourceParentChildren === 1 && (sourceUnitEqualsParent || sourceAreaRatio >= 0.8)
        ? "single source ADM2 child at the representative point and same/near-coextensive with source ADM1; tier purpose needs individual review" : null,
      baseline_current_component_count: currentGeometry.components,
      baseline_current_ring_count: currentGeometry.rings,
      baseline_current_vertex_count: currentGeometry.vertices,
      baseline_current_bbox_wgs84: currentGeometry.bbox,
      boundary_assessment: physical
        ? "No complete extent overlay; source-point screen only."
        : "No full polygon overlay or contemporary official crosswalk; pinned source identity/name and current ancestor chain retained.",
      completeness: "Not established: source polygons do not establish all settlements, landforms, islands, territorial extents or current administrative completeness.",
      finding, recommendation,
      evidence: physical
        ? ["issue-scope-pinned.json", "baseline-members.geojson.gz", "sources/resolve-query-receipt.json", "sources/resolve-ecoregions-53-71-745-842-846.geojson.gz", "sources/" + spec.file]
        : ["issue-scope-pinned.json", "baseline-members.geojson.gz", "sources/register.json", "sources/" + spec.file]
    });
    members.push({
      type: "Feature", id, geometry: feature.geometry,
      properties: {
        id, name: p.name, parent_id: p.parent_id, reference_owner: p.reference_owner,
        metadata: md, source_native_id: nativeId,
        geometry_sha256: sha(Buffer.from(JSON.stringify(feature.geometry)))
      }
    });
  }
  if (new Set(rows.map((r) => r.subject_id)).size !== 229) throw new Error("Assessment subjects are not unique.");
  const assessedIds = rows.map((r) => r.subject_id);
  if (JSON.stringify(assessedIds) !== JSON.stringify(scope.member_location_ids)) throw new Error("Assessment order/IDs differ from the issue-pinned roster.");

  const provinceGroups = new Map();
  for (const row of rows) {
    const province = row.parent_chain[0];
    if (!provinceGroups.has(province.id)) provinceGroups.set(province.id, { province_id: province.id, province_name: province.name, country: row.reference_owner, subject_ids: [], statuses: new Set(), source_ids: new Set() });
    const group = provinceGroups.get(province.id);
    group.subject_ids.push(row.subject_id); group.statuses.add(row.individual_status); group.source_ids.add(row.source_id);
  }
  const provinces = [...provinceGroups.values()].map((g) => ({
    ...g, subject_count: g.subject_ids.length, statuses: [...g.statuses], source_ids: [...g.source_ids],
    individual_status: g.statuses.has("correction-needed") ? "correction-needed" : "insufficient-evidence",
    scope_note: "This packet owns only its exact subject cohort; country/province remainder and neighboring location evidence may be in other batches. No parent aggregate is changed or certified."
  }));

  for (const province of provinces) {
    const admin1Code = sourceCodeByOwner[province.country];
    const parentFeature = hierarchy.get(province.province_id);
    const parentNative = sourceAdmin1[admin1Code].filter((f) => norm(f.properties.shapeName) === norm(province.province_name));
    const rowsForProvince = rows.filter((row) => row.parent_id === province.province_id);
    province.pinned_geoBoundaries_adm1_same_normalized_name_candidates = parentNative.map((f) => ({
      shape_name: f.properties.shapeName, shape_id: f.properties.shapeID,
      geometry_type: f.geometry?.type || null
    }));
    province.scoped_point_supported_parent_names = [...new Set(rowsForProvince.flatMap((r) => r.adm1_source_representative_point_candidates))].sort();
    province.scoped_points_matching_expected_admin1 = rowsForProvince.filter((r) => r.adm1_source_point_agrees_with_atlas_parent_name).length;
    province.scoped_points_total = rowsForProvince.length;
    province.parent_review = parentNative.length === 1 && province.scoped_points_matching_expected_admin1 === rowsForProvince.length
      ? "Name and representative-point screen agree with the pinned ADM1 candidate; no complete parent-boundary overlay/current parent source crosswalk was performed."
      : "Parent meaning/current boundaries remain unresolved; do not repair from a name/representative-point screen alone.";
    province.atlas_parent_source_id = parentFeature?.metadata?.source_id || null;
    province.atlas_parent_source_name = parentFeature?.metadata?.source_name || null;
  }

  const counts = {};
  for (const code of Object.keys(sourceDefs)) {
    const assigned = rows.filter((r) => r.reference_owner === sourceDefs[code].name);
    const adminSubjects = assigned.filter((r) => r.subject_kind === "administrative source unit");
    const ecoSubjects = assigned.filter((r) => r.subject_kind === "ecoregion portion");
    const sourceUnits = [...new Set(assigned.map((r) => code + ":" + r.native_source_id))];
    counts[code] = {
      country: sourceDefs[code].name, pinned_geoBoundaries_adm2_feature_count: sourceRoster[code].length,
      assigned_subject_count: assigned.length, direct_administrative_subject_count: adminSubjects.length,
      ecoregion_portion_subject_count: ecoSubjects.length,
      unique_pinned_adm2_predecessor_count_represented: sourceUnits.length,
      exact_scope_is_partial: scope.area_scopes.find((a) => a.name === sourceDefs[code].name).partial,
      distinction: "Feature counts describe the retained source and issue subset; they are not an Atlas quota or evidence of national/current completeness."
    };
  }
  const used = new Set(rows.map((r) => sourceCodeByOwner[r.reference_owner] + ":" + r.native_source_id));
  const outsideRoster = {};
  for (const [code, features] of Object.entries(sourceRoster)) {
    outsideRoster[code] = features.filter((f) => !used.has(code + ":" + f.properties.shapeID)).map((f) => ({ native_source_id: f.properties.shapeID, source_name: f.properties.shapeName, note: "Not represented by a scoped direct unit or a scoped physical predecessor; this is explicit scope remainder, not a defect or transfer." }));
  }

  write("assessment.json", {
    version: 1, issue: ISSUE, built_from_main: BASELINE_COMMIT,
    issue_scope_sha256: sha(Buffer.from(JSON.stringify(scope))),
    current_world_index_path: "data/world-index.json", current_world_index_sha256: sha(fs.readFileSync(path.join(REPO, "data/world-index.json"))),
    publication_v5_release: release.release,
    macro_certificate_sha256: release.macro_certificate_sha256,
    source_member_count: rows.length, status_counts: rows.reduce((o, r) => (o[r.individual_status] = (o[r.individual_status] || 0) + 1, o), {}),
    country_source_inventory: counts, country_source_remainder: outsideRoster,
    rows
  });
  write("province-assessments.json", {
    version: 1, issue: ISSUE, province_count: provinces.length,
    assigned_province_members: provinces.reduce((n, p) => n + p.subject_count, 0), provinces
  });
  write("scale-screens.json", {
    version: 1,
    method: "Spherical area approximation of source GeoJSON exterior rings minus interior rings; candidate screening only. Parent ratios compare source ADM2 to normalized-name source ADM1. The representative point selects a parent candidate. This is not equal-area GIS overlay, complete edge coverage, or a geographic approval.",
    flags: rows.filter((row) => row.source_parent_repeated_tier_flag || row.source_scale_screen_flag).map((row) => ({
      subject_id: row.subject_id, name: row.name, country: row.reference_owner,
      source_name: row.source_name, source_role: row.publisher_canonical_role,
      source_area_km2_screen: row.native_source_area_km2_spherical_screen,
      source_adm1_area_km2_screen: row.source_adm1_area_km2_spherical_screen,
      area_ratio_screen: row.native_adm2_to_source_adm1_area_ratio_screen,
      source_parent_children_at_representative_point: row.source_parent_children_at_representative_point,
      source_geometry_equals_parent: row.source_predecessor_equals_source_adm1_geometry,
      flag: row.source_parent_repeated_tier_flag || row.source_scale_screen_flag,
      status: row.individual_status, recommendation: row.recommendation
    })),
    limits: [
      "Bamako source ADM2 and ADM1 geometry equality is exact in the retained pinned GeoJSON, but role/purpose requires current legal source review.",
      "Nouadhibou's source ADM2 is approximately 90.16% of the Dakhlet Nouadhibou ADM1 screen area and is a single-child parent candidate; do not infer a city fragment, a mistaken parent or a required merge from area ratio alone.",
      "Source administrative extents and point counts do not establish the boundaries of cities or settlements; no urban footprint or complete settlement source was inspected."
    ]
  });
  write("sources/register.json", sourceRegister);
  const baseline = { type: "FeatureCollection", name: "Exact issue 473 member features at the fresh main baseline", features: members };
  const baselineBytes = Buffer.from(JSON.stringify(baseline));
  const compressed = zlib.gzipSync(baselineBytes, { level: 9, mtime: 0 });
  fs.writeFileSync(path.join(ROOT, "baseline-members.geojson.gz"), compressed);
  write("baseline-receipt.json", {
    issue: ISSUE, baseline_commit: BASELINE_COMMIT, source_repo_path: "data/world-index.json",
    member_count: members.length, uncompressed_bytes: baselineBytes.length,
    uncompressed_sha256: sha(baselineBytes), compressed_path: "baseline-members.geojson.gz",
    compressed_bytes: compressed.length, compressed_sha256: sha(compressed),
    member_roster_sha256_lf_separated: sha(Buffer.from(assessedIds.join("\n") + "\n")),
    current_release: release.release,
    preservation: "Read-only copies of the exact assigned features; no project geography was modified."
  });
  console.log(JSON.stringify({ issue: ISSUE, subjects: rows.length, provinces: provinces.length, statuses: rows.reduce((o, r) => (o[r.individual_status] = (o[r.individual_status] || 0) + 1, o), {}), countries: counts, output_bytes: { assessment: fs.statSync(path.join(ROOT, "assessment.json")).size, baseline_gzip: compressed.length } }, null, 2));
}

main();

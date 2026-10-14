// Physical features and territorial ownership are independent (#528/#534).
// This interprets measured evidence; it changes neither locations nor overlays.
export function diagnoseMapCell({effectiveOwner, physicalEvidence = [], lineage, transitions = [], intendedLocations = []}) {
  if (!Number.isSafeInteger(effectiveOwner?.index) || effectiveOwner.index < 0)
    throw Error('Require the measured effective owner (zero means unassigned)');
  if (!lineage?.selected || !lineage.native ||
      !Number.isSafeInteger(lineage.selected.first_owner) || !Number.isSafeInteger(lineage.native.first_owner))
    throw Error('Require selected geometry and native-grid measurements');
  const supported = physicalEvidence.filter(e => e.covers === true && e.explicit_feature === true);
  const water = supported.filter(e => e.kind === 'water');
  const land = supported.filter(e => e.kind === 'land');
  const dry = land.filter(e => e.excludes_water === true);
  const losses = transitions.filter(t => t.joined === true && t.before === true && t.after === false);
  const candidates = [...new Map(intendedLocations.map(location => [location.id, location])).values()];
  const reasons = [], blockers = [];
  let kind = 'mixed-or-unknown';
  if (lineage.selected.first_owner !== lineage.native.first_owner || lineage.native.first_owner !== effectiveOwner.index) {
    kind = 'native-grid-selection-mismatch';
    blockers.push('The selected geometry, stored native grid and effective owner disagree.');
  } else if (losses.some(t => t.same_vintage === false)) {
    kind = 'source-vintage-disagreement';
    blockers.push('Joined territorial source vintages disagree on membership; the intended location needs reconciliation.');
  } else if (losses.some(t => t.same_vintage === true)) {
    kind = 'downstream-geometry-loss';
    reasons.push('The same joined source vintage covers this cell upstream and loses membership downstream.');
  }
  if (!effectiveOwner.index) {
    if (candidates.length !== 1) blockers.push(candidates.length ? 'More than one source-backed location covers this cell.' : 'No upstream source feature has been joined to a current location ID.');
    if (!water.length && !dry.length) blockers.push('Physical source coverage is missing for the proposed location addition.');
    if (lineage.selected.holes?.length) blockers.push('The selected polygon hole needs its own territorial/semantic explanation; water alone does not establish an ownership exclusion.');
  }
  if ([lineage.selected, ...(lineage.original ?? []), ...(lineage.consumed ?? [])].some(stage => stage.boundary_ties?.length) || supported.some(e => e.boundary_ambiguous))
    blockers.push('The cell center falls exactly on a measured source boundary.');
  if (effectiveOwner.index && candidates.length === 1 && candidates[0].id !== effectiveOwner.id)
    blockers.push('The source-backed location differs from the current owner.');
  const locationStatus = blockers.length ? 'unresolved' : effectiveOwner.index ? 'currently-assigned' : 'source-supported';
  if (water.length) reasons.push('An explicit physical water feature is supported at this source date; it does not determine location ownership.');
  if (water.length && dry.length) reasons.push('The physical land mask and water evidence disagree. Retain both sources and dates; this alone does not settle territorial membership.');
  if (!water.length && !dry.length) reasons.push(land.length ? 'Only coarse land context is available.' : 'Physical land/water remains unverified.');
  return {
    physical_status: water.length ? 'water-supported' : dry.length ? 'land-supported' : 'unknown',
    physical_source_disagreement: Boolean(water.length && dry.length),
    location_status: locationStatus,
    current_owner: {id: effectiveOwner.id, index: effectiveOwner.index, name: effectiveOwner.name ?? null},
    intended_location: locationStatus === 'source-supported' ? candidates[0] : null,
    candidate_locations: candidates, blockers, kind, reasons,
    next_action: locationStatus === 'source-supported' ? 'Prepare the exact source-supported native-cell assignment, preserving existing owners and separate river/lake evidence.' :
      locationStatus === 'currently-assigned' ? 'Report current ownership separately from physical features; no assignment change is established.' : 'Resolve the listed location evidence blockers independently of physical water status.',
    limits: ['Cell membership is numerical evidence, not source authority or a repair approval.',
      'Administrative coverage does not establish dry land; physical water does not imply owner zero or a permanent territorial exclusion.',
      'No geometry, ownership, release, overlay or click precedence is changed.']
  };
}

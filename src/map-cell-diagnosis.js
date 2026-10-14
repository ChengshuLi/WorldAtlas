// Read-only interpretation of measured cell evidence. Administrative membership
// and a polygon hole are deliberately not physical land/water observations.
export function diagnoseMapCell({effectiveOwner, physicalEvidence = [], lineage, transitions = [], intendedLocations = []}) {
  if (!Number.isSafeInteger(effectiveOwner?.index) || effectiveOwner.index < 0)
    throw Error('Require the measured effective owner (zero means unassigned)');
  if (!lineage?.selected || !lineage.native ||
      !Number.isSafeInteger(lineage.selected.first_owner) || !Number.isSafeInteger(lineage.native.first_owner))
    throw Error('Require selected geometry and native-grid measurements');
  const supported = physicalEvidence.filter(e => e.covers === true && e.explicit_feature === true);
  const water = supported.filter(e => e.kind === 'water');
  const land = supported.filter(e => e.kind === 'land');
  // Coarse shoreline polygons often include inland water. They cannot refute a
  // positive water observation, or establish that an unassigned cell is dry.
  const dry = land.filter(e => e.excludes_water === true);
  const losses = transitions.filter(t => t.joined === true && t.before === true && t.after === false);
  const reasons = [];
  let kind = 'mixed-or-unknown';
  if (lineage.selected.first_owner !== lineage.native.first_owner ||
      lineage.native.first_owner !== effectiveOwner.index) {
    kind = 'native-grid-selection-mismatch';
    reasons.push('The selected geometry, stored native grid and effective owner disagree.');
  } else if (water.length && dry.length) {
    kind = 'source-vintage-disagreement';
    reasons.push('Explicit water and water-excluded land evidence overlap this cell. Compare their dates and coverage.');
  } else if (!effectiveOwner.index && water.length) {
    kind = 'intentional-mapped-water';
    reasons.push('An explicit mapped water feature covers the cell; the selected geometry and native grid leave it unassigned.');
  } else if (losses.some(t => t.same_vintage === false)) {
    kind = 'source-vintage-disagreement';
    reasons.push('Joined source vintages disagree on cell membership; this does not isolate a simplification error.');
  } else if (losses.some(t => t.same_vintage === true)) {
    kind = 'downstream-geometry-loss';
    reasons.push('The same joined source vintage covers this cell upstream and loses membership downstream.');
  } else if (effectiveOwner.index) {
    reasons.push('The cell is assigned and agrees with selected geometry. Physical land/water remains a separate question.');
  } else if (lineage.selected.holes?.length) {
    reasons.push('The cell is inside an excluded polygon hole without explicit water evidence. The hole alone is not a water finding.');
  } else {
    reasons.push('Available evidence does not distinguish a source gap, vintage difference, or unmapped water.');
  }
  const candidates = [...new Map(intendedLocations.map(location => [location.id, location])).values()];
  const blockers = [];
  if (!water.length && !dry.length) blockers.push('A physical source resolving mapped water exclusions at this cell is missing.');
  if (water.length && dry.length) blockers.push('Physical sources disagree on water versus land; their dates and boundaries need reconciliation.');
  if (!effectiveOwner.index && !water.length && candidates.length !== 1) blockers.push(candidates.length ? 'More than one source-backed location covers this cell.' : 'No upstream source feature has been joined to a current location ID.');
  if (!effectiveOwner.index && !water.length && lineage.selected.holes?.length) blockers.push('The selected polygon hole needs a physical or semantic explanation before it can be filled.');
  if ([lineage.selected, ...(lineage.original ?? []), ...(lineage.consumed ?? [])].some(stage => stage.boundary_ties?.length) || supported.some(e => e.boundary_ambiguous)) blockers.push('The cell center falls exactly on a measured source boundary.');
  if (kind === 'native-grid-selection-mismatch' || kind === 'source-vintage-disagreement') blockers.push(...reasons);
  if (effectiveOwner.index && dry.length && candidates.length === 1 && candidates[0].id !== effectiveOwner.id) blockers.push('The source-backed location differs from the current owner.');
  const resolvedWater = water.length > 0 && !dry.length && !blockers.length;
  const supportedAssignment = !effectiveOwner.index && dry.length > 0 && !water.length && candidates.length === 1 && !blockers.length;
  return {decision: kind === 'native-grid-selection-mismatch' ? 'unresolved' : effectiveOwner.index ? 'currently-assigned' : resolvedWater ? 'water' : supportedAssignment ? 'land-with-location' : 'unresolved',
    current_owner: {id: effectiveOwner.id, index: effectiveOwner.index, name: effectiveOwner.name ?? null},
    intended_location: supportedAssignment ? candidates[0] : null,
    candidate_locations: candidates, blockers, kind, reasons, physical_support: water.length && dry.length ? 'conflicting' : water.length ? 'mapped-water' : dry.length ? 'mapped-dry-land' : land.length ? 'coarse-land-context' : 'unknown',
    next_action: supportedAssignment ? 'Prepare an additive native-cell repair for the intended location, preserving existing owners and explicit water exclusions.' : resolvedWater ? 'Preserve the mapped water exclusion.' : effectiveOwner.index && kind !== 'native-grid-selection-mismatch' ? 'Already assigned; current ownership is reported without claiming physical or source-owner correctness.' : 'Resolve the listed evidence blockers.',
    limits: ['Cell membership is numerical evidence, not source authority or a repair approval.',
      'Administrative coverage does not establish dry land; absent water features do not establish absence of water.',
      'No geometry, ownership, release, or UI is changed.']};
}

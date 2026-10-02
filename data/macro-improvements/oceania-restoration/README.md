# Oceanian omitted-land candidate (issue 501)

Recorded 2026-10-02, America/Los_Angeles. This package prepares **28 complete named
territories** against geographic release 3, preserving all 49,589 existing
location features and their source bytes. The resulting candidate has 49,617
locations and four added local parent groups. Region/subcontinent/continent IDs
are retained; regional interiors remain unapproved.

All 30 task candidates retain exact source geometry and representation outcomes
in `candidate-report.json.gz`. Kingman Reef and Gardner Pinnacles have no current
canonical cell centers and stay held. Their proposed identities are not added to
the candidate or registered; no neighboring water cell is assigned to them.
Palmerston and Manihiki belong to a separate correction task and are excluded.

`source-identity-plan.json.gz` retains the reviewed parent roles and exceptions;
`retained-identity-scan.json.gz` retains exhaustive current/archived footprints,
registry/name matches, published-version membership findings and their hashes.
`inputs.json` pins the immutable source package from the preceding source audit.
Original XML, gazetteer HTML and GSHHG comparison bytes remain at
`data/macro-improvements/macro-coverage-oceania/`. No network fetch is required.

The staged geometry is the exact closed OSM dry-land union for each named island,
atoll or compact Bounty archipelago. OSM ways/rings are source components, not
separate locations. Generated source wrappers carry explicit stable source
identities while retaining raw XML archive hashes and way IDs. OpenStreetMap
contributors receive attribution under ODbL 1.0; the source and derivative
database obligations remain applicable. Wikipedia text references retain their
CC BY-SA terms; linked media were not imported. GSHHG is a comparison dataset,
not the replacement coastline source. Modern evidence supports only 2026–2027.

No factual records are imported or transferred. Every newly assigned owner,
culture, religion, population, habitation, rank and environmental attribute is
unknown until separately supported. The McKean name match in Pennsylvania is an
explicit geographic homonym; its existing identity and land are retained.

The retained `PCN+00?` source footprint is Henderson. The report includes its
complete before-feature and a sourced proposal for the modern reference label
“Henderson Island”, with unchanged ID, footprint and history. **The proposal is
not applied by this pure-addition producer.** It does not relabel old historical
claims, assert ancient names or relocate that identity to actual Pitcairn Island.
The designated integrator must supply the separate retained-ID metadata receipt.

From a complete checkout with Node 24 and pinned Python preparation packages:

```sh
node scripts/prepare-oceania-land-restoration.mjs \
  --root=/absolute/path/to/WorldAtlas \
  --output=/absolute/path/to/fresh-candidate
node scripts/check-oceania-land-restoration.mjs \
  --before=/absolute/path/to/WorldAtlas/data \
  --stage=/absolute/path/to/fresh-candidate
node --test test/oceania-land-restoration.test.mjs
```

The producer accepts a hash-matched release-3 baseline, checks the original source
and archive bytes, repeats all cell-center outcomes, and uses the generic
source-backed creation validator. That validator checks exact geometry, WGS84
land area, current/competing overlaps and complete parent chains; the additional
archive checker rejects any reused archived land. Inputs are never mutated and
failed preparation removes only its own temporary output.

`creation-receipt.json.gz` and `candidate-hierarchy.json.gz` retain the successful
staging snapshots. `outputs.json` pins durable artifacts. Reproduction regenerates
raw source wrappers and a full generic `migration/index.json`; compressed snapshots
are evidence, not an installable replacement manifest. `validation.json` records
independent exhaustive preservation and hierarchy checks on the real candidate.

Publication remains under the designated integrator: authorized private registry
and claim preflight; retained-ID Henderson metadata receipt; combined ordered
geometry/metadata migration proof chain; evidence applicability; a new cached
canonical ownership grid and exhaustive representation/unique ownership checks;
member-derived macro envelopes and neighbor/source-gap routes; matching
static/hosted assets; hosting limits. Local scans do not prove live absence, and
positive cell-center screening does not claim the full global grid was rebuilt.
The regional research gate remains closed.

A read-only full release-4 preparation probe is retained in
`publication-order-probe.json`. It uses the installed repair geometry proof, the
new creation proof and all four metadata receipts from the published v3 release.
It initially failed **“Metadata original unit archive differs from actual before
identities”**: the identity reconciler processes geometry hierarchy snapshots
before all older metadata receipts. The latest pure-addition snapshot already
contains v3 identities, so those older before-archives cannot match. The chronological-proof integration fix was merged under issue 509 at
`51e9f84a30b22a3cc1d4ebf4f579f28f5ed531bb`. The unchanged real candidate then
prepared a valid release-4 manifest using the explicit pinned order: original
repair geometry, four retained v3 metadata receipts, then this creation proof.
`publication-order-validation.json` retains that successful result and sequence.
The original failed probe remains evidence. Do not discard old receipts or
silently repin them. Live static/hosted publication and the other stated gates
remain with the designated integrator; no live operation occurred.

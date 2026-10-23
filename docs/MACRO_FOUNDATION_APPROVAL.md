> Native Site 20 / geographic version 4 deployed on 2026-10-02 at 7:03:33 PM America/Los_Angeles; live content preservation and actual GitHub queue read-back are verified. [PR #519](https://github.com/ChengshuLi/WorldAtlas/pull/519) delivers the final publication/handoff record; verify its merge status and start from fresh main containing these receipts. The Site 19/version-3 paragraph below is the preceding verified milestone.

Current publication: **geographic release 5 / Site 21**, root-verified on 2026-10-03. The finite Uchalinsky reporting-convention decision, Kingman/Gardner dry-land additions, and complete sourced Cook/Chagos replacements are finished. All 49,625 locations are represented on the fixed grid; all 116 macro envelopes have no material overlap, parent-union mismatch or source-land loss. The published partition has six continents, 29 subcontinents and 81 regions. Exact release, source, grid, historical-preservation and browser proofs are in `data/validation/macro-publication-v5.json`. This supersedes the release-4 status below; earlier dated reports remain historical evidence.

The audit approves declared macro geography and routing, with no known unresolved named-route or adjacent-parent mismatch. It does not certify every offshore rock or worldwide shoreline, surveyed physical continental divides, or regional interiors. Source-coverage observations remain geography-research evidence, not proven missing territories. Uchalinsky follows the sourced Bashkortostan administrative reporting convention; Chagos dry-land footprints retain documented low-tide/shoreline uncertainty. Historical location-attribute imports remain gated until each complete regional branch is approved.


# Approved global macro reporting partition

The [macro-boundary follow-up](../data/macro-improvements/macro-boundary-followup/README.md) distinguishes the 49 incomplete finite-river measurements from demonstrated assignment errors: 48 do not intersect the inspected source river/canal and one does. All retain their approved reporting conventions; none becomes physically verified merely through this clarification. It also records the separate, repairable island/source/grid coverage limitations. The original publication receipt and uncertainty ledger remain unchanged.

Issue #33 approves the own-boundary conventions for all six continents, 29 subcontinents and 81 regions, excluding Antarctica. The four sourced continental decision sheets, original inspection ledgers and explicit migration receipts are retained. `data/macro-foundation/approved-boundary-decisions.json` records every current group, fulfilled correction and named-land route; `macro-certificate.json` pins the exact release, membership fingerprints and immutable envelope manifest.

The hierarchy remains constructed bottom up. Regions union their represented location land; subcontinents union regions; continents union subcontinents. Independent verification checks every source location's inclusion, asset hashes, exact membership, valid geometry, child containment and same-tier material overlap. The frozen envelopes remain independent audit constraints for subsequent interior edits.

These are sourced, fixed geographic reporting conventions, including explicit administrative reference edges where physical divides lack adequate evidence. They do not follow changing political ownership or imply those administrations existed historically. Original physical-precision uncertainties remain preserved; this is not surveyed watershed/crest approval. GEOS zero-area collapsed boundary segments are retained explicitly, not classified as land. Source-overlay ribbons are measured under a 1e-6-degree corridor (at most about 0.112 m); land conservation uses 1e-9 degrees. Input land is neither clipped nor reassigned to conceal those ribbons.

All named absent or partially represented island families have a fixed regional destination and an explicit coverage limitation. Missing shoreline/islet source coverage remains regional work; represented-land envelope approval does not assert complete world shoreline coverage. Adding missing land follows its sourced routing and a coordinated envelope/certificate publication, never an arbitrary cell reassignment.

`regional-handoffs.json.gz` covers every one of the 81 regions. Each future regional worker must audit its complete area/province/location branch, source suitability, granularity, coverage and grid representation. Approval here does not approve any regional interior, permit new location-attribute imports, or close worldwide semantic issue #7. Source-only research may continue.

The installed and natively deployed version-4 release contains 49,623 locations: all 49,589 predecessor IDs remain, six retained footprints have sourced corrections, and 34 named land territories are added. Original geometries, source inspections and historical claims remain archived. Ownership and environmental products reuse unchanged locations and recompute only the 40 changed footprints. The canonical grid is precompiled once for this geographic revision; navigation reuses it. The finalized backend and Site use release `geography:review:d7db5972b2370dd6109538e85011e05fd0396f093a09d30bf68cce371da98ecc`; live API and asset pins match the publication receipt; the refreshed issue pins match the same release; workers must retain those pins when claiming updated scopes.

Site 20 uses environment revision 4 and the unchanged custom owner-only audience. Native deployment `appgdep_6ac06250225c8191b3b2b66d20134146` succeeded at 2026-10-03T02:03:33.040989Z; source mirror commit is `1495a124377f2557cb6485bf2a0d969a6cb5db4f`. Live API/asset pins and all five preserved content collections match in `data/validation/macro-publication-v4.json`, including 396 attribute claims, 3,588 names and six media links. Actual GitHub read-back at 7:22:19 PM PDT verified 503 issues, including 273 exact packets covering all 49,623 locations once; canonical ready GitHub packets are authoritative. Proof: `data/reference-migrations/macro-improvements-v4/queue-checkpoint/actual-github-queue-readback.json.gz`. No regional interior is approved and no history-import gate is opened. Kingman/Gardner representation holds, partial Chagos coverage and the documented physical-boundary uncertainties remain open.

The preceding publication was verified in **Site 19 / geographic version 3** with its existing custom audience and environment revision 3. `data/validation/global-macro-publication.json` records exact native deployment IDs, source/release hashes, preserved claims and archive read-back proof. The complete regional inventory is `data/macro-foundation/regional-handoffs.json.gz`; the cooperative gate approves only the macro partition and retains an empty regional-certificate list. Certificates and projections preserve their creation-time publication checkpoint; the separate publication receipt is the completed live result.


## Literal current member-edge validation prerequisite

`projectCurrentMemberEdges` in `scripts/prepare-macro-review-projection.mjs`
extracts only current canonical identity and the literal presence/value of
`metadata.source_member_ids` from every part in the supplied exact world index.
It preserves absent versus null, malformed values, order and duplicates instead
of interpreting or repairing them. The `member_edges` descriptor binds every
indexed part's path, ordinary mode, bytes, Git blob identity and SHA-256.

`validateCurrentMemberEdges` compares those actual bytes with the monolithic
projection and all dashboard-declared compact shards. Complete owner IDs, exact
member-property presence/value, part bindings and literal compact/monolithic row
equality are required. `validateSemanticFollowup` invokes this check when the
current monolithic projection declares `member_edges`; legacy projections keep
their existing behavior. The producer is an explicit exported prerequisite, not
automatically called by the existing migration producer. No world data is
regenerated by this engineering change.

Passing this validation establishes metadata equality only. It does not enable
native negative-only admission, prove source-member absence for a legacy
projection, interpret malformed claims as absence, assign ownership, or recover
historical transformation ancestry. Introducing this descriptor in real current
data still requires a reviewed complete extraction, genuine validation and an
explicit accepted migration gate. That gate and the later native policy remain
separate work; an author-produced descriptor is not accepted authority.

The raw-byte extraction returns its locally decoded canonical features for the
current semantic/footprint check, avoiding a second parse of every current part.
Those transient features are removed from the small validation report. The API
never accepts supplied decoded features in place of the complete raw bytes.

The extractor also accepts an exact-order synchronous iterable of whole raw
parts. The filesystem validator uses this to read, hash and decode one canonical
part before loading the next, without retaining an aggregate raw-buffer array.
Missing, extra, reordered and duplicate parts still refuse; no partial report is
returned if iteration or a later part fails. Caller-owned arrays are not mutated.
Decoded geometry remains input-sized for the existing semantic and footprint
checks, and the footprint hash still creates its complete serialization. This
change makes no whole-world peak-memory or timing guarantee.

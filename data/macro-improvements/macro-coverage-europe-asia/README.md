# Europe and Asia named-land coverage evaluation

Engineering issue #43, under #40. Recorded 2 October 2026 (America/Los_Angeles). This evaluation checks **all 46** approved Europe/Asia named-land routes against independent shorelines and names. It installs no geography, changes no historical claims, and approves no regional interiors. The approved release-3 source and frozen envelope hashes are retained in `result.json`.

The evaluation is complete for its declared scope. **Complete archipelago coverage remains unapproved.** Broad source-window counts include neighboring unnamed land, old coastline offsets and genuinely omitted components; they are not a count of verified missing islands. Two mainland windows (Sinai and Peninsular Malaysia/Singapore) are explicitly partial search envelopes, not whole-peninsula certificates. Source components below 0.1 km² remain archived but are outside the quantified coverage summary.

## Evidence and checks

- `result.json`: exhaustive 46-route ledger, pins, status, coverage domain and future actions.
- `components.json`: 12,547 full-polygon comparisons (12,456 unique GSHHG IDs) against all 81 current regional envelopes. WGS84 geodesic integration measures entire polygons; named points only associate names with components.
- `gazetteer-source-inventory.json`: 105 original named article snapshots, source SHA-256, revision/attribution and geographic association context. Raw pages are archived.
- `geonames-source-inventory.json` and `geonames-routing-checks.json`: 25 independent GeoNames country snapshots and 66,564 original island/rock/atoll records. The original selected TSV bytes are archived. Source country codes are catalogue context, not ownership or region assignments; edit timestamps are not historical observation dates.
- `modern-candidate-review.json`: nine public OpenStreetMap XML queries, complete directed coastline chains and all referenced nodes/way versions; 26 dry coastal polygons at least 0.1 km² compared against every one of the 49,589 current location footprints.
- `water-mask-review.json`: all native GSHHG level-2/3/4 descendants examined for 11 selected components. None had nested water descendants. Modern closed water contours and complete water multipolygons are independently subtracted; Diego Garcia's documented lagoon-minus-inner-islands removes about 0.13 km².
- `territory-restoration-context.json`: existing candidate identities/source roles for Malta, Guernsey, Faroes, Cocos and Chagos. These are potential predecessor subjects, **not approved attachments**. The Eysturoyar fallback's many-island extent and narrow name specifically require source-role verification.
- `validation.json`: successful original-byte/hash, source lineage, polygon validity, complete closed-ring, query containment, coverage-threshold and candidate-identity checks.

GSHHG 2.3.7 is a 2017 WVS/WDBII composite, not a present-day survey. Its README explicitly documents GPS offsets and uncertain historical lake datum. Header areas use the magnitude exponent in `flag >> 26`; actual decisions use calculated WGS84 polygon areas. The exhaustive initial comparison covers outer ocean shoreline components, without subtracting lakes for every anonymous component, so these broad totals must not be treated as dry-land ownership denominators. The selected modern restoration candidates have separate water-mask checks. A 200-metre metric buffer is an offset diagnostic only, never replacement geometry.

## Staged findings

Modern closed-coastline comparison identifies **22 missing candidates** with less than 1% current location overlap, no current footprint within 0.001 degree, and the entire polygon inside its query envelope. Examples include Ro, Comino/Cominotto, Sark/Brecqhou/Jethou/Herm, Fugloy, Cocos members, and Salomon components. Candidate geometry and original XML retain source versions and licenses. This establishes mapped omission evidence; it does not itself determine a location's identity, local parent or historical territorial extent.

Three additional polygons intersect or lie near existing geography and require source-based restoration review rather than a new identity. The modern Cocos West Island polygon has about 13.5% current coverage; Diego Garcia's masked modern polygon about 37.8%. Whole-location purpose and source authority must be checked before replacing either footprint. Patmos's GSHHG majority classification flips under the offset diagnostic, so it is an outline/vintage case rather than a verified omitted main island.

Minamitorishima/Marcus Island is independently present in modern source geometry and names, but its macro route remains unassigned here. The approved Japan convention explicitly names the main/Ryukyu/Izu–Bonin/Daito association; Japanese sovereignty or GeoNames `JP` does not establish a geographic parent for this remote Pacific island. A coordinated Japan/Micronesia decision is required before installation.

Integration belongs to #45 and linked bounded remediation items. Preserve predecessor IDs, footprints and claims; require sourced territorial compatibility for attachment versus a new identity. Accepted footprint changes need complete parent crosswalks, a new release/grid representation and explicit revalidation of spatially derived ownership/environmental products. Anonymous source-window components must not be reassigned by nearest point or country owner. Parent #40 stays open until its actual geographic corrections and remaining coverage dependencies are resolved.

## Retained source bytes and reproducibility

`archive-manifest.json` lists four deterministic evidence archives, their byte hashes and exact member hashes. Restore them **into a scratch copy** of this evidence directory. The archives contain original named pages, original XML, original selected GeoNames source lines and normalized audit-only polygon fragments. The fourth archive retains the exact scoped input JSON, original upstream README notices and original source-collection manifest; restore all four archives before replaying the scripts. No audit blob is needed by the deployed map; the existing static build does not copy this directory.

The entire GSHHG binary distribution is independently pinned in `result.json` to SHA-256 `28600e8f7a08645aab43079326df6504212ec5ccb2b4bcf3b5f4f12ed60e82bc`, with original URL and binary digest. The reused source archive remains unchanged. Restore and verify that version before rerunning extraction. Raw country ZIP digests and the exact selected bytes are retained; live GeoNames/Wikipedia requests may return newer editions, so re-fetching creates a new evidence version rather than reproducing this one.

The Python files record the evaluation method. Run them only in a restored scratch directory with the pinned release-3 repository/source inputs; do not overwrite committed evidence or silently substitute a later geographic release. `verify.py` checks the restored evidence assets and original-byte manifests. The source evaluation's completion does not close worldwide semantic review, authorize imports or imply coastline precision beyond the explicitly recorded source dates/domain.

Licenses: GSHHG LGPLv3 (exact notices retained); Wikipedia article text CC BY-SA with original page/revision/author-history attribution; GeoNames CC BY4.0 (exact published README retained); OpenStreetMap contributors ODbL1.0 with original XML/version attribution. These terms remain attached to their respective source assets; no blanket replacement license is asserted.

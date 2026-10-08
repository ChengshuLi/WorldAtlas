# Madhya Pradesh interior review (#82)

This is a source-only packet for the exact 224 member IDs in [`issue-scope.json`](issue-scope.json). It does not approve the Central India region, the state’s full interiors, or historical attribute imports. No shared hierarchy, footprint, release, or production data was changed.

## Reproduction

The reproduction uses Python 3.12 and the repository-pinned `requirements.txt` dependencies. From the repository root, run:

```sh
python3 data/regional-review/regional-review-0968ad79c26518d2/reproduce.py
```

The script reads the original compressed source through `gzip` without writing a decoded source file. It records whole-file hashes for each input, runtime/library versions, the exact issue scope, current source rosters, source-to-Atlas membership, valid-geometry checks, topological shape comparison, WGS84 symmetric-difference areas, and sibling packet partition coverage in `assessments.json`.

Positive control: the shared `worldatlas-evidence-geometry-v1` helper returns a WGS84 area in the expected 12–13 billion m² range for a one-degree equatorial square. Negative control: it rejects a self-intersecting bow-tie polygon. No geometries are repaired. Re-running the script is deterministic.

## Reproduced results

- The 224 scoped Atlas IDs occur exactly once and map one-to-one by native ID and name to 224 retained geoBoundaries IND ADM3 features. All identify as 2018 “Sub-District” features. This verifies source identity and lineage, not modern legal status.
- The sibling packet scopes for #81, #82, and #83 partition all 422 Madhya Pradesh location IDs exactly: 54, 224, and 144. There are no duplicate or missing IDs in the area partition.
- The retained geoBoundaries GeoJSON has 6,822 features; its source metadata declares 6,836. The 14-feature difference is unresolved. The source metadata names Pathways Data Pvt. Ltd. and LG Directory, says “Sub-District,” represents 2018 boundaries, records a 2023-01-19 source update / 2023-12-12 build, and declares ODbL 1.0. This metadata and license are source assertions; they do not establish legal boundary truth or completeness.
- All 224 Atlas/source geometry pairs are valid. 212 pairs are topologically equal. Twelve differ; their source/Atlas areas and WGS84 symmetric-difference areas are retained individually in `assessments.json`. The largest difference is Seondha (Datia): about 671,004 m², 0.145% of the Atlas polygon area. The deltas are not adjudicated as correct or incorrect.
- Fourteen subjects are multipart polygons. Their names and component counts are in `assessments.json`; component multiplicity alone does not prove fragmentation or error.
- Current administrative rosters with exact URL, retrieval date, whole-page SHA-256, names, and counts are captured for 26 of 27 scoped province groups. Twenty-one are IGOD pages sourced from the Local Government Directory; five are district administration pages. Sheopur’s current complete tehsil roster remains unavailable in this packet. Raw webpage HTML is not redistributed because no page-specific reuse terms were identified; the URLs and hashes are explicit restoration instructions.
- Eleven groups have different Atlas/current roster counts: Agar (4/5), Burhanpur (4/5), Chhindwara (14/12), Dewas (9/10), Gwalior (8/10), Khandwa (6/9), Khargone (10/11), Raisen (10/12), Sagar (13/14), Sehore (9/10), and Ujjain (11/12). Other groups also have non-exact spellings or names. These are crosswalk leads, not evidence of a missing or misdrawn polygon.

## Individual assessment

`assessments.json` assigns one status and reason to every exact subject and to all 27 province groups:

- **Correction-needed: 11 locations.** Pandhurna and Sausar are still parented under Chhindwara, while Madhya Pradesh’s official 2023 order forms Pandhurna district from all Pandhurna and Sausar tehsil areas. Nine Hoshangabad-group subjects remain under the old district label after the official Hoshangabad-to-Narmadapuram rename effective 2022-02-07.
- **Insufficient evidence: 213 locations.** Their source identity and old administrative role are documented, but exact current legal boundary correspondence, district completeness, and local territorial continuity are not established.
- **Justified: 0.** No subject has a complete enough source-vintage and current-boundary chain for a positive geographic finding.

The Pandhurna order says that the new district comprises all 74 patwari halkas of Pandhurna tehsil and all 63 of Sausar tehsil, and that Chhindwara retains 12 tehsils. The official Pandhurna and Chhindwara district pages corroborate the new/current district descriptions. These support a parent-relationship correction proposal for the two named units, but the order does not include a boundary polygon annex and the Atlas source is from 2018; no footprint migration is approved here.

For Hoshangabad, the official district history establishes the rename. Current Narmadapuram pages disagree on the tehsil count: the tehsil page says eight but lists nine, while the election-office page refers to eight. The tehsil page names Narmadapuram Rural and Narmadapuram Urban, while this packet has separate Hoshangabad and Hoshangabad Nagar features. That suggests a possible name crosswalk but does not prove matching legal footprints. Keep all nine individual rows unresolved pending source-level crosswalk.

Earlier `data/geographic-decisions/asia.json` semantic assessments remain open. The identity/name checks here do not convert those assessments to approvals. Atlas administrative levels, labels, source-footprint shares, and stored overlaps were treated as claims to test, not as independent evidence.

## Follow-up handoffs

Two exact-scope dependent work items are recorded on GitHub: [#1085](https://github.com/ChengshuLi/WorldAtlas/issues/1085) owns the 111-subject source/geometry reconciliation (including the 12 divergent geometries, 11 count-difference district groups, and five Sheopur locations); [#1086](https://github.com/ChengshuLi/WorldAtlas/issues/1086) carries the 11-subject engineering handoff. Both are blocked on #82; #1086 also depends on #1085. They have versioned evidence-quality issue contracts and will require their own claims, fresh branches, reproduction, and independent review before implementation.

1. Engineering: coordinate the 2023 Pandhurna district formation with the affected Central India scope; assess adding the Pandhurna province identity and reparenting only the exact Pandhurna and Sausar IDs after current boundary correspondence is established. Separately assess renaming the existing Hoshangabad province label to Narmadapuram while preserving its stable identity and retaining all nine subjects under it unless a sourced tehsil crosswalk supports a further change. Do not edit geometry from this packet alone.
2. Geography/source work: resolve the twelve source/Atlas geometry differences, source current tehsil boundary material for roster-difference groups, and capture Sheopur’s complete current official roster. Use legal/current geometries only where source license and vintage are explicit; otherwise preserve precise restoration instructions and uncertainty.
3. Preserve the original 2018 source and all release/member pins. Any shared province/region change must be coordinated with the other Madhya Pradesh packets and the Central India integration; this packet does not authorize a unilateral core edit.

## Source custody

`source-inventory.json` records source roles, dates, hashes, license statements, and lawful retention/restoration status. The original geoBoundaries compressed source remains in `data/global-sources/` under its declared ODbL license. The official Pandhurna order was inspected as a two-page scanned PDF (SHA-256 `12cc5105b7482a8d06cec508b26bf393bc0af14d2145a414d8a3eba62130f397`, 862,340 bytes), but no reuse license was identified. It is therefore not redistributed here; restore it from the exact official PDF URL in the source inventory and verify its hash.

Scope snapshot refreshed 2026-10-06 from the live GitHub API after an exact issue-body hash mismatch. The current API body retains the same `worldatlas-work:v1` contract and identical embedded 224-ID workload scope; only the captured body hash/retrieval timestamp and this packet’s issue-scope file hash were refreshed.

# Engineering and source follow-up handoff

Date: 2026-10-05. Source/semantic evidence only. No shared hierarchy, geometry, ID, release, live data, or history changes are proposed in this PR.

## Actionable follow-ups

1. **Kosovo exact four district rows.** IDs: `gb:XKX:ADM1:2360587B11570115914955`, `gb:XKX:ADM1:2360587B15813948402025`, `gb:XKX:ADM1:2360587B89959345704230`, `gb:XKX:ADM1:2360587B9056373484571`. Source records are `District of Mitrovica`, `District of Peja`, `District of Prizren` and `District of Gjakova`; each repeats its one-child `framework:province` parent name. The retained pinned release package has seven district features, while its metadata says 48 municipalities. KAS reports 38 municipalities. Coordinate the seven-feature original source, metadata-count and license restoration with #999. After that is merged, a bounded follow-up must adjudicate these four exact Atlas identities and parents against the exact law annex/current roster. Preserve IDs and neutral status language; do not relabel ADM1 as municipalities.
2. **Mount Athos.** ID `gb:GRC:ADM3:53547021B80449020436996`; parent `framework:province:agion-oros:d7b00e3c954f`. The source class `Municipality` conflicts with constitutional Article 105's self-governed Aghion Oros region description. A bounded role/identity decision is needed before changes. Do not infer the precise polygon or correct name from the statutory text alone.
3. **Three Greek fallback parent nodes.** IDs `framework:province:poros:dc2c201d378c`, `framework:province:ydra:e88d77299c93`, `framework:province:elafonisos:7eb34f1f2d9b`; child IDs are in `assessment.csv`. Each same-name parent has one child and no source parent shapeID. The baseline records incompatible fallback shares against Attikis/Peloponnisoy (Poros 37.06%/3.21%, Ydra 25.35%, Elafonisos 46.85%). Obtain a licensed official regional/municipal boundary source, determine the legally/geographically correct grouping, and preserve child IDs. Ratios are not proposals for the winning parent.
4. **Greek 2010-to-current source reconciliation.** Exact #421 GRC workload is 226 old source locations. The 2010 source has 326 features; YPES reports 332 municipalities currently and documented 2019 splits of five prior municipalities into 12. Restore the authoritative current municipality register and lawful boundary archive, map each scoped identity by exact source code/legal history, and distinguish the numeric count difference from individual omissions. Do not use ELSTAT census geometry as legal boundary proof. Coordinate the shared national source question with batch #420 and do not overwrite #71/#819 evidence.
5. **Attikis and islands/cities.** Attikis is an exact 64-child workload group. The pinned parent record flags 13 specific children below 80% source-footprint retention; assess marine clipping versus boundary/source defects from official source geometry. Audit island and city-fragment completeness using an independent official gazetteer/boundary layer. 35/227 2010 Greek source features have no same-layer land edge in this diagnostic; no-edge results cannot establish omitted islands. Oraiokastro's two-feature aggregation must retain both source IDs.

## Dated child issue handoffs (2026-10-05)

- [#1006](https://github.com/ChengshuLi/WorldAtlas/issues/1006) is blocked pending #420 and #421. It owns exactly 306 Greek Atlas location IDs across those two packets (including the two-native-feature Oraiokastro multipart identity) for a current lawful municipality roster and per-ID 2010-to-current legal/code crosswalk. It excludes the 19 different source identities still owned by #819 and does not claim all 332 present-day units are enumerated.
- [#1007](https://github.com/ChengshuLi/WorldAtlas/issues/1007) is blocked pending #421. It owns exactly the Mount Anthos/Aghion Oros, Poros, Ydra and Elafonisos location rows and their referenced parent nodes for sourced role/parent adjudication; no IDs, hierarchy or footprints are changed here.
- [#1008](https://github.com/ChengshuLi/WorldAtlas/issues/1008) is blocked pending #421 and the shared source lineage/count/license work in #999. It owns exactly the four batch 6 Kosovo district IDs and their same-name parent references; it does not repeat #999's seven-feature archive restoration.

Each child has a distinct evidence directory, exact subject list and immutable issue-contract pins. All three were created with `status:blocked` because their declared evidence dependencies remain open. Search also found duplicate #1000 closed in favor of canonical #999; no duplicate Kosovo archive task was created.

## Invariants for implementers

- Keep issue #421's frozen outer-region geometry, member set, area partitions and all source vintages unchanged.
- A later PR must state exact affected subjects and previous/source IDs, not repin or silently transfer any location fact.
- The regional integration owner combines child evidence and makes whole-parent/area decisions. This packet makes no territorial endorsement.
- Use source evidence only; no production import, deployment, certificate, publication, history migration or region approval is authorized.

## Related work

- [#999](https://github.com/ChengshuLi/WorldAtlas/issues/999): shared seven-feature Kosovo source restoration / metadata and license inquiry; its current exact Atlas roster is the other three features.
- [#819](https://github.com/ChengshuLi/WorldAtlas/issues/819): blocked 19-subject Greek census crosswalk from a different ancestor packet. It is a useful shared-vintage lead but is not the #421 Greek roster and ELSTAT layers remain statistical only.
- [#420](https://github.com/ChengshuLi/WorldAtlas/issues/420): concurrent adjacent Southeast Europe packet; coordinate any national Greece source work before issue creation so the shared 326-to-332 reconciliation is not split into conflicting source/restoration jobs.

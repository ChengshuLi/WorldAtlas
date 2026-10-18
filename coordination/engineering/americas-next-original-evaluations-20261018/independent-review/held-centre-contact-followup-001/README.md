# Honduras/Nicaragua held-centre contact follow-up

Supplemental evidence for the existing original repair evaluations: Honduras issue #2462 and Nicaragua issue #2463. This adds a focused centre-contact read for four already-held original land keys. It does not add a qualification or acceptance claim.

| Country / owner | Original key `(x,y)` | Native centre `(lon,lat)` | Complete source feature | Embedded derived base | Other recorded contact |
| --- | --- | --- | --- | --- | --- |
| Honduras / Macuelizo | `(66489,119783)` | `(-88.69822936612681,15.329951489035457)` | interior | outside | Inline archive-only Nueva Frontera negative: interior; named Guatemala ADM1 ordinal 9 and ADM2 ordinal 124: outside. |
| Nicaragua / Murra | `(68584,120892)` | `(-85.82142611932898,13.856273705086496)` | interior | outside | HND ADM1 El Paraíso: interior; HND ADM2 Trojes: outside. |
| Nicaragua / San Juan del Sur | `(68704,122918)` | `(-85.65664502643364,11.140427323633512)` | interior | outside | CRI ADM1 Guanacaste: interior; CRI ADM2 La Cruz: outside. |
| Nicaragua / El Castillo | `(69687,123084)` | `(-84.30681324046597,10.916690037036531)` | interior | outside | CRI ADM1 Alajuela (source ID `gb:CRI:ADM1:80129987B16009817839121`, ordinal 2): interior; ADM1 Heredia (source ID `gb:CRI:ADM1:80129987B30917059240714`, ordinal 0), ADM2 Sarapiquí, San Carlos and Los Chiles: outside. |

The four source IDs and original class/contacts remain in `held-row-exception-packet.json`; the exact native rule results and geometry hashes are in `centre-contact-results.json`. Source features are linked to the original corpus payloads by repository path, source commit, Git blob OID, compressed SHA-256 and decoded SHA-256. The inputs also cite the exact country source-evidence files, native patches, native helper and latitude-table pins.

## Complete original-scope partition

The original requested scopes are fully represented by the actual supported-pair authority products plus the documented original exception rows:

| Country | Original requested | Actual native-qualified | Preserved documented exceptions | Split |
| --- | ---: | ---: | ---: | --- |
| Honduras | 6,633 (6,590 land + 43 inland water) | 6,632 (6,589 land + 43 inland water) | 1 | qualified product + exception |
| Nicaragua | 2,884 land | 2,881 | 3 | qualified product + exceptions |
| Total | 9,517 | 9,513 | 4 | qualified products + exceptions |

The actual constructor products and operating summaries are retained at `coordination/engineering/americas-next-original-evaluations-20261018/{hnd,nic}/qualified-authority-001/constructor-result.json` and `derived-operating-summary.json` (tree `07c74ff101d4ab5e679255ed85c402356aa54a42`). The four exception rows retain their original `territorial_exclusion_cells` disposition. The focused contact read does not revise exception membership or claim a causal operand. The 9,513 qualified cells were subsequently accepted in PR #2469 (merge commit `75861b9784f75b7894bfc51fa0419f40f966157d`) and are present in current tree `07c74ff101d4ab5e679255ed85c402356aa54a42`; this supplemental PR claims no additional repair credit.

The earlier comparison against selected baseline commit `252f2aa1e6309b6990985dec73611d6df0e11c70` (tree `c1df1bb415be741b182eccbdc4f23142d642e624`, 6,203,110 native cells) is retained as dated historical provenance only. At that time, issues #2462 and #2463 recorded zero coordinate and owner intersections; that pre-acceptance comparison does not establish the current intersection.

The current selected-patch intersection was independently reconciled against the actual current patch in tree `07c74ff101d4ab5e679255ed85c402356aa54a42`: HND has 6,633 original cells = 6,632 accepted cells plus 1 held exception; NIC has 2,884 = 2,881 accepted plus 3 held exceptions. The accepted counts match the native-qualified products, and the audit found no wrong-owner overlap. The accepted cells come from PR #2469, merge commit `75861b9784f75b7894bfc51fa0419f40f966157d`. This is an audit of the current patch, not an inference from the older `252f2aa` comparison. The independent current-patch partition review is recorded at [PR #2494 review 5561932870](https://github.com/ChengshuLi/WorldAtlas/pull/2494#pullrequestreview-5561932870). The reviewer can append the exact input pins and key hashes to that public review; no private receipt is represented here as a repository artifact.

The original authority diagnostic labels all four rows `territorial_exclusion_cells` but does not name a causal operand. The follow-up reports contact facts only. In each case the pinned complete source feature contains the centre while its embedded derived `base_geometry` does not; that representational difference requires review and does not establish which geometry should control. All four rows remain unresolved; this packet adds no repair or accepted cells beyond the 9,513 already accepted in PR #2469, assigns no sovereignty, and does not clear the holds. Existing source attribution, license, CRS, vintage, and whole-source limits remain governed by the country evidence packages.

The scanner was not rerun for this publication. The files are path-sanitized copies of the retained result and packet; scientific values, keys, source IDs, counts, relations, and geometry hashes are preserved. A sanitized, path-portable reproduction adapter is included as `held-row-diagnostic-repro.mjs` (SHA-256 `0222a8cced63e0ea2ac02cea8acf48eee6329750ddc7d5742bfc886e6a027d20`). It is a reconstruction from the retained task-local `diagnose.mjs` (SHA-256 `9d0c4c603da9b59f17b75733853be95f9993081b6a3a2a4161c838d29bdc64a2`), not the original executed file or an invocation receipt. It consumes the four literal original row/class/contact joins retained in this packet; it does not regenerate their extraction from the original interval blocks. Its command template and exact fixture layout are documented in the packet. The original shell/environment invocation was not retained. Independent review and normal downstream acceptance remain pending.

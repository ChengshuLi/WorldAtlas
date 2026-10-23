# Exact Kiribati source-relative native repair

Issue #2257 evaluates only frozen `gb-KIR-ADM1--repair-evaluation`: **2,836 original land cells / 1,000 segments**, owners 26614–26616, source indices 41032–41034, blocks 31/32. The separate 6,216-cell physical companion is excluded.

## Current proposed result

`diagnostic-003` screens all 2,836 original cells. `native-002` qualifies **2,552**: Line 669, Gilbert 1,787, western source remainder 96. **284 identity holds remain**: four eastern cells and 280 disconnected western cells. Offline qualification requires independent exact-head review and selected-output verification before integration. Issue #2257 stays open.

The original 2,832-cell proposal was narrowed after independent review found that western location alone does not establish target membership. `scope-002/source-component-disposition.json` retains every original source component, exact positive-area component joins, per-component candidate totals, and every held interval. Only original Phoenix component 2 → current remainder part 1 (2 cells) and component 4 → part 2 (94 cells) are admitted. Components 3, 5 and 7–11 have no current polygon intersection and contribute 280 held cells. Component 6 has zero candidates and remains unresolved and wholly excluded. Source component 1 contributes the four eastern holds:

- [133102,6032,6033]
- [133102,6041,6042]
- [133170,6102,6103]
- [133171,6100,6101]

Every hold is owner 26615/source index 41033. The original 380-cell remainder denominator is preserved as 96 proposed + 284 held. Exact held intervals and next evidence needs are in `scope-002`; absence of eastern conflict does not qualify western cells.

## Original source and limits

The complete original simplified geoBoundaries KIR ADM1 source at revision 9469f09 is 73,286 decoded bytes, SHA256 a2e55d40d5a45738a1927b1c3c4334c9bae73466cca2f96c7f7a0aa440ed8f81: Gilbert 29 components, source-named Phoenix 11, Line 5. All 45 components remain source competitors. Catalogue represented-year 2017 and OSM/Wambacher ODbL 1.0 provenance are retained. This is distinct from #611's 805,741-byte full-resolution source.

The retained generic western name and metadata provide negative western-domain intent; they do not authorize the disconnected components. Whole unmatched original polygons, including the zero-candidate component, are territorial exclusions in `source-003`, without clipping or altering the source. Exact component intersection supports bounded source-relative restoration, not named-island mapping, legal council jurisdiction, complete current coastline, sovereign attribution, historical claim or reconstructed lineage. All current geometries, names, identities and parents remain unchanged.

`source-review` records original native-centre membership for all 45 components and zero exact boundary ties. All original/current geometries inspected are valid under Shapely 2.1.2 / GEOS 3.13.1. `context-002` preserves MCIA/NSO statistical and council context and prior #611/#526 evidence. Those pages do not authorize polygons; warrant boundaries were not adjudicated. #611/#526 retain their full limitations. Further held-cell assignment needs affirmative exact component-to-current-target evidence or separately coordinated identity correction.

## Executed checks

- Stock original interval extractor reproduced 2,836 cells / 1,000 segments from queue SHA256 78007430b6f9faedb188ef0619b7ff0a7a2cc7fff2ec9f1c41ee69936ec4ebd8.
- Unchanged stock `physical-001` authenticates complete GSHHG native member and metadata and all three original target geometries. Gilbert/Line have no reported physical issues. Whole Phoenix missing/extra reconstruction witnesses remain; the native qualifier checks no contact with admitted centres.
- Fresh stock `source-003`, full `diagnostic-003` (2,552 supported / 284 held) and original `native-002` authority. A real full-cohort native-authority adverse attempt fails closed with no authority output.
- `verification-002` checks all 2,836 cells against actual accepted base native rows (three whole parts, 780 rows) and cumulative additive patch: both overlaps zero. Exact supported-plus-held union equals the original scope.
- `composition-002` preserves all 892 prior ledger rows and 147 authorities and adds three rows / one authority: 294,376 + 2,552 = **296,928** native cells. All 284 Kiribati and 1,203 Vanuatu holds remain unassigned.

Current outputs are `source-003`, `diagnostic-003`, `native-002`, `scope-002`, `composition-002`, `context-002`, `verification-002` and `ownership-selection-v3.json`. Earlier source/diagnostic/native/composition/context/verification versions and v2 sidecar are superseded immutable proposal evidence, **not delivery authority**. Complete original source/physical operands remain unchanged and reusable. Original constructors and commit pins are never silently repinned.

Normal root-controlled queue verification of actual selected geography and emitted picker/sampler smoke remains required. No regional certificate, historical import, provider operation, deployment, production publication or legal correction is performed.

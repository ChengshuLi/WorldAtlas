# North Macedonia 84-to-80 municipality roster review

Review date: 2026-10-05. Issue #995 is source-only research for the exact 84 `gb:MKD:ADM2` Atlas IDs scoped there. This packet does not alter geography, IDs, hierarchy, source catalog, release pins or publication data. It does not approve a regional branch or historical import.

## Finding

The source’s 84 shapes represent a mixed roster that is not a valid current 80-municipality layer. The State Statistical Office (SSO) documented 84 municipalities in NTES 2007. Following the 2013 territorial organization, the SSO’s 2014 NTES amendment records Drugovo, Vraneshtitsa, Zajas and Oslomej joining Kichevo. SSO’s 2017 and 2019 materials describe 80 administrative municipalities; NTES 2019 also has 8 level-3 statistical regions and 1,792 level-5 settlements.

The retained 2016 HDX/RIMWGE ADM4 shapefile has 84 named polygon records and the geoBoundaries source contains the same 84 geometries (ellipsoidal symmetric-difference fraction below `1e-8` for each pair under the declared calculation). Five source records—Vraneshtitsa, Drugovo, Zajas, Kichevo and Oslomej—spatially map to the current SSO/AKN Kichevo code `MK00307`: four former units plus the old Kichevo polygon. The other 79 source records each map by their dominant spatial overlap and source name to a distinct current NTES municipality code. Collectively, the 84 rows reach all 80 current municipality codes exactly once as targets, with five source polygons contributing to Kichevo.

This is an identity/crosswalk finding, not a claim that all 84 polygon borders are legally current. The source metadata claims a 2016 representative year, while its underlying roster is the older 84-unit arrangement and its source lineage names EuroGlobalMap v8.0 processed in October 2015. geoBoundaries’ 2023 source-update/build timestamps describe repository ingestion/build activity, not the legal boundary epoch. The precise effective date of the source geometry remains unresolved.

## Reproduction and geometry comparison

`reproduce.py` reads the exact source GeoJSON from the immutable #422 baseline and the retained CC-BY HDX/RIMWGE source archive. It verifies both hashes and compares all 84 source shapefile geometries to geoBoundaries. It then restores the current official AKN layer in memory by the exact query/hash in [SOURCES.md](SOURCES.md), and compares it with the official 2019 NTES roster transcription. Area fractions use the repository’s shared WGS84 straight-source-edge ellipsoidal helper. It outputs every subject row, source shape ID/name, existing Atlas parent ID, current municipality code/name, source-code collisions, dominant source-area overlap and target coverage in `crosswalk-results.json`.

The AKN layer query observed 82 polygon records, of which 80 had unique municipality codes; two named features, `OHRIDSKO EZERO` and `EZERO SPILJE`, have no municipality code and are not municipalities. All 80 unique AKN codes match the official NTES 2019 municipality codes after normalizing two Cyrillic `МК` prefixes. AKN’s service path contains “2022,” but its layer metadata supplies no per-feature vintage or reuse license. Its response geometry is therefore a provisional official comparator, not a cleared source for redistribution or legal certification.

The area screen uses longitude/latitude inputs (EPSG:4326, with HDX source ETRS89/EPSG:4258 transformed with longitude-first axis order), Shapely polygon intersections, and the shared WGS84 ellipsoidal area integral. For 79 direct matches, the median fraction of a source polygon inside its dominant current municipality is 99.30%; the minimum is 94.31% (Chair). The union of the five Kichevo-related source shapes covers 99.68% of the AKN Kichevo polygon. Across current targets, the median target-area coverage by the source union is effectively 100%, but two cases are substantial unresolved outliers: Resen (`MK00509`) is 74.30% covered and Dojran (`MK00406`) is 82.77% covered. Water/shoreline treatment, generalization, a source boundary change or another epoch difference could explain these residuals; the available sources do not identify the cause. No source names are remapped from overlap alone, and no boundary is certified.

Geometry validity and these area ratios are only reproducibility/diagnostic outputs. They do not establish legal edges, enclaves/islands, completeness, or licensing. AKN bytes are not retained because its license is unknown; exact observed response hashes and restoration queries are in [SOURCES.md](SOURCES.md).

## Source-code and identity risk

The HDX `SHN4` attribute has only 71 unique values for 84 polygons. `MK00307` repeats across the five Kichevo-related polygons above; `MK00809` repeats across all ten Skopje city municipalities. SSO’s 2019 NTES roster instead gives ten distinct municipality codes for Aerodrom, Butel, Gazi Baba, Gjorche Petrov, Karposh, Kisela Voda, Saraj, Centar, Chair and Shuto Orizari. Therefore a join keyed only on source `SHN4` would conflate distinct Atlas subjects in both Kichevo and Skopje. The new crosswalk uses exact source names, SSO current roster codes, current AKN feature codes and geometry correspondence while preserving all 84 Atlas IDs.

The retained shapefile’s native `Name4_L` labels exactly match the SSO 2019 native-script label for 76 of the 79 direct one-to-one matches. Three differences are recorded verbatim in `crosswalk-results.json`: Debartsa/Дебарца versus Debarca/Дебрца (`MK00304`), Mavrovo and Rostusha/Маврово и Ростуша versus Mavrovo i Rostuse/Маврово и Ростуше (`MK00607`), and the source label Гази Ба versus the roster’s Гази Баба for Gazi Baba (`MK00804`). The first two are plausible transliteration/spelling variants, but these sources alone do not establish official equivalence; the Gazi Baba label may be incomplete, though its source English name, spatial match and code align. Treat all three as label-review handoffs; do not infer a boundary or identity correction from the labels alone.

`crosswalk-results.json` contains a row for each exact scoped subject. Four rows are marked `former_municipality_merged_into_current_kichevo`; the old Kichevo row is `historic_kichevo_component_of_current_municipality`; the other 79 are `current_roster_unit_spatially_corresponds`. The output preserves each source shape ID and the original Atlas parent ID. It does not transfer historical data or replace any IDs.

## Eight parent relationships and granularity

All 84 existing Atlas parent assignments name the same eight NTES level-3 statistical regions found by the 2019 roster and source shapes. Each matched parent is a statistical region, which SSO describes as a non-administrative grouping of administrative municipalities—not a provincial government unit:

| Atlas parent | NTES code | Official statistical-region name |
| --- | --- | --- |
| `framework:province:east:93d71c19983e` | `MK002` | East |
| `framework:province:northeast:ae810c24404c` | `MK007` | Northeast |
| `framework:province:pelagonia:4091f04e8c10` | `MK005` | Pelagonia |
| `framework:province:polog:76d403f17558` | `MK006` | Polog |
| `framework:province:skopje:d4d0d12ba0f8` | `MK008` | Skopje |
| `framework:province:southeast:133e6267a43b` | `MK004` | Southeast |
| `framework:province:southwest:683e6a222125` | `MK003` | Southwest |
| `framework:province:vardar:178ce5206540` | `MK001` | Vardar |

The neighboring NTES levels are explicit: non-administrative statistical regions (level 3), administrative municipalities (level 4), then settlements (level 5). The 2019 SSO material notes that portions of the ten Skopje municipalities that form Skopje as a settlement appear as separate level-5 units. That does not make those ten source polygons one level-4 municipality.

## Engineering handoffs (no shared edits in this issue)

1. Do not treat the claimed 2016 layer as a current legal 80-municipality source. Keep the 84 existing IDs and source evidence; if a current boundary update is proposed, first restore a licensed, dated official 80-unit geometry and reconcile Resen/Dojran and all other boundary differences.
2. Do not join `SHN4` as a unique ID. Preserve the 84 Atlas IDs and use a reviewed per-feature crosswalk; specifically retain the five Kichevo source polygons and distinguish all ten Skopje municipality features. Review the three native-label differences before using source labels as canonical display names.
3. Consider describing the eight parent units as statistical regions in the hierarchy/source metadata while retaining their existing IDs and memberships. Any shared hierarchy/catalog change belongs to a separately scoped engineering task and review.
4. Before redistributing AKN geometry, obtain explicit reuse terms and an immutable boundary vintage or agency confirmation. Its current service response is only a restoration-only comparator in this packet.
5. The SSO classification files are restoration-only here because their download page did not state full-file reuse terms. Preserve the scoped roster facts with citations; do not assume that availability on the SSO site grants bulk redistribution rights.

## Outcome and limits

The scoped research is complete: all 84 IDs, their source polygons, current roster links, source/parent associations, lineage, license limits and exact remaining geometry questions are recorded. The four-to-one Kichevo roster change and source-code collisions are supported; all 80 target codes are accounted for. The 2016 geometry’s exact legal epoch, AKN layer terms/vintage, and Resen/Dojran residual causes remain unresolved. No geography or parent tier is approved, and no source import is authorized.

For exact evidence hashes, retrieval dates, license limits and original-source restoration steps see [SOURCES.md](SOURCES.md). For exact per-subject findings see [`crosswalk-results.json`](crosswalk-results.json).

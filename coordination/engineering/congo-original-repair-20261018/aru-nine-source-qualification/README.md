# Aru nine-key source qualification attempt

**Status: substantive source evidence and stock diagnostic completed; all nine keys remain pending and held.** No repair, ownership change, hold removal, package completion, or accepted credit is claimed. This is a bounded slice of original `gb-COD-ADM2--repair-evaluation`, not a new denominator.

## Exact original keys and bindings

The nine original owner-14440 land keys are:

- `[14440,128782,153513]`
- `[14440,129086,153529]`
- `[14440,129091,153527]`
- `[14440,129093,153526]`
- `[14440,129096,153525]`
- `[14440,129098,153524]`
- `[14440,129099,153524]`
- `[14440,129101,153523]`
- `[14440,129103,153522]`

All nine are physical-support true and inland-water-support false in the retained original mask join. The original target is `gb:COD:ADM2:63176286B14719092717616` (Aru), recovered from the 50-target source-stage input at commit `7839ae9de7d57c732050df05e7f6d5c9b42afd88`. The exact whole-target physical receipt is pinned at `coordination/engineering/congo-original-repair-20261018/physical-001/whole-target-support.json`, 2,264,808 bytes, Git blob `272f696249d4b495eee03cb164fd1da9331ccb41`, SHA-256 `8a926e4fa97f70f814c9cfd5d2c92792798669254de0d072761518bf91105a75`.

The prepared source-evidence input binds the original COD feature, all nine exact coverage cells, the retained physical receipt and all 20 registered negative families. Stock source-evidence preparation retained 14 conservative target-level exclusion candidates and 1,365 disjoint source IDs. These are source disagreement operands, not per-key legal findings or authority to remove a source. An independent reviewer checked exact key/target/physical coverage and confirmed no applicability overclaim.

## Uganda source comparison

The original complete-family center overlay places all nine centers inside registered 2006 geoBoundaries UGA ADM2 features: eight in Vurra (`47994165B92141857832480`) and one in Maracha (`47994165B51818816351694`). The retained UBOS 2006 county archive is 8,325,415 bytes, SHA-256 `9857cf0088b578beccea29c467f9e1a1224b6341ebe944320c975cb9ca984921`; it was already present at `/tmp/ubos-uganda-county-2006-sv534fc7879.zip`. No archive was downloaded for this work.

Using the archive's embedded custom WGS84 UTM 36N `.prj`, the independent center comparison places only `[14440,129086,153529]` inside UBOS Vurra; the other eight centers fall outside all 164 UBOS county polygons. The same-name polygons overlap substantially but are not identical: Vurra intersection 664.026 of 767.334 km²; Maracha intersection 377.886 of 451.898 km². The archive's ISO/ESRI CRS metadata conflict remains, and this is a center-only representation comparison—not whole-cell qualification or territorial applicability.

The registered geoBoundaries metadata identifies the 2006 UGA ADM2 source broadly as “geoBoundaries, Wikimedia Commons” and provides only a generic `commons.wikimedia.org/wiki/File` source field, not a feature-level source file or direct UBOS crosswalk. A targeted public Commons lookup surfaced 2017 Arua and Maracha locator maps derived from OpenStreetMap and other locator-map sources; those maps do not identify the source of the pinned 2006 boundary geometries. See [Arua District locator map](https://commons.wikimedia.org/wiki/File:Arua_District_in_Uganda.svg) and [Maracha District locator map](https://commons.wikimedia.org/wiki/File:Maracha_District_in_Uganda.svg). This search does not prove that no further source record exists.

## Stock qualification result

The stock `prepare-delivery-handoff.mjs source-evidence` route completed using Node 24.19.0 and the bundled Git 2.53.0 with `GIT_NO_LAZY_FETCH=1` and `GIT_NO_REPLACE_OBJECTS=1`. Its config SHA-256 is `c5f1e1c3e1f4042bbde7e066ba94267e8816acf86731cfd52891efea0ff7d860`. Outputs:

- `source-evidence-generated/source-evidence.json`: 35,437 bytes, SHA-256 `6e4b8c67d0ffcfc12b778740d0a60e3fb30339c5c766d117ca1234e6fd656793`.
- `source-evidence-generated/territorial-exclusion-provenance.json`: 68,852 bytes, SHA-256 `d83889360f9ba9577d9f5412683f8fb361875bcd75073190195b08b9e585ddc9`.

The exact patch and prepared source-evidence body were retained in a local evidence-only commit `784f68d049437adf7b6ae69715827bab1fe2e4e7`, ref `refs/codex/research/aru-nine-stock-inputs`. This synthetic root commit is only an immutable local input container; it does not represent a public branch, accepted selection, or science decision. The full `source-evidence.json` embeds original COD target geometry and remains local; it is intentionally excluded from public packet changes. The retained UBOS archive and raw UGA/UBOS geometries were not added or redistributed.

The stock native diagnostic ran once against those exact inputs. It requested 9 cells, supported 0 and held all 9 as `territorial_exclusion_cells`; first failure `unique-source-target-coverage` at owner 14440, y=128782, x=[153513,153514). Runtime 217.586 seconds. Diagnostic output is 3,723 bytes, SHA-256 `5a4dbfdd104822648de88ac6ad70d2d63334e31106109c12ad0b5813dc38335f`; its preparation record binds config SHA-256 `b7362ce58bc566ea7aa7e2de0464cdad608afc047f9a4e42c6977adadbf9b544`. This is screening evidence only: no physical producer, owner observation, source applicability decision, whole-cell qualification, repair, or acceptance.

## Bounded disposition proposed

The reviewer found no mismatch in the source-evidence or diagnostic inputs. Positive qualification is not supported: the pinned Uganda feature and UBOS polygons disagree at eight centers, with one different representation match; neither the stock refusal nor the source overlays decide applicability. The exact pinned metadata gives only generic Wikimedia Commons provenance, and the targeted public Commons lookup did not identify a feature-level 2006 source or UBOS crosswalk. The reviewer found no specific reasonable public metadata step left from the examined source trail. This supports a narrowly scoped, proposal-only researched-unresolved disposition for these nine keys, with all holds retained and no repair, ownership change, hold removal, package completion, or credit. The lookup does not prove that no further source record exists; material new lineage evidence can reopen the question.

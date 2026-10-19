# PNG67 source-relative held dispositions

Status: proposed evidence-only packet on accepted main `77609a1f159bfee954e52d48a883c5fe3e4b59f5`. It records exactly **67 residual keys** under issue #2376: **49** `unresolved_prior_source_fitness` and **18** `territorial_exclusion_cells`. Every row remains `held`; the packet adds **zero** repair credit, does not change selected data, and does not close issue #2376.

## Accepted baseline and residual

The original package has 56,552 land cells across 20,060 intervals and 130 owners. Accepted receipts #2399 (merge `0ae269650196956723d32b0c0e068f384b006b14`, receipt #6230570011) and #2506 (merge `448809e882ff9e2125702d30e3d7759a253470a3`, receipt #6253622919) account for 56,485 accepted source-relative repairs. This packet carries no new accepted credit; the remaining 67 keys stay held. The current selection check at `2b569815a7e37c5797586092688122d9b5d749b0` found all 67 at zero in base, patch, and effective assignments. Latest main `77609a1f159bfee954e52d48a883c5fe3e4b59f5` adds only TUV files; PNG input paths are unchanged. PR #2379 remains a donor/source-native handoff with zero repair credit.

## Source-fitness groups

The 49 exact held source-fitness keys map to four retained candidate components in `residual-dispositions.json`. Each key preserves its owner ID/name, land class, original reason, component ID, original source-comparison record location, compatible source subject IDs, and feature-level source-intersection witnesses. The group-level comparison is not a claim that the whole candidate component or any residual cell has current source applicability, physical support, or assignment authority. Retained source records say the unresolved prerequisite is whole-component source-fitness review; cause/surface applicability remain unknown.

## Territorial contact join

The 18 territorial keys map to owner 35609 (Kiunga Rural LLG, six cells) and 35754 (Lake Murray Rural LLG, twelve cells). The exact per-key table tests each center against all three retained full negative operands. Longitude follows the source contract's rational native-grid formula; latitude is read from the pinned little-endian binary64 native row raster. Source geometries are used verbatim as stored with no CRS transformation, datum conversion, or coordinate normalization. No center was classified on a polygon boundary.

Country Admin-0 and foreign Admin-1 operands each contact the same 15 cells; the foreign original-source ADM1 operand contacts nine; the source-specific overlap is six, and their union is exactly the 18 held cells. On immutable packet head `1bff559fd0bbe53a0540b41a7e434894b509f47`, `conservation_check` independently replayed the 18 territorial-contact rows against the exact three geometry inputs pinned in this packet. It confirmed the 18/18 contact rows were internally consistent, including the 15/15/9 per-operand counts, zero boundary classifications, and no missing or mismatched key classifications; it also confirmed the 49 source-fitness keys are disjoint from the 18 territorial keys. This review verifies reproducibility of the geometric contact calculation on the retained bytes only; the reviewer did not fetch the IDN ADM1 source. The separate `contract_precedents` exact-object/provider recheck is in progress. Neither geometry replay nor retained bytes authenticate upstream source delivery or vintage, establish present source applicability, or clear the provider retrieval limit: an earlier provider attempt could not fetch the IDN ADM1 source. These administrative footprints do not establish sovereignty, a current boundary, provider authority, source licensing, or cell assignment. Dataset release/vintage is not established for the country/Admin-1 files; the original-source footprint is a retained historical comparison input.

## Next step and limits

Keep all 67 rows held. The 49 source-fitness groups require the outstanding lineage/source-applicability evidence under the original #1626/#1647 workflow. The 18 territorial rows retain their per-feature geometric witnesses but still require a source-applicability decision; contact alone is not an authority decision. No repair, selected-data change, legal status, sovereignty, or whole-package closure is claimed.

Evidence pins and exact input metadata are in `evidence-pins.json`; the immutable original source records remain at those pinned repository paths.

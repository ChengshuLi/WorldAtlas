# Independent global census and executable queue review

Selection: `a61b6f9e7f88b1da380e3a834f89d7509132ed71`, ChengshuLi/WorldAtlas. Reviewed 2026-10-14. Read-only review; no ownership or repository changes.

## Conclusion

No unresolved census-count or executable-selector blocker found in the reviewed artifacts. The queue begins with actual current owner-0 intervals, not the historical gap-candidate mask. It separates qualification-ready candidates from lineage, mapping, physical-interpretation, source-conflict and physical/territorial disagreement investigations. Qualification-ready does not mean an approved repair.

There are 644 territorial family/cause packages covering 40,589,285 distinct owner-0 cells and 14 additional geographic source-disagreement packages covering 100,304,914 physical-land cells outside territorial coverage. Their disjoint combined domain is 140,894,199 native cells. Two supplemental investigations preserve invalid-source uncertainty and Antarctic policy exclusions; they are not added to this count.

Source/cause sessions, exact sparse selectors, preserved competitor/source IDs, shared input loads, measured source sizes/timings, owner/source conflict keys and explicit completion criteria provide practical worker entry points. The 523,918 component diagnostic is not used to create hundreds of thousands of tasks.

## Independent checks performed

1. Reconciled all territorial category totals, per-block totals, source roster indexing, package uniqueness and package totals. The categories partition 40,589,285 cells; 6,911,949 are unique current-location candidates with retained physical support, comprising 6,736,231 land and 175,718 inland-water cells.
2. Rehashed six territorial blocks and independently reconstructed the source sweep for 26 selected rows containing 1,029 classified intervals, directly from raw per-feature intervals. Checked source multiplicity, deduplicated owner union, half-open interval ordering, owner-0 containment and supported-unique physical joins. Included the held-out river row. This was a bounded check, not a second global rasterization.
3. Compared every native span of all three Fiji normalized source features against their unmodified valid original geometries using the exact native arithmetic with only the longitude-domain validation relaxed. All cell spans matched. Original source longitudes exceeded 180 by floating-point epsilon; polygon order changed, membership did not. Complete source-native counts were 306,203, 152,102 and 106,757.
4. Relocated the territorial selector and successfully extracted the 577-cell Lesotho package. Checked compressed-only source roster/lineage inputs. Intentionally corrupted isolated copies of shared metadata and interval bytes: both were rejected. Existing output directories were rejected, and failed runs had no package completion marker.
5. Independently checked the 14 geographic rectangle selectors form a disjoint complete native-grid partition, their per-block package counts sum correctly, and native cells immediately around every rectangle boundary obey the advertised geographic membership.
6. Relocated the physical selector and extracted 43,998 southern level-1 island cells; the separate invalid-source 948-cell envelope with its one source record; and 673 excluded Antarctic records with zero counted-work contribution. Rejected output collisions and a corrupted source block; failed extraction had no completion manifest.

Reviewer peak RSS in the sampled partition check: 657,860 KiB, below 1 GiB. No expensive global source scan was repeated.

## Findings resolved during review

- Added executable physical-only geographic packages, replacing a queue note alone.
- Made the territorial selector module-relative and usable with compressed metadata.
- Added shared metadata and interval hash validation, exclusive output creation, and completion markers only after count validation.
- Disclosed the three Fiji periodic-normalization exceptions and distinguished native compatibility from topology/territorial approval.
- Preserved invalid-envelope overlap explicitly: of 938 cells outside valid physical support, 63 are already territorial-covered (55 mapped), so only 875 lie outside the combined land/territorial domain. Supplemental uncertainty must not be added wholesale to the headline count.

## Interpretation limits

- 54,876,608,624 owner-0 cells include oceans; this is not a repair workload.
- Native Web Mercator cell counts are not ground area, especially in the Arctic. Do not prioritize solely by cell count.
- Complete retained-source enumeration is not contemporary global ground truth or complete worldwide territorial authority. Physical-only Arctic disagreements can reflect retained territorial footprints, coast/ice definitions or source vintages.
- Physical water is independent of territorial ownership. Water evidence does not veto a source-backed location assignment; river overlays remain a separate UI concern.
- The invalid original polygon was not implicitly repaired. Antarctic exclusion is an unmeasured policy-excluded domain, not zero missing cells.
- Connected-component counts use planar four-neighbor grid connectivity; opposite longitude edges are not joined. They are diagnostics, not task or jurisdiction boundaries.
- Before applying any future repair, rebase/revalidate current owner-0 membership and complete source qualifications; serialize selected-bank integration. This review does not approve any ownership change.

## Reproducible review receipts

- `sampled-partition-review.json` and `check-sampled-partitions.py`
- `fiji-normalization-review.json` and `check-fiji-normalization.mjs`
- `extractor-guard-review.json` and `check-extractor-guards.py`
- `physical-extractor-review.json` and `check-physical-extractor.py`

Review scripts contain the original review workspace location. The production selector portability was tested in isolated relocated fixtures. Receipts identify the selector code hashes actually exercised.

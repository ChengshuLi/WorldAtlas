# CAF 461 held residual: proposed documented unresolved disposition

**Disposition:** Proposal only. All 461 residual cells remain held. This packet claims no new accepted outcomes, repairs, exceptions, owner changes, or issue completion. It requests issue-level review of a documented-unresolved disposition under the original per-interval “additive repair or documented exception” contract.

## Exact scope and current selected-owner observation

The pinned original package is `gb-CAF-ADM3--repair-evaluation`: 2,130 land cells in 1,319 interval segments across 46 owners and 46 source atoms. The previously accepted/supported subset remains 1,669 cells; the residual is exactly 461 held cells, all recorded as `territorial_exclusion_cells`, across 36 owners (12 wholly held). The full original owner roster is preserved.

`current-selected-owner-observation-cdce5b02.json` is a local preparation artifact from current main `cdce5b02d354431321436b8f8674d804df629c01`; it is not included in this branch. The values below describe that artifact but cannot be independently verified from this PR alone. It queried all 2,130 original package cells. Base owner is zero for all 2,130. The existing accepted additive product has an owner on 1,669 cells and zero on the 461 residual cells; effective selected owner is zero on those 461, with no base/product overlap. This is a current selected-owner observation only: it does not establish source applicability, rights, physical correctness, or acceptance.

`caf461-proposed-unresolved-disposition.json` is a local preparation artifact and is not included in this branch. It joins every held tuple to its exact interval row, source-feature indices, original target, held reason, and current observer result. The 461 keys are unique and each has `base_owner=0`, `accepted_additive_owner=0`, `effective_selected_owner=0`, `owner_id=null`, and `existing_product_overlap=false`. Each row remains `accepted:false` and `proposal-only`; those row-level facts cannot be independently verified from this PR alone.

## Source, physical, and rights limits

All 461 keys fall inside a retained full-original `mapped_land_support` run; none falls inside the narrowed evidence run used for the 1,669-cell qualified subset. This identifies source coverage, not causal per-cell contact, legal applicability, current authority, or sovereignty. Source-feature indices and target-level territorial-exclusion context are retained per row, but they do not prove that the exclusion applies to each key.

The retained physical packet contains whole-target reconstructions for all 46 targets, with 47 explicit disjoints and 93 query witnesses and no target issue rows. These are whole-target results, not per-held-cell physical determinations. The original class ledger records all 2,130 cells as land and none as inland water; that classification alone does not prove each source boundary placement.

The primary source is geoBoundaries gbOpen CAF ADM3, represented as 2018, role Commune, with recorded CC BY 3.0 IGO metadata. Distinct CAF ADM1/2/3 source vintages and licenses remain separate. The retained source-rights interpretation has unresolved attribution, share-alike, editionless/generic license, vintage, CRS, and COD/FOD terms questions. Issue #899's law-era crosswalk remains unresolved; 21 of 46 positive atoms overlap its 92 subjects. No current legal boundary, statutory parentage, sovereignty, or source accuracy is inferred.

## Proposed unresolved disposition and acceptance gate

For each exact residual key, the proposal records the held outcome and the concrete unresolved question: whether an applicable retained source/foreign operand supports that recorded exclusion, or whether a different source-supported repair is justified. Available source and physical records are included at their actual granularity. Where they are target-level, the packet labels them target-level and does not convert them into per-key findings.

The packet relies on the original contract's documented-exception alternative; it does not claim that a positive additive repair is required or that an exception is already accepted. It requests explicit issue-level acceptance of this per-key documented-unresolved proposal. Until that acceptance is recorded, all 461 outcomes remain held and receive zero new credit. The 1,669 previously supported cells remain unchanged.

## Files and provenance

- `caf461-held-keys.jsonl`: 461 exact held tuples, original interval-row locators, source indices, target context, and held reason.
- `caf461-evidence-summary.json`: detailed evidence summary, source/physical/foreign/rights pins, and derived counts.
- The current selected-owner observation and derived 461-row proposal are local preparation artifacts and are not included in this branch. This is a partial evidence handoff, not a complete-reference packet; the PR must remain draft until the references are available and reviewed.

Historical source paths in the evidence summary identify immutable prior evidence. They are not represented as files in the current-main checkout unless their exact current path is present.

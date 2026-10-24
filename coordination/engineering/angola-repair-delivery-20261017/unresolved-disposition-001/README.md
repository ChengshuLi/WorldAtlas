# Angola original interval disposition proposal

This additive packet makes the existing Angola stock handoff's cell accounting explicit at the original interval level. It does not rerun or replace the source, geometry, physical, or historical assessment.

## Result

The original `gb-AGO-ADM2--repair-evaluation` queue contains 170,526 cells in 15,252 exact intervals across 47 targets. The retained stock disposition and accepted #2377 receipt account for 141,263 supported cells across 9,939 intervals. The other 29,263 cells across 5,313 complete intervals and 28 targets remain a **proposed documented-unresolved source-disagreement disposition**. They receive zero additional repair or exception credit in this packet.

The generator joins every frozen queue interval to the retained held spans and the literal current-selected-owner observation at `c58875b56e3954070632f1626a0724ef3108dc11`. It requires each original interval to be wholly supported or wholly held; no mixed interval is assigned a disposition. It also verifies that every held key has zero base/additive/effective selected owner, every supported key is effectively assigned to its exact original target, and the full cell and owner counts match the retained stock disposition.

## Files

- `interval-dispositions.json` contains all 15,252 original intervals and their explicit accounting category. `accepted_supported_delivery` references the accepted #2377 delivery receipt. `proposed_documented_unresolved_source_disagreement` has `accepted_repair_credit: 0` and points to the preserved foreign-ADM1 contact finding.
- `../method/build-unresolved-interval-disposition.py` reproduces the interval join and rejects denominator, owner, key, partial-interval, or current-selection mismatches.
- `current-selected-owner-observation.json.gz` is the complete 170,526-key output of `scripts/observe-selected-owners.mjs`, run against the exact current-main commit. Its report explicitly limits itself to literal selected ownership and does not claim scientific qualification.

## Evidence references and limits

- Accepted supported-delivery receipt: [PR #2377 accepted merge result](https://github.com/ChengshuLi/WorldAtlas/pull/2377#issuecomment-6230307071).
- Independent source/partition review: [issue #2313 review checkpoint](https://github.com/ChengshuLi/WorldAtlas/issues/2313#issuecomment-6228143772).
- The 29,263 held cells are the conservative union of whole foreign ADM1 source contacts (NAM 15,255; COD 13,269; COG 722; ZMB 17). The source products have different represented years and licenses; the original 2018 Angola ADM2 source is CC BY 3.0 IGO. No legal, sovereignty, current-boundary, whole-feature, or source-applicability determination is made.
- The source-relative accepted delivery remains 141,263 cells. The 29,263 held cells remain unaccepted until separately reviewed and accepted. This packet does not close issue #2313, change selection, resolve the separate source-conflict or physical-interpretation packages, authorize an import, or assert a regional certificate.

Rebuild the interval accounting from a checkout of this PR head with its complete history (including the pinned current-main commit) and Python 3. The observer report is intentionally pinned to the measured main commit, not to this packet's later commit:

```sh
out="/tmp/angola-interval-dispositions-$(date +%s).json"
python3 coordination/engineering/angola-repair-delivery-20261017/method/build-unresolved-interval-disposition.py \
  --out "$out"
cmp "$out" \
  coordination/engineering/angola-repair-delivery-20261017/unresolved-disposition-001/interval-dispositions.json
```

The command uses no external packages and refuses to overwrite an existing output.

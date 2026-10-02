# Sourced source-policy corrections

Reviewed 1 October 2026. The original `data/location-policy.json` remains byte-identical. A sourced overlay corrects reference-role descriptions for every conclusively identified Europe profile, including Spanish locations outside Europe. It does not alter geographic identity, geometry, membership, temporal names or historical attributes.

| Profile | Correct effective role | All current locations | Source proof |
| --- | --- | ---: | --- |
| Italy | Published ISTAT local labour systems (2011 geography, 2018 update) | 610 | Every current SLL source code matches the official SIAT code registry; independent count query reports 610. The retained source geography hash is unchanged. |
| Spain | MAPA agricultural district adaptations plus retained municipalities | 384: 341 agricultural, 43 municipal | Official MAPA layer explicitly describes Comarcas Agrarias and province/comarca fields. Municipality metadata remains separate. Europe-only counts are 333+39; the correction includes the other 12 locations. |
| Kosovo | Seven named source district territories | 7 | Actual pinned original GeoJSON has seven District of ... features with exact current source-ID correspondence. The metadata's Municipalities/48-unit claim is retained as contradictory source metadata. |

`data/source-policy-corrections/europe-v1.json.gz` contains complete before/after policy objects, all 1,001 stable location IDs with source-role crosswalks and unchanged footprint/metadata/parent hashes, byte-exact original policy text, fresh/retained source receipts and two stable-ID area-label proposals. Supported source roles do not certify consistent location scale or complete cities/islands; every branch remains semantically open.

## Effective-policy lookup

`src/source-policy-corrections.js` exports `effectiveSourcePolicies(basePolicy, correctionBundle)` and `correctedLocationSourceRole(locationId, correctionBundle)`. Python review scripts can import `effective_source_policies(base, bundle)` or `load_effective_source_policies()` from `scripts/source_policy_corrections.py`; Python/JavaScript parity is tested. The resolver returns a new policy object and never mutates its input. It accepts only the recorded original or already-corrected policy entry; an unrelated policy edit requires a new reviewed correction. Application/global-review consumers should use the returned effective policy and its correction evidence, preserving `retained_administrative_selection` as original context. The legacy `level` remains the selected administrative source layer; `effective_level` describes the actual installed role and must be used for atlas-role presentation. An ADM integer is not an atlas tier.

The full bundle is a durable research artifact. Static coverage can use a bounded projection of its `policy_corrections` and keyed location annotations; it should not expose all raw source receipts in the main location panel. Root integration consumes the overlay separately from the frozen geographic input files. The UI/database/content separation remains intact.

## Stable-ID label proposals

- `framework:area:france:a85924a668ef`: proposed reference name **Monaco**. Current member/province inventory contains only Monaco; Monaco Statistics corroborates that reference identity.
- `framework:area:belgium:3a14f80912de`: proposed reference name **Luxembourg**. Current member/province inventory contains only Luxembourg; GISCO identifies Luxembourg independently of Belgium.

Both proposals preserve original complete group objects, member IDs, footprint hashes, parent IDs and source proof. They are **not installed**. They do not approve coextensive tiers or compact-territory granularity, and they do not rename historical entities at invented dates. A later reviewed hierarchy migration must preserve the original labels/evidence and regenerate the appropriate hierarchy-dependent assets.

## Validate or regenerate

```sh
python scripts/prepare-europe-source-policy-corrections.py --check
python test/europe-source-policy-corrections.py
node --test test/source-policy-corrections.test.mjs
```

The producer reuses the embedded official source observations on a fresh clone. A new factual retrieval can be supplied with `--observations path/to/receipts.json`; changed sources need new receipts and explicit review. It never writes base policy, geography, hierarchy, prepared attributes or historical records. Its input hashes and every ID/footprint classification are rechecked before producing the overlay.

# West Siberian role and multipart evidence follow-up

Research packet for issue #1092, prepared 2026-10-06. It assesses exactly the 45 subjects listed by the issue; sorted subject IDs hash to `bfc28011d523d063794c21c09eb7a3671e2215bc285a5ce786d4d3e17448b561`. The reproducible row-level record is `findings/followup-assessments.json`. The derived scope/pin record is `baseline/issue-contract.json`.

## Findings and limits

The inherited source review separates three questions. The 11 ecological fragments intersected from four administrative source districts are not complete administrative units. Their administrative `Raion` source role is unsupported; the findings mark these `correction-needed` and recommend a product/engineering decision that preserves their IDs, geometries and lineage until an explicit ecological type/layer is available. They are not authorized for geometry edits.

The 25 city-named subjects have evidence that their source names describe municipal city or urban-okrug forms while the Atlas source role says `Raion`. Russian municipal-government classifications and administrative-territorial ranks are distinct concepts. The records therefore do not infer that a city-okrug label requires a different Atlas tier: they recommend a sourced role crosswalk with municipal type represented separately. The Altai Krai 2026 law-based list was not retrieved, and Slavgorod's source-era city-okrug label conflicts with a later official Treasury search lead describing conversion to municipal okrug. Row-level current legal status remains limited or unresolved. No bulk tier or geometry change is proposed.

The nine multipart features retain their 2017 source component counts and historical source parent context. Official rosters can help identify names and municipality classes, but no complete current official polygon or legal annex was retrieved and compared component by component. Islands, omissions, inclusions, current extents and exact legal parent assignments remain unverified. These nine findings remain `insufficient-evidence`; their counts are source facts, not evidence of completeness.

The 2017 geoBoundaries source represents boundaries for 2017, was updated 2023-03-03 and built 2023-12-12. Its metadata reports 2,328 units, while the complete 120,489,189-byte source archive contains 2,327 features. The archive's whole-file SHA-256 is `74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0`; its license is ODbL 1.0 with OpenStreetMap and Wambacher attribution. The full archive is not redistributed; restoration instructions and the retained, scoped evidence hashes are in `sources/source-register.json` and the inherited packet. The Resolve ecoregion source is CC BY 4.0; its exact four scoped features and metadata remain in the inherited packet. Neither source establishes current legal geography.

Official Rosstat pages, the federal OKTMO catalog, statutory/municipal pages and MChS page are catalogued with direct URLs, apparent vintages, intended source roles, license limits, restoration instructions and access limitations in `sources/source-register.json`. Except for the inherited retained MChS capture, the new official materials were surfaced as official-page text by search extraction; their source bytes were not retained or hashed. In particular, a normal TLS-verified Rosstat request failed certificate validation, and certificate checks were not bypassed. These are discovery leads and bounded contextual evidence, not inspected byte-level source records. Do not treat them as geometry evidence or claim current completeness from them. An engineering/research handoff should retrieve the current official files through a verified channel, record exact bytes and terms, and compare each member and multipart component to its cited legal annex or authorized geometry.

## Reproduction

From the repository root, run:

```sh
python3 data/regional-review/west-siberia-roles-followup-20261006/reproduce-followup.py
```

The generator checks the inherited assessment's pinned file hash and baseline, derives the exact 45-member roster, validates positive and negative scope controls, emits the row-level assessment and issue-contract files, and writes `findings/reproduction-result.json`. Two consecutive runs produced identical assessment SHA-256 `05ad7a208d2be3531d9be343bcb51d0c02349152ae69c84bfd9b5cb185e8bb47` and issue-contract SHA-256 `13a9d0c8bbf6fbc80f98a8842c82f315211d9183e066a246e319a90dc46f9acf`; category counts were 11, 25 and 9 respectively. Hashes establish reproducibility of this derivation, not correctness of upstream geography or the source descriptions.

This packet is a bounded source/role research result. It does not certify the West Siberian region, current boundaries, source completeness, or authorize imports, geography changes, publication or regional approval. The role crosswalk, official-byte restoration and component-level boundary research are explicit engineering/research follow-ups.

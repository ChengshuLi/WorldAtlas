# Argentina complete-family source-fitness evidence

This packet assesses exactly the seven-member family `gap-source-batch:af41d8136269b78548021a84` for issue [#1418](https://github.com/ChengshuLi/WorldAtlas/issues/1418), linked to the still-open parent [#1202](https://github.com/ChengshuLi/WorldAtlas/issues/1202). It preserves all seven physical components, four current contacts, three positive-length neighbors, all six administrative source-feature observations referenced by the component rows, the one recorded land-source-fitness row, and the original emitted source-relative rows and numeric values. The complete rows are in the two `source-fit.json` results and the compact family/component files beside them.

## Scope and current evidence

The frozen routing report records seven components in source-family order with roster SHA-256 `b2b8155d09bfa4e86a51b8ed6617927790e9c666c9294f96fcc9a7453b87dbda`. The four current contacts are Castelli (`gb:ARG:ADM2:61730980B13025573352502`), Villarino (`gb:ARG:ADM2:61730980B44606052944654`), Magdalena (`gb:ARG:ADM2:61730980B51096129050346`), and Pinamar (`gb:ARG:ADM2:61730980B99310691740446`). Positive-length neighbors are Castelli, Villarino, and Pinamar; Magdalena is a contact but not one of the recorded positive-length neighbors. The emitted family record does not provide a numeric boundary length.

The source rows reference six 2020 geoBoundaries feature IDs: Castelli, Patagones, Villarino, Magdalena, General Juan Madariaga, and Pinamar. The component rows, including each recorded feature intersection, source hash, original measurement, and identity binding, are preserved without rerunning the global physical producer. Their status mix is three `mapped-land-support`, one `mixed-source-support`, one `outside-mapped-L1-context`, and two `unknown`; two members remain in numeric closure. The family’s exact next-prerequisite counts are preserved in the full family row. These are prior source-relative classifications, not new geometric measurements or proof of land surface.

## Source identity, terms, and limits

The authenticated consumed product is the simplified geoBoundaries ARG ADM2 GeoJSON at the URL in the pinned [original-source catalogue](../../../coordination/engineering/original-geography-source-corpus-20261006/catalogue.json). The raw decoded payload is 5,502,879 bytes, SHA-256 `cedee8710e49d9017327fc1d4b2dc536e95a82317dc94c3bac8d9404af6bf771`, CRS84 (longitude/latitude), and 525 features. The catalogue’s advertised count and retained product metadata say 526. All six source feature IDs present in the physical component rows resolve in the consumed product. The four current contacts match by exact `shapeID` and `shapeName`; the simplified features have null `shapeParent`, while the Atlas contact records currently carry the Buenos Aires parent. This is an identity/context reconciliation, not a boundary comparison.

The retained geoBoundaries product metadata records boundary year 2020, departments, underlying sources Instituto Geográfico Nacional and UNHCR/OCHA ROLAC, CC BY 3.0 IGO, source data update date 2023-01-19, and build date 2023-12-12. The product-level retrieval timestamp is not recorded; the `original-geography-source-corpus-20261006` path identifies its collection campaign only. The source registry and frozen routing row record an **unsimplified** locator, while the catalogue and consumed bytes identify the **simplified** product. These locators and bytes are not equated. The report retains both records.

The metadata states CC BY 3.0 IGO. The [official license deed](https://creativecommons.org/licenses/by/3.0/igo/deed.en) describes attribution, a license link, and no implied endorsement; that record does not resolve upstream permissions beyond the product metadata or establish political authority, legal boundaries, currentness, dry land, ownership, source lineage, or completeness.

The six geoBoundaries names have exact-name matches in the pinned Georef comparator for Buenos Aires (Castelli, Patagones, Villarino, Magdalena, General Juan Madariaga, and Pinamar). The comparison includes only IDs/names/province labels from the Georef records. It does not compare or redistribute Georef geometry. Its layer vintage and reuse terms remain unconfirmed in the pinned #960 packet, so this is not an independent authority or legal-boundary finding.

Completed #442 remains the source for the prior unsimplified product record: 69,702,323 decoded bytes, 525 observed features versus 526 advertised, plus a recorded registry/source hash discrepancy. Its decoded payload exceeds the 32 MiB evidence input cap and is not decompressed here; its compressed archive bytes and existing inventory remain pinned. Contact reuse in #442 does not establish physical-family overlap. The earlier broad exclusion comment on #1202 is preserved unchanged; the subsequent correction records the distinct family-level reconciliation.

No source-fitness, physical-authority, cause, effective-date, lineage, land-water, physical-completeness, boundary-length, or legal-ownership approval is made. No geography or record is changed, no geometry is repaired or imported, and nothing is clipped, snapped, simplified, filled, released, or published.

## Reproduction and controls

Run with CPython 3.12.14 and the exact immutable helper pinned by issue #1418:

```sh
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/argentina-gap-source-fitness-20261007/reproduce.py --run argentina-run-3
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/argentina-gap-source-fitness-20261007/reproduce.py --run argentina-run-4
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/argentina-gap-source-fitness-20261007/reproduce.py --finalize-reproducibility
/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node scripts/evidence-quality.mjs research/geography/argentina-gap-source-fitness-20261007/evidence-quality.json
```

The runner reads only issue-pinned whole files through `Baseline`, authenticates the actual materialized bytes, applies the helper’s 32 MiB per-file and 256 MiB phase caps, and writes exclusively through `NewVintage`/`write_new_vintage`. It uses Python’s standard JSON/gzip libraries; no GIS library or global graph rebuild is used. Each fresh run checks all seven family members, all four current contacts, all six referenced administrative feature IDs, the one source-fitness row, all three neighbors, and the complete retained component source rows. A changed component ID in the full compressed family slice is rejected by the same input reader at the whole-file hash check before output admission. The two final `source-fit.json` files have equal whole-file SHA-256 `d75d630f538017709ba27e89ec76e68c2e95913ebfba19cdf35a27b8ef048bae`.

`evidence-quality.json` is the byte manifest for this packet. Its `limited` result is intentional: retrieval timestamp, unsimplified decoded input, Georef vintage/terms, source authority, physical cause and surface status remain unresolved. It is evidence review, not geographic approval or a publication gate.

Closes #1418

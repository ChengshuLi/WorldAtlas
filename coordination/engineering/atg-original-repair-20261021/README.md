# Antigua and Barbuda original repair evaluation

This packet covers the frozen original package `gb-ATG-ADM1--repair-evaluation`: 883 retained land cells in 288 original intervals, source family 12 / block 28, owner index 7110, and selector features 1274–1280. It excludes the distinct 130-cell / 103-interval `physical-interpretation` companion.

## Evidence and findings

- `current-selected-owner-observation.json` is the one stock current-owner observation at `ea099024c1d175842e4d323db752b49d9f7a5825`. It queries all 883 exact keys. Base, accepted-additive and effective selected owners are zero for all keys; there are no existing-product overlaps. This is not historical acceptance credit.
- `factual-disposition-proposal.json` retains the original 288 intervals and provides all 883 `(y,x)` rows joined to exact source-candidate, land-support, inland-water, roster, lineage and observer evidence. All 883 keys have a matching owner-7110 candidate run and one selected source feature; all hit retained land support and none hit the retained inland-water mask. The source feature occurrence counts are included in the packet.
- The selected seven features resolve to named stable IDs through the roster and lineage. The raw source product has eight features including Redonda (index 1273). The repair selector contains only indices 1274–1280; Redonda is outside this exact repair slice. The global source-raster report says all eight features are mapped; this packet does not infer that Redonda is absent from the broader raster or the separate physical package.
- The retained compressed source payload is 9,157 bytes, SHA-256 `28c9286241b38663e4c2c3f24c21810e60e54b7c645569840805f6fd0b8be8e5`; decompressed source is 26,215 bytes, SHA-256 `021f6ca73869807bcb04d3b71ea1f26d630eb11707522ff1a0db5f3d86e40c8d`. Metadata records a Public Domain underlying license and the derivative product attribution statement records CC-BY 4.0; the retained record says the represented-year claim is 2009, while temporal status, underlying permission particulars, authority, current applicability and political interpretation are unverified.

## Proposed disposition

The packet proposes a documented unresolved exception for each of the 883 exact keys; all rows remain `accepted:false` and `credit:false`. No additive patch, owner change, source qualification, legal authority, sovereignty finding, current physical classification or geometry result is asserted. Root acceptance remains separate.

Evidence pins in the JSON bind every retained queue, mask, roster, lineage, source-catalogue, attribution and payload input to the observation commit and include byte sizes and SHA-256 values.

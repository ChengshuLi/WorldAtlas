# Source packet

This directory preserves bounded source inputs and retrieval/extraction receipts for issue #1355. It supports a source-fitness assessment of the exact 45-component physical-gap family `gap-source-batch:8875fd920e43656b5f36e704`. It does not approve, correct, import, publish, or establish legal or physical boundaries.

## Contents

- `family-row.json`, `component-roster.txt`, and `scope-extraction.json` preserve and validate the issue-pinned route-family membership against the original custody shards at baseline `eddf3d98c725a768959e431462b16d9adf507a41`.
- `worldcover/` contains the two complete retained ESA WorldCover 2021 v200 tiles. `worldcover-crops/` contains a bounded, all-touched extract for the western source tile whose full response exceeds the per-input evidence limit. The whole-tile and crop receipts record source checksums, endpoint metadata, derivation, and output checksums.
- `jrc-crops/` contains four bounded JRC Global Surface Water v1.5 crops for the 45-component footprint. `jrc-source-receipts.json` records original source tile metadata and crop hashes. `metadata/` preserves the provider's XML metadata.
- `metadata-sources.md` records primary source pages, source terms, temporal and quality limits, and the unresolved BIG geometry reuse terms. The packet contains no BIG polygon geometry.
- `extract-scope.py` reproduces the route-family extraction and component roster checks from the pinned git baseline. `extract-worldcover.py` records the bounded WorldCover crop workflow; it refuses to replace existing outputs.

All data and analyses are source-relative. Raster class, mapped-water presence, non-detection, and overlay results are not ground truth, legal authority, proof of dry land, or an explanation of how a gap formed. No geometry repair, buffering, or boundary proposal is part of this source packet.

## Reproduction environment

Python dependencies are pinned in the packet's `requirements.txt`. Source payloads and raster inputs are individually bounded by the repository evidence limits. Temporary full source tiles used to create crops are removed by the extraction workflows; the receipts preserve their observed hashes and endpoint metadata. Retrieval timestamps are recorded only at the precision actually captured.

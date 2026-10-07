# Source packet

This directory preserves bounded source inputs and retrieval/extraction receipts for issue #1355. It supports a source-fitness assessment of the exact 45-component physical-gap family `gap-source-batch:8875fd920e43656b5f36e704`. It does not approve, correct, import, publish, or establish legal or physical boundaries.

## Contents

- `family-row.json`, `component-roster.txt`, and the original `scope-extraction.json` preserve the initial issue-pinned route-family membership extraction at baseline `eddf3d98c725a768959e431462b16d9adf507a41`. Current-base receipts independently rerun the complete 14-part source scan against `839883ae281af7bf012f694698624a7ec77275e1`, `431ecbbfee17c71f4a08060d40664b8a616ba08f`, and `745cc86a5e1e4d9917730bad0b5a7a031de99ceb`; each retains the same exact family-row and roster hashes. All prior receipts remain unchanged.
- `worldcover/` contains the two complete retained ESA WorldCover 2021 v200 tiles. `worldcover-crops/` contains a bounded, all-touched extract for the western source tile whose full response exceeds the per-input evidence limit. The whole-tile and crop receipts record source checksums, endpoint metadata, derivation, and output checksums.
- `jrc-crops/` contains four bounded JRC Global Surface Water v1.5 crops for the 45-component footprint. `jrc-source-receipts.json` records original source tile metadata and crop hashes. `metadata/` preserves the provider's XML metadata.
- `metadata-sources.md` records primary source pages, source terms, temporal and quality limits, and the unresolved BIG geometry reuse terms. Exact BIG 2022 KSP and 2023 RBI layer metadata JSON responses are retained under `metadata/`; the packet contains no BIG polygon geometry.
- `extract-scope.py` reproduces the route-family extraction and component roster checks from the pinned git baseline. `extract-worldcover.py` records the bounded WorldCover crop workflow; it refuses to replace existing outputs. `produce.py` computes the exact original-component overlays, current-admin contacts, and per-component source-raster histograms into an exclusive, complete run with `publication.json` written last.

All data and analyses are source-relative. Raster class, mapped-water presence, non-detection, and overlay results are not ground truth, legal authority, proof of dry land, or an explanation of how a gap formed. No geometry repair, buffering, or boundary proposal is part of this source packet.

## Reproduction environment

Python dependencies are pinned in the packet's `requirements.txt`. Source payloads and raster inputs are individually bounded by the repository evidence limits. Temporary full source tiles used to create crops are removed by the extraction workflows; the receipts preserve their observed hashes and endpoint metadata. Retrieval timestamps are recorded only at the precision actually captured.

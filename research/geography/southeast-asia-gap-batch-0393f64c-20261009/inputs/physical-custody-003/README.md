# Retained physical and query custody, continuation 003

This packet preserves the exact 30 contract-prioritized cases from issue #1641 using already-retained repository inputs. It also carries the complete 318-component roster and its 122 family locators. The builder reads immutable Git blobs and the pinned original decoders; it does not run GIS, overlays, comparisons, or physical operators.

`manifest.json` inventories 66 independently compressed JSON files. `index.json.gz` contains the batch roster, source identities, dispositions, and limits. Each file under `cases/` contains one complete case, keeping its source, target, current component candidate, prior records, physical query relations, and existing comparison rows together. Each file under `sources/` contains one complete GSHHG query-source pointset and its original native-record binding. Encoded and decoded byte counts and SHA-256 values are recorded for every file. This partition keeps each decoded file below the repository's ordinary 32 MiB evidence-file limit.

The administrative source feature, administrative target feature, and current Atlas component candidate remain separate records with distinct roles. The current component candidate does not stand in for a selected owner, source ordinal, parent, native cell, or uncovered-cell binding. The 288 non-priority component states remain in the earlier full-batch packet.

GSHHG is the retained 2017 distributed release with older heterogeneous WVS/WDBII observation dates. The relations and pointsets remain source-relative diagnostics. Contemporary physical status, source fitness, narrow registration-sensitive shoreline or channel truth, river widths, seasonal wetness, cause, political ownership, authority, and repair eligibility remain unresolved. No class, repair, or geographic approval is asserted.

Run `assemble-physical-query-custody-003.py` from the repository root to reconstruct these files from the immutable source pins recorded in the index and manifest. The script refuses to replace differing custody outputs.

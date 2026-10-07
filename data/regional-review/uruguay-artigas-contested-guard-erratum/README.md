# Artigas offline reproduction preservation guard

This additive packet addresses the output-preservation defect recorded after PR #1173. The earlier packet and its source files remain byte-for-byte unchanged. The runner admits only a fresh direct child of this packet's `outputs/` directory, rejects an existing destination, traversal, symlink destinations, and changed code or inputs before publication, and writes the report only after reserving the output directory.

The runner executes the retained `inputs/code/capsule-reproduce.py`, a checked-in offline adaptation of the exact original script retained beside it. It consumes five complete baseline files plus both complete source payloads. Their full-file SHA-256 pins are checked before the analysis. The produced JSON is compared byte-for-byte with the retained historical report; the retained runs all match its SHA-256 `3970173b2c2050c1099ec427e4d64076e96a3000635ba20db203fa204320e44a`. `inputs/original-source-inventory.json` preserves the earlier packet's full source hash, retrieval, vintage, license, and restoration records, including the legal-source restoration instructions.

Run from the repository root:

```sh
python3 data/regional-review/uruguay-artigas-contested-guard-erratum/reproduce.py --output data/regional-review/uruguay-artigas-contested-guard-erratum/outputs/run-5
python3 data/regional-review/uruguay-artigas-contested-guard-erratum/verify-guard.py
node scripts/evidence-quality.mjs data/regional-review/uruguay-artigas-contested-guard-erratum/evidence-quality.json .
```

Each output name is single-use; choose a new name for every successful run. The negative-control verifier temporarily probes code/source drift and restores the original bytes in a `finally` block. It also checks an existing sentinel, traversal, and a symlink destination without writing outside the packet.

## Evidence limits

This reproduces representation only. The report reads the exact Artigas ADM1 subject and IGM IDs 15/16 attributes, feature counts, geometry type, and coordinate-member presence. It does not assess topology, overlap, containment, area, legal boundaries, sovereignty, or ordinary ADM2 membership. The IGM layer describes an official mapping representation, not bilateral agreement. The historic 2017 geoBoundaries feature is a single ADM1 reference. Source verification labels and legal restoration instructions are retained from the earlier packet; this safeguard did not reauthenticate sources or retrieve restoration-only legal originals. It does not resolve title, certify the region, repair geography, import data, or deploy anything.

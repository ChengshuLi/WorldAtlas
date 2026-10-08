# Comoros locality source search (issue #634)

This is a bounded evidence-only packet for `atlas:territory:COM` and its three retained source-island components. It adds research findings and a reproducible administrative crosswalk, without changing hierarchy, geometry, IDs, production data or release state.

## Files

- `source-inventory.json` records source identity, vintage, retrieval time, response hashes, reuse/access terms and limits. No copyrighted or access-controlled source bytes are copied into this packet.
- `findings.md` explains the source decision, island/admin findings, uncertainty and the exact next-owner handoff.
- `administrative-crosswalk.csv` lists the source's 3 ADM1 islands, 17 ADM2 prefectures and 55 ADM3 communes; each row is an administrative unit and explicitly not a settlement.
- `reproduce.py` validates the predecessor archive's exact SHA-256 and generates or verifies the crosswalk without external packages.
- `test_reproduce.py` exercises correct counts/output, changed-input rejection and deterministic repeated rendering. `positive-control.json`, `negative-control.json` and `reproducibility.json` preserve the bounded run receipts.

## Reproduction

From repository root:

```sh
python3 data/regional-review/comoros-settlement-source-20261003/reproduce.py
```

The command checks the output against the retained OCHA COD-AB 2019 archive in predecessor packet #482. To regenerate the CSV only if it is absent:

```sh
python3 data/regional-review/comoros-settlement-source-20261003/reproduce.py --write
```

The source archive is intentionally not duplicated. Its restoration URL, license statement, size and SHA-256 are in `source-inventory.json` and in predecessor #482.

Run the focused controls from the packet directory with Python 3:

```sh
python3 -m unittest -v
```

## Result

An official village-coordinate lead exists in INSEED metadata, but no inspected source is both an openly reusable, complete settlement gazetteer and verifiable against every ADM2/ADM3 unit. The EHCVM 2020 point variables describe a sample and contain missing village coordinates; the RGA-2 2025 metadata indicates community GPS but restricts microdata and does not provide public village rows, a clear spatial aggregation meaning or a redistribution license. The full settlement/admin crosswalk therefore remains unresolved. See `findings.md`; do not treat this packet or the administrative table as proof of regional completeness.

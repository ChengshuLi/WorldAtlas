# Paraguay validator integrity erratum

Issue #1330 adds a narrowly scoped, versioned validator-integrity packet under this directory. It preserves the completed #1111 correction and original #446 source packet. It does not repair or approve geography.

## What was reproduced

Two accepted full reproductions ran in distinct credential-scrubbed Python `-I` child processes at the pinned 27be775 vintage, each with the exact historical `scripts/evidence/immutable.py` bytes supplied at its import boundary. Earlier `original-run-one` and `original-run-two` are preliminary shared-process runs; the accepted isolated outputs are under `vintages/original-isolated-run-one/` and `vintages/original-isolated-run-two/`. The three original products matched the retained #1111 files byte for byte on both runs. Each full run retained its runtime, issue and helper pins, path/blob inventory, output hashes and completion receipt. Each contains all 12 previously successful controls.

The new raw-roster check reads the 215-unit ledger, the 32-parent scope and the parent rows before converting child tokens to sets. It rejects duplicate and blank raw tokens, duplicate parent rows, missing or substituted/foreign children, incorrect counts, and malformed columns. Two coherently rehashed candidates are also passed through the unchanged legacy packet and parent gates; those gates accept the duplicate and blank token cases. The new check rejects both.

The output-admission controls exercise the current shared `NewVintage` entry point. They preserve an existing sentinel; reject an existing run, dangling symlink, traversal and symlink-escaped destination; enforce file and whole-phase byte limits; and retain a real failure after the first calculated output without a completion receipt. A complete helper-code drift fixture is rejected before the legacy entry point runs. All fixture outputs remain inside this owned directory.

The accepted pair shares a complete unique-content input inventory of 235,285,126 bytes. The largest raw file is 16,950,115 bytes; the exact 45,589,273-byte Paraguay original remains absent and is not fetched. Input-byte identity, source vintages and the runtime appear in the run receipts. The historic 27be helper pin and current-main 913486 helper pin remain distinct.

Run the full historical reproduction from the repository root with Node/Python runtimes declared by the current repository workspace:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 research/geography/paraguay-validator-integrity-erratum-2026/reproduce_validator_integrity.py
```

It uses caller-selected exclusive output vintages; `--isolated-full-runs` runs the accepted isolated pair and intentionally refuses to overwrite any existing destination. The helper-drift control has its own fresh output vintage:

```sh
PYTHONDONTWRITEBYTECODE=1 python3.12 research/geography/paraguay-validator-integrity-erratum-2026/reproduce_validator_integrity.py --helper-drift-control
```

Inspect `isolated-reproduction-results.json` for the accepted full-run pair, `reproduction-results.json` for preliminary runs and controls, every whole-run `publication.json` receipt, and `evidence-quality.json`. The accepted runs preserve the three historical outputs byte for byte in their new vintages. Earlier same-process runs are not relied on for acceptance. Failed runner/harness attempts are separately recorded in `failed-attempts/`; a failed attempt is not a successful reproduction. The post-calculation failure control is under `vintages/failure-after-calculation/` and has no `publication.json`.

## Geographic evidence limits

The source context in `source-context.json` binds this erratum to the original issue scope, source inventory, ledgers and exact source vintages. The original 215-location scope covers one physical Southern Patagonian Ice Field feature, 195 Paraguay Atlas rows and 19 Uruguay departments. Paraguay coverage is partial (195 of 243 Atlas rows); Argentina South is partial (one of 54 rows); Uruguay covers the 19 department-name scope. The original #446 Paraguay roster has 247 source features: 241 one-to-one native rows and six records represented by aggregates. The 195 scoped Paraguay Atlas rows comprise 194 native IDs and one multipart Atlas ID representing two source records.

The original 2012 Paraguay geoBoundaries source file is 45,589,273 bytes and has the inventory SHA-256 `d42bd1f9…b22362858`. It exceeds the repository’s 32 MiB per-file limit, so the packet preserves its exact restoration URL and verification instructions instead of the source bytes. Metadata associates it with CC BY 4.0, but the exact source file and its source-level rights statement were not re-inspected here. The 2022 INE statistical cartography says its DPA limits are referential; the published district count and names do not prove legal polygons or 2012-to-current successors.

The retained Uruguay 2017 source and 2024 IGM response support a name/role comparison only. The IGM metadata describes department polygons, cites IGM/AGESIC/IDE for free use, reports data updated 2024-09-18, and leaves temporal coverage undetermined. Its retained response contains 19 department-name matches plus separate Isla Brasileña and Rincón de Maneco features whose territorial meaning remains with its own follow-up.

The Southern Patagonian Ice Field record is a physical landform, not an administrative unit. Its Natural Earth source release, source feature ID and original bytes are not retained. Argentina-Chile treaty and foreign-ministry records preserve a pending demarcation context; this packet does not infer sovereignty or reassign the physical feature.

Open work remains explicitly owned: #926 (current legal Paraguay units), #928 (SPI provenance/identity), #929 (multipart geometry encoding, engineering), and #930 (Asunción city/district granularity, engineering). #927 is closed; that does not certify this region. See current statuses and timestamps in `source-context.json`.

No legal source acquisition, geometry correction, regional approval, certificate, release, import or publication is performed or authorized by this erratum. The partial research result refers to #1330 only; it does not certify #446 or any region.

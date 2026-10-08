# Southern Patagonian Ice Field source and parent assessment

Issue #928, exact subject `country-SPI`. Research packet prepared 2026-10-08 by worker `01a10948-7d38-75d0-bc01-4cc28ea41f49`; the claim receipt and manifest bind that reservation.

## Result

The exact pinned Atlas roster contains one feature. A dated Natural Earth 5.1.0 map-units file contains one matching `SPI` feature (`NE_ID=1729635141`) and describes it as an indeterminate, disputed map unit claimed by Argentina and Chile and under survey. Natural Earth's official terms page states that its map data are public domain; the page's retrieval hash and restoration instructions are recorded in `source-inventory.json`. This is a strong dated identity and map-unit source candidate.

It is **not verified as the exact original geometry source**. The candidate geometry hash is `08e44b0ec89bdfd84be2a604c01396778ac0130923676c67bd313ba0553f61f4`; the Atlas subject records `original_geometry_sha256=285e80dadd61de9903bf3070b7a594e4009034d8b67adc304111328da53468ce`. The exact source vintage and source bytes used by Atlas remain unresolved. Keep the current feature and stable ID pending source restoration and engineering review.

Official Argentine and Chilean materials establish that the feature's physical name does not define sovereignty. The 1998 bilateral agreement describes the boundary route between Monte Fitz Roy and Cerro Daudet, with its annexed charts forming part of the agreement. Both governments state that the Argentine glacier inventory used pre-1998 cartography in this zone. Chile's 2018 statement says Section A was determined and georeferenced, while work on Section B and common cartography remained underway at that time. No later official source specific to the Fitz Roy–Daudet line was located in this review; do not present 2018 status as current.

The Atlas `province` parent is a one-child `framework:province:southern-patagonian-ice-field:7fa95a3f233f` tier with geographic kind and open semantic review. The official glacier inventories describe a physical ice field and many outlet glaciers, not an administrative province. The packet recommends an engineering review of the redundant province tier and physical-feature representation; it does not choose a sovereign country parent or alter core geography.

## Contents and reproduction

- `source-inventory.json` records official sources, dates, exact downloaded-byte hashes, reuse terms, and restoration instructions.
- `findings.md` explains source meaning, vintage, completeness, license and limits, and the neighboring granularity assessment.
- `engineering-handoff.md` gives the specific unresolved source and hierarchy decisions.
- `reproduce.py` is read-only and emits the deterministic reproduction JSON to stdout. Compare it against the retained `reproduction-results.json`; the entry point accepts no output path and cannot overwrite packet evidence. Its four adverse controls confirm that duplicate or missing Atlas/Natural Earth identities are rejected.
- A corrupted output hash was also tested against the shared evidence validator; it rejected the packet with `Input bytes mismatch`.
- `evidence-quality.json` binds the packet to issue #928's existing source-review contract.

From the repository root run:

```sh
python3 data/regional-review/southern-patagonian-icefield-source-parent-20261005/reproduce.py | diff -u data/regional-review/southern-patagonian-icefield-source-parent-20261005/reproduction-results.json -
node scripts/evidence-quality.mjs data/regional-review/southern-patagonian-icefield-source-parent-20261005/evidence-quality.json
```

Run the `comparison command twice to verify byte-identical read-only output. It streams to a comparison process and creates no destination file. The reproduction verifies identity and provenance statements only. It does not validate the icefield boundary, resolve territorial sovereignty, certify a province/area hierarchy, or approve the region.

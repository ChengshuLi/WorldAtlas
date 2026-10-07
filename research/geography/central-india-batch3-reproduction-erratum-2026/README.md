# Central India batch 3 reproduction erratum (#1323)

This additive packet preserves the original #83 / PR #1105 reproduction and adds a bounded, pinned runner. It addresses reproducibility and preservation only. It does not adjudicate territorial law, certify a region, or authorize publication or imports.

## Reproduce

From repository root, use the bundled Python 3.12 runtime with the repository's Shapely and PyProj dependencies:

```sh
python research/geography/central-india-batch3-reproduction-erratum-2026/reproduce.py --vintage original-YYYYMMDD-unique
```

Choose a new name for every attempt. The runner checks the complete output set before calculation, reads pinned files from immutable commit `950eb2188e5b66d88ea47a679936a02fe3eb1c40`, validates the issue's exact pins and the predecessor's 12 source-inventory descriptors, and uses the shared immutable evidence helper from that same commit. It scans the full 36-entry world index for the exact 229 subjects and retains a disjoint 35-province partition. The original area scope remains partial: Madhya Pradesh 144/422 and Uttar Pradesh 85/244.

The retained native source is a 13,794,274-byte gzip. Its decoded bytes are hashed and admitted in 4 MiB chunks. One feature line is parsed at a time; every native `shapeID` is checked for uniqueness, and only the 229 matching geometries are materialized for analysis. A feature over 32 MiB is rejected. Two isolated staging roots run the predecessor analysis against pinned inputs. The complete JSON reports must match each other and the preserved original report byte for byte before `NewVintage` publishes any products. The original packet is never written.

The controlled vintage contains both full reports, an exact comparison, execution and input inventory, adverse-control receipts, and a final `publication.json`. Its built-in controls exercise the real materialized-input admission path with the altered Batiyagarh geometry, changed helper, changed hierarchy, changed UP roster, a missing native source, and a pre-existing output directory. Rejections must leave the selected product path absent or the colliding bytes unchanged. Earlier vintages without those controls are explicitly superseded in this README.

## Findings and limits

The retained 2018 geoBoundaries India ADM3 source contains 6,822 features against 6,836 declared in its metadata. Across the exact 229-subject batch, the retained report shows 202 topological equals and 27 differences. Those comparisons preserve diagnostics; they do not prove current legal boundaries or territorial correctness. Metadata asserts ODbL 1.0 and its attribution/share-alike terms; independent legal confirmation is outside this packet.

The issue's evidence scope is narrower than the macro handoff. The fixed Central India macro envelope contains 854 locations; the handoff says regional interiors are not approved and location attribute imports are not ready. This packet's 229 subjects leave 625 macro members outside its scope. The four part files holding these 229 IDs do not certify the other 625 macro members or the full region.

Current UP DARMS rosters provide names and selector codes, not legal boundary geometry. MP source pages are incomplete or contradictory, and the Mauganj order copy is unauthenticated. Parentage, source completeness, current legal polygons, boundary dates, and independent license verification remain unresolved. See [research-limits.md](research-limits.md) and the original packet's source restoration instructions.

## Preserved run history

`vintages/original-20261007-a/` is a preserved preliminary attempt that is **not accepted**: its two reports matched each other but differed from the predecessor in the reported source feature count discrepancy and the hash/size recorded for the patched producer. Those fields were corrected narrowly, and the runner now rejects any full-report mismatch before publishing.

`vintages/original-20261007-b/` through `vintages/original-20261007-e/` are preserved reproductions with exact full-report equality. Run `f` is the candidate acceptance vintage: it adds explicit proof that the shifted-footprint control changed geometry coordinates only while retaining the same subject identity and properties, alongside typed positive, negative, and two-run receipts. Repository evidence checks and distinct exact-head review are still required before the issue can close. Earlier outputs remain unmodified for audit history.

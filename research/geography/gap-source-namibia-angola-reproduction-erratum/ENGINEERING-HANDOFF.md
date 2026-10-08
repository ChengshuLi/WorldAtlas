# Engineering handoff: legacy standalone entry points

This geography packet is additive and stays inside issue #1437's owned path. The original files are preserved byte-for-byte, so the following defects remain in the original commands and require their owning engineering scope:

1. `research/geography/gap-source-namibia-angola-20261006/reproduce_full_product_comparison.py` must authenticate exact component/contact membership and immutable source, code and complete input bindings before computation and before any output write. It currently accepts same-length duplicate component or contact rows.
2. `research/geography/gap-source-namibia-angola-20261006/reproduce_source_geometry.py` has stronger identity checks but needs the same independently anchored input/code/source validation and output-safety behavior if it remains a supported entry point.
3. The original packet README must describe the pair matrix as using consumed simplified NAM/AGO contact geometries. Full product geometries are distinct same-ID operands used by a separately labeled comparison. Preserve all historical reports and add a new output; do not overwrite or relabel them.
4. Retain controls for same-length duplicate and missing component/contact rows, altered whole-input and code bytes, malformed or empty geometry, existing output directories, symlinked output roots, traversal attempts, and exactly 210 unique candidate/contact pairs. Fail before publishing accepted output.

Independent correctness checks in this packet reproduce the issue finding and provide a separately authenticated matrix, but they do not retrofit these legacy commands. This handoff is an engineering follow-up, not a source correction, territorial conclusion, or production approval.

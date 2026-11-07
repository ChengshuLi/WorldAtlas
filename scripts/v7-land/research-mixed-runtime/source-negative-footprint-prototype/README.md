# Source-negative containment helpers

This experimental, data-free overlay contains two independent building blocks. It does not register a decision, modify a map, or integrate with the mixed runtime.

- `federal_register_rectangle.py` parses a reviewed five-row west-longitude/north-latitude DMS rectangle from a bounded, cropped PDF page. It authenticates input bytes and canonical geometry against caller-supplied hashes, passes a sealed immutable copy of the PDF to the converter, and rechecks the source path after conversion. It fails closed on malformed, ambiguous, unclosed, or nonrectangular input.
- `negative_component_filter.py` removes any source-footprint-hit component from a separately resolved fully contained positive set. Root IDs are ephemeral results and must not be stored as selectors.

The caller is responsible for source custody, correct heading and crop provenance, same-generation component input authentication, geometry validity and boundary-center checks, source-independent geographic review, and explicit mixed-runtime integration. A historical marine unit is not necessarily an island boundary.

The PDF helper requires Linux sealed `memfd` support, `/usr/bin/prlimit`, and `/usr/bin/pdftotext`. The subprocess has a 45-second timeout and a 10 MB output-file limit; source input is capped at 32 MiB. Exact input and geometry hashes must come from authenticated configuration, not from this code.

Run the data-free tests from this directory with `python -m unittest discover -v`.

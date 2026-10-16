# Physical-gap audit successors

`scripts/physical_gap_successor.py` authenticates complete encoded and decoded
physical-source bytes and their exact gzip relation. `verify_decoded_relation`
checks both whole-file descriptors before comparing the decoded result;
`decode_gzip_layers` accepts one to three explicit single-member layers and
rejects truncation, trailing bytes, changed bodies and decoded-size overflow.

The live `scripts/worldwide_gap_successor.py` adapter consumes this helper.
Its own source and execution custody, exact ordered tile operands, unknown-state
handling and lossless delta reconstruction govern actual successor reuse. The
unused generic preview-snapshot planner has been retired; it was never the live
worldwide adapter. The retained tests exercise the decoding contract and the
actual adapter separately.

Archived physical-gap reports and manual reproduction code retain their original
source, execution and measurement vintages. This helper does not install a
preview, approve native ownership, resolve scientific uncertainty, or authorize
new source/physical-water claims.

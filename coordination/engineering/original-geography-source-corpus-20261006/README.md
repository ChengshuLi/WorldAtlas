# Complete original geography source custody

This packet retains the exact original bytes needed for source-versus-Atlas comparisons. It contains every source product consumed by the frozen administrative registry and a separate India ADM3 refinement product. It changes no Atlas geography, source selection, application, release, native grid or production data.

`catalogue.json` exhaustively binds source keys, cohorts, original whole hashes/sizes, recorded consumed locators, original metadata bindings, actual feature counts, advertised feature counts, payload order and byte offsets. Metadata remains in the named immutable baseline files. `transport-provenance.json` retains actual acquisition observations and earlier containing-file/archive relationships. Reused originals have their actual recorded retrieval observations where available; no missing earlier retrieval date is invented.

The payloads are gzip encodings of the original raw byte stream, using the existing immutable codec. Most products have one payload. Brazil ADM2 and India ADM3 use two contiguous fragments to keep every encoded and decoded ordinary descriptor within the existing bound. Fragments may cut through a JSON token: concatenate **decoded bytes in catalogue order**, then verify the reconstructed original whole byte count and SHA before parsing. Never JSON-reserialize fragments or substitute a full/reference/current source product.

`corpus.py` reads the actual committed package, verifies the complete registry/refinement cohort, every ordinary encoded/decoded descriptor and fragment binding, reconstructs every original, repeats deterministic compression, and examines every unmodified source feature. It rejects missing/duplicate source identities; invalid, empty or unsupported source geometries remain explicit per-source findings. Complete shape IDs are bound by a sorted roster hash. No union, normalization, MakeValid, buffer, snap, clipping or source simplification occurs.

Run from a repository containing the exact delivery commit, with Python3.12.14, zlib1.2.12 and Shapely2.1.2/GEOS3.13.1:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B coordination/engineering/original-geography-source-corpus-20261006/corpus.py \
  --repo "$PWD" --selected FULL_COMMITTED_PRODUCER_SHA \
  --output "$PWD/.cache/source-corpus-reproduction-new"
```

The selected full commit must contain the producer, catalogue and complete payloads. The program compares actual executed code and codec to their immutable containing bytes. Output directories are exclusive new vintages. Final delivery reports identify the executed producer commit, which predates the report-retention commit; they do not relabel frozen sources as later current geography.

`prepare_transport.py` records the one-time transition from the authenticated retained capture into this ordinary package. Its optional input is the earlier private capture catalogue, not a dependency of durable reproduction. It never downloads sources. Its historical extraction wrappers are provenance; complete member/product raw bytes are independently retained by this packet. Private machine paths are omitted from public receipts. Original capture receipts and failed earlier namespace-scan attempts remain preserved outside the author checkout; no source paths or historical wrappers are overwritten.

The reports and directed controls document complete original custody and two actual executions. Hash equality and GEOS validity establish neither the correctness of an administrative boundary nor whether a gap is water. The represented year, advertised counts, source license strings and build metadata are retained claims. Retrieval timestamps are transport observations, not effective geography dates. Source authority, political ownership, dated applicability and water interpretation require separate research. India is explicitly outside the administrative registry; its advertised count discrepancy remains visible.

Retained original geoBoundaries derivative-product use terms appear in `CITATION-AND-USE-geoBoundaries-original.txt`, authenticated against the recorded immutable upstream Git LFS pointer. `individual-source-attribution.json` preserves every original source credit and recorded underlying license. Credit [geoBoundaries](https://www.geoboundaries.org) and the individual metadata sources when using these products. The upstream derivative-product CC-BY4.0 statement does not independently establish underlying Oman government permission, source accuracy or territorial authority; the original Other-Direct-Permission metadata remains unchanged.

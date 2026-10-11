# Original administrative hash domains

This corrects issue #1739. Original Python JSON represents some integer-valued coordinates as `25.0` or `-8.0`; JavaScript serializes their same binary64 values as `25` or `-8`. Existing recorded digests must remain unchanged. A new digest of reformatted coordinates is not proof of the old preimage.

## Supported input extension

The complete source scope remains authenticated through the existing merged-handoff registry or literal original-product route. Existing direct JavaScript hash matches remain supported.

- `original_candidate_canonical_bindings` keeps its existing component and feature fields. For an original geometry domain it can additionally supply `geometry_sha256`, `geometry_bytes_base64` and `derived_js_geometry_canonical_sha256`. The original SHA must match the recorded physical row, decoded complete bytes must hash to that SHA, and their complete parsed value must match the actual candidate. Both full and fragment SOURCE predicates and NATIVE revalidation use the same check.
- `original_administrative_canonical_bindings` optionally supplies rows with `source_path`, `source_sha256` (the complete decoded source product), zero-based `feature_index`, `feature_sha256`, `geometry_sha256`, `feature_bytes_base64`, and `geometry_bytes_base64`. The consumer still reads and authenticates the complete source product/catalogue. Each alias names exactly one actual ordinal in that body. Both original byte preimages must hash exactly and completely parse to the corresponding actual feature/geometry. Duplicate ordinals, foreign products and omitted values fail. Feature and geometry hashes must match as a pair from the same serialization domain; mixed pairs fail.
- Encoded length is bounded before base64 decoding. Each new decoded alias and parsed/canonical scratch is prospectively charged to the existing shared phase budget; native case rechecks retain their repeated charges. Whole product and decoded preimage limits remain 32 MiB and the phase limit remains 256 MiB. These are admitted-byte accounting, not claims about exact JavaScript heap consumption.

No float normalization, geometry edits, replacement historical hashes, source approval, relaxed method matching or selection bypass is introduced. Existing supported-programme records are not changed. A delivery using the new caller still needs the ordinary independently reviewed programme registration and new execution receipts.

## Executed verification

The additive-gap-repair regression suite plus the new original-hash tests passed together with zero skips. Missing sparse historical fixtures were fetched as six exact blob OIDs, verified against the non-truncated immutable main tree, then read in the normal managed author checkout. They are not missing-test exceptions in the final result.

`reproduce-original-hashes.py` reads complete immutable retained source operands directly from Git, checks input admission before reading, and emits its result to stdout. It exercises only the changed join boundaries, not a native or scientific calculation:

- NOR `9870535a…`: actual original full SOURCE premises fail only `original-full-candidate-binding` before the geometry preimage; all premises pass afterward, and the actual NATIVE case revalidation entry accepts the unchanged candidate. A changed interior coordinate remains rejected even with its derived JS digest updated.
- NOR `fd74f968…`: the original NOR source feature at ordinal 128 has no JavaScript hash-pair match and exactly one authenticated original-preimage match.
- COD `ab011…`: the original AGO source feature at ordinal 120 has the same no-match/unique-match result.
- Both actual whole-product checks reject a wrong actual ordinal and a changed whole source body. Synthetic controls additionally reject coherent changed feature properties/coordinates, missing/duplicate aliases, wrong product bindings, mixed hash pairs, oversized input and cumulative budget exhaustion.

The first local actual-input adverse probe accidentally opened a polygon ring. It was corrected to mutate an interior vertex, and the final probe reaches and verifies the intended original-hash rejection. No source input was changed.

Original input commits: NOR `f3c8ecddff787f33e2b07de1fa36f4365abfc9df`; COD `3853d5a5a10acd5012bc92cb0261765d8117dc02`. The reproducer binds their literal paths, full source hashes and historical feature/geometry digests. These are retained-source code regression controls; upstream scientific authority is not re-evaluated.

## Limits and continuation

No complete SOURCE subprocess, NATIVE cell computation, selected output or production publication is claimed by this boundary replay. Programme registration follows independent method review, with all prior records preserved. The independent supported delivery wave continues on its earlier accepted method. The delivery owner can reuse the input extension after normal exact-head review, catalogue registration and qualified execution. Original unknowns and all scientific/publication gates remain in force.

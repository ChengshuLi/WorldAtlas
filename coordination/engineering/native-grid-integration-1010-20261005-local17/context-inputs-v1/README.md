# Immutable original-source to compact context inputs

This separately scoped transform consumes all43 original files enumerated in inputs.json at immutable548c5f89f00271050823076a84695bb41e1b8454. It preserves every original native geometry type and coordinate, stable location ID, original owner index and parent ID. It emits a minimal native-context input, not a new source or factual catalog: unused names, attributes and other metadata remain in untouched complete original files and are not included in this derivative. The existing application catalog is not replaced by it.

Generation used committed d70c5d8; readback used committed65cfcef. Two complete fresh vintages produced identical bytes, and readback authenticated every43 original source-file descriptor, all34 output parts and all49625 ID/parent/index mappings, exact original footprint digest, and3968397 original vertices. Original native Polygon versus single-part MultiPolygon type is preserved rather than inferred from ring count. Positive/negative controls cover unchanged source bytes, wrong/incomplete IDs or parents, changed digest and malformed coordinates. Neither numeric validation nor matching digests approves factual source topology.

Reproduction from an owned checkout with committed code and Node24:

```sh
node scripts/native-ownership/prepare-context-inputs.mjs 548c5f89f00271050823076a84695bb41e1b8454 FRESH-ONE
node scripts/native-ownership/prepare-context-inputs.mjs 548c5f89f00271050823076a84695bb41e1b8454 FRESH-TWO
node scripts/native-ownership/verify-context-inputs.mjs FRESH-ONE FRESH-TWO
node --test test/compact-context-inputs.test.mjs
```

The preparer requires plain Node execution, exact committed ordinary executed-code bytes, immutable original source reads, an exclusive fresh owned output directory, whole-file/decompressed32MiB limits and the unchanged aggregate256MiB/512descriptor admission budget. Both runs accounted249514779 bytes and87 descriptors, with additional131072bytes/16descriptors reserved for review. The retained derivative parts total32840846encoded bytes. The typed stage manifest also declares the immutable readback code and retained logs/README. Its inventory remains below the same byte and descriptor limits.

This is the original-to-compact stage only. Root integration can consume these exact byte-bound inputs and the separately verified native candidate without pretending it consumed the full original source set within the same transform. The stage evidence-quality.json is now a mandatory native static-build prerequisite, through scripts/native-ownership/validate-context-input-stage.mjs. It validates ordinary whole-file bytes, complete original and derivative inventories, immutable executed code, identities/parents/indices, native footprints and two-run product identity, then binds its receipt to the packaged atlas. Negative controls reject missing, tampered, omitted, stale and over-budget inputs. Final independent review is still outstanding; the existing standard queue does not automatically certify this README or arbitrary indexed subordinate packets. No existing evidence limit is widened. Existing legacy voluntary partition tooling is not silently repurposed as enforcement for this issue.

No original geometry, source file, factual record, release, default selection or live database is changed. Global factual coverage/water questions, broad dated-boundary performance, installation and deployment remain unapproved.

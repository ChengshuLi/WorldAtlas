# Authenticated subject gzip decoding

The shared whole-file inspector already validates gzip from an explicit decoded-byte descriptor. The subject readers now use that same declaration for containing files and prior-evidence inventory/registry JSON, while preserving plain JSON and legacy `.gz` behavior. Arbitrary binary files are not sniffed.

All original limits remain unchanged. Focused real-entry controls cover complete mixed component/contact membership, wrong hashes, coherently omitted/altered subjects, source vintages, prior inventories and candidate registries, and a small encoded legacy gzip whose actual decoded body exceeds the configured cap.

Both actual full subject checks executed immutable `4de4a4c2ed0c908eb08f3927b45ad73e75539b65` against the twelve original whole baseline files at `ea7ba3eafb0f7b5a384920c79fb6ed42cf48a653`. Each verifies all 45 component and eight contact identities from #1355; the 21 numerical siblings and old science remain unchanged. These are identity/byte checks, with no geography measurement or source-fitness approval. Actual commands/times/exits and both identical result bodies are retained under `verification/`.

Reproduction: in a checkout containing the frozen commit, run Node 24:

```
node coordination/engineering/subject-descriptor-decode-20261007/check-subjects.mjs 4de4a4c2ed0c908eb08f3927b45ad73e75539b65 run-one
node coordination/engineering/subject-descriptor-decode-20261007/check-subjects.mjs 4de4a4c2ed0c908eb08f3927b45ad73e75539b65 run-two
node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs
```

Use fresh absent run destinations. The complete-source reader authenticates source mode and whole encoded/decoded bodies through the real shared validator. The original input/caller files must match the frozen commit; numerical source data are read from immutable Git without materializing a world checkout.

The earlier shared-reader gzip parse failure and the first claim rejection caused by conflicting kind labels are historical receipts, not successful executions. This PR does not change GEO5 sources, observations, ownership, release or production. After delivery, GEO5 must refresh its genuine baseline/manifest and exact-head gate under its own claim.

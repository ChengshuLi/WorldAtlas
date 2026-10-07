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

The first real package build at head `7c33ffce` refused the changed shared helper against the original context validator's code pin. The coupled continuation retains all seventeen literal validator files from actual ancestor `83bed8c4c49e8f54077bb4abf0f32d41d0992f81`. This source ancestor is distinct from the old manifest's unchanged advertised execution commit. The dispatcher authenticates every file and transitive import before executing the actual original validator. Original stage manifests, snapshot overrides, context/release/geometry pointsets and hashes remain unchanged.

After the complete old stage passes, the dispatcher reads the same authenticated before/after contexts, proposal and release registry and calls current `validateContextMigration`. Its result must have exactly the same non-token receipt. Only the genuinely reconstructed current-realm proof crosses into coverage rebinding; the old realm's proof cannot substitute.

Original coupled controls at `7c38a431fe89085b11d3c2a89a7934a788164f9c` remain in `verification/prior-coupled-7c38/`. Index-binding controls at `90e3e58de82c7587326f35d75291bc1ce385f573` are retained in `verification/prior-coupled-90e3/`. Final shallow-portable control commit: `99160ebecb6e94f3419609810d81d33b019e875a`. The actual 38-test command includes six coupled controls:

```
node --test test/evidence-quality.test.mjs test/premerge-evidence.test.mjs test/build-context-validation-vintage.test.mjs
```

Those local tests use bounded fixtures and authentic small code/stage bodies. They do not materialize a whole context image or certify a combined scientific phase. The existing original consumer retains its independently bounded 17-code/105-data admission, including mandatory snapshot overrides; its complete real continuation must pass in hosted package CI. Combining that source floor with subject custody would exceed one ordinary scientific phase, so no such claim is made here. No original native/geography calculation is repeated. Ordinary Node without loaders or preloads is required for the captured code realm.

The final current proof also binds its geometry index body to the exact original stage SHA. A real formatting-only index mutation can leave the migration receipt identical, but is rejected by this source binding. All original geometry files are reauthenticated before current minting.

The real-entry small fixture is the exact 6,278-byte original stage body at ancestor83bed, retained as a candidate fixture and checked against the captured index SHA. Regression needs no undeclared historical Git fetch. This is an ordinary source copy, never a substitute baseline or a whole-context source image.
